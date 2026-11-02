# CenterPose 객체 추적 — YOLO · PyTorch · AprilTag

> 학습일 2026-10-29 (자료를 받은 날 기준), 정리일 2026-11-02
> 자료: CenterPose 객체 추적 — YOLO · PyTorch · AprilTag (KANT, 2026.10.29 공식 문서 기준, 100쪽. 로컬 `ref/ROS2/`에만 보관)
> 실습: [SeongminJaden/yolov8-ubuntu24-practice](https://github.com/SeongminJaden/yolov8-ubuntu24-practice), [Ubuntu 24.04 YOLOv8 실습 설치 가이드 (velog)](https://velog.io/@roboticsmaster/Ubuntu-24.04-YOLOv8-%EC%8B%A4%EC%8A%B5-%EC%84%A4%EC%B9%98-%EA%B0%80%EC%9D%B4%EB%93%9C)
> 관련: [260930 OpenCV·RealSense](../260930/ROS2.md), [261019 Isaac ROS 컨테이너](../261019/ROS2.md#isaac-ros-개발-컨테이너), [261020 카메라와 합성 데이터](../261020/ROS2.md#4-실습-2--카메라와-합성-데이터), [261021 태스크가 가능한 범위](../261021/ROS2.md#태스크가-가능한-범위)

## 목표
- 검출 상자 · 태그 ID · 물체 자세를 **같은 시각, 같은 좌표계**로 연결
- 가려져도 같은 물체인지 판단하고, 측정이 오래되면 행동을 멈춤
- 결과물(교안): 라벨 정책서, 데이터 분할표, YOLO 가중치, CenterPose ONNX, TF 구성, 추적 로그, 실패 영상

## 네 가지 구성 요소
| 요소 | 답하는 질문 | 출력 |
|---|---|---|
| YOLO | 무엇이 어디에 있나 | 클래스 · 2D 상자 · 점수 |
| CenterPose | 물체가 어떻게 놓였나 | 회전 · 이동 · 상대 크기 (3D 자세) |
| AprilTag | 이 표식은 몇 번인가 | ID · 코너 · 태그 자세 |
| PyTorch | 모델을 어떻게 학습하나 | 텐서 · 자동미분 · 최적화 (학습 도구) |

- YOLO와 PyTorch는 대체 관계가 아님 → **모델**과 **학습 도구**의 관계
- YOLO만으로는 3D 위치 · 회전 · 영구 ID를 모름 → CenterPose · AprilTag · 추적 계층과 역할을 나눔
- YOLO가 있을 때의 이점
  - AprilTag만 쓰면 태그가 보이는 물체만 정확한 ID로 구분
  - YOLO를 더하면 태그가 가려져도 외형으로 후보를 찾음 → 태그를 다시 읽기 전에는 같은 색 퍽을 같은 ID로 단정하지 않음
- YOLO는 CenterPose의 필수 전처리가 아님 (CenterPose 자체에 검출 과정이 있음)
  - 클래스 선택 · 후보 제한 · 재탐색 용도로 앞에 둘 수 있음

### 검출 · 자세 · 추적
| | 하는 일 | 주의 |
|---|---|---|
| 검출 | 프레임마다 후보를 찾음 | 검출 번호는 영구 ID가 아님 |
| 자세 추정 | 물체 좌표를 $R, t$로 표현 | CenterPose ROS 출력은 `Detection3DArray` |
| 추적 | 이전 물체와 현재 후보를 연결 | 출력을 이어 붙여도 안정된 ID · 가림 복구는 저절로 안 생김 |

### 통합 파이프라인
- 입력: 카메라 RGB + CameraInfo($K$)
- 세 모델 병렬: YOLO(클래스 · 상자), CenterPose(자세), AprilTag(ID · 태그 자세)
- 동기화 → 후보 연결 → TF 변환 → 추적 상태 + 불확실성 → 대상 선택 → 행동 허용 판정 → 로봇 제어기

## 버전과 장비 역할
- Ubuntu 24.04 + ROS 2 Lyrical(LTS, 지원 종료 2031년 5월) + Isaac ROS 5.0 (Jetson Orin은 JetPack 7.2)
- YOLOv8을 쓰는 이유: Isaac ROS 5.0에 **YOLOv8 전용 디코더**가 있음 (YOLOv8 자체가 LTS인 것은 아님)
- YOLO26도 가능하지만 출력 텐서 형식이 달라 디코더를 직접 구현해야 함
  - 할 일: 텐서 해석 → 신뢰도 · 클래스 변환 → resize/letterbox를 원본 픽셀로 복원 → `Detection2DArray` 발행 → 같은 영상으로 Ultralytics 결과와 비교
  - 이미 NMS가 적용된 출력에 NMS를 또 하지 않도록 확인
  - 모델 파일 이름만 바꿔 기존 디코더에 넣으면 안 됨

| 장비 | 하는 일 |
|---|---|
| 학습 PC | 데이터 검사 → GPU 학습 → ONNX 내보내기 (PyTorch · TAO) |
| Jetson / ROS 실행 장비 | TensorRT 엔진 생성 → 카메라 추론 → ROS 메시지 → 추적 → 행동 판단 |

- 파일이 바뀌는 흐름: `.pt`(PyTorch 가중치) → ONNX(계산 그래프 교환 형식) → TensorRT 엔진(대상 GPU 전용 실행기) → ROS 디코더 → 검출 메시지
  - 디코더: 모델 텐서를 클래스 · 상자 · 점수로 해석하는 코드
  - 학습 프레임워크 · 추론 엔진 · 통신 프레임워크를 구분
  - **엔진은 대상 장비에서 생성** (다른 GPU로 복사해 쓰지 않음)

## YOLOv8 검출 원리
- Backbone(특징 추출) → Neck(여러 크기 특징 결합) → Head(클래스와 상자 예측)
- 중복 상자는 NMS로 줄임

$$
\mathrm{IoU} = \frac{|A \cap B|}{|A \cup B|}
$$

- NMS (보충): 점수 높은 상자부터 남기고, 그 상자와 IoU가 임계값보다 큰 같은 클래스 상자를 지움
- **신뢰도 임계값과 IoU 임계값은 역할이 다름**
  - 신뢰도: 이 후보를 물체로 볼지
  - IoU: 두 상자를 같은 물체의 중복으로 볼지
- 상자 중심 픽셀 ≠ 3D 물체 중심 → 깊이나 자세 추정과 연결해야 로봇 좌표 목표가 됨
- 2D 추적 성공이 6D 자세 성공을 뜻하지 않음 (퍽 두 개가 교차 · 가림일 때 ID가 바뀌는지 시험)

## CenterPose
### 네트워크 구조 (교안 그림)
- 입력 $H \times W \times 3$ → 특징 추출(DLA34 등) → 특징 맵 $H/4 \times W/4 \times 64$ → 출력 헤드 셋

| 헤드 | 채널 | 의미 |
|---|---|---|
| 물체 중심 | 중심 히트맵 1, 서브픽셀 오프셋 2, 2D 상자 크기 2 | 물체 후보 위치 |
| 키포인트 | 히트맵 8, 오프셋 16, 중심에서의 변위 16 | 3D 상자 꼭짓점 8개의 영상 위 위치 (점마다 x, y) |
| 상대 크기 | 3 | 폭 · 높이 · 길이의 비 (예: 0.64 / 1 / 0.69) |

- 후처리: 2D 키포인트 복원 + 카메라 내부 파라미터 → PnP → 6-DoF 자세와 크기
- 중심 히트맵에서 값이 가장 큰 곳 = 물체 후보
- 꼭짓점 순서는 **물체 좌표계 기준으로 모든 영상에서 같게** (화면 왼쪽 점을 매번 1번으로 붙이면 안 됨)
- 공개 시연 · 원문 예시는 우리 장비 결과가 아님. 퍽이 신발 모델로 검출될 거라 가정하지 않음
- CenterPoseTrack: 시간 필터와 불확실성을 쓰는 **별도 연구 모델** → ROS CenterPose 옵션 변경으로 대체 안 됨

### 카메라 투영과 6D 자세
$$
p_c = R\,p_o + t, \qquad u = f_x \frac{X}{Z} + c_x, \quad v = f_y \frac{Y}{Z} + c_y
$$

- $p_o$: 물체 좌표의 점, $p_c = (X, Y, Z)$: 카메라 좌표의 점, $f$: 초점거리(px), $c$: 주점
- 6D = 이동 3축 + 회전 3축
- 픽셀 오차가 작아도 깊이 · 스케일이 맞다고 단정할 수 없음. 왜곡 보정 여부도 기록

### PnP
$$
R^*, t^* = \arg\min_{R,t} \sum_i \big\| u_i - \pi\big(K(RP_i + t)\big) \big\|^2
$$

- 3D 기준점 $P_i$(상자 꼭짓점)와 영상점 $u_i$의 **재투영 오차**를 최소화하는 자세를 찾음
- 보충: 대응점 3쌍(P3P)은 해가 여러 개라 보통 4쌍 이상 사용
- 실패 원인: 점 순서 오류 → 뒤집힌 자세 / $K$ 오류 → 거리 · 방향 오차 / 가림 → 부정확한 점
- 잔차와 **양의 깊이**($Z > 0$)를 검사

### 단안 영상의 크기 모호성
- 작고 가까운 물체와 크고 먼 물체는 영상에서 비슷하게 보임
- CenterPose의 크기는 **상대 크기** → 이것만으로 절대 거리(m)를 확정하지 않음
- 실측 치수 · 깊이 · 기준 표식으로 스케일 검증
  - ROS 디코더의 `cuboid_scaling_factor`를 조정한 뒤 여러 거리에서 실제 길이와 비교

### 대칭과 회전 정답
- 원기둥: 축 둘레로 돌려도 외형이 같음 / 정사각 기둥: 90°마다 반복
- 태그 방향으로 기준을 정할 수 있지만, 태그가 가려지면 회전을 관측할 수 있는지가 달라짐
  - 그래서 태그가 안 보일 때는 yaw 판단을 보류
- 축과 대칭을 라벨 정책에 명시

## AprilTag
- 검은 경계와 사각형 코너를 찾고, 내부 비트 패턴으로 ID 해독
- 한 변의 실제 길이와 $K$로 태그 좌표계의 자세 계산
- 태그 ID는 의미가 없음 → **ID → 물체명 · 치수 · 장착 변환** 매핑 파일을 따로 작성
- `size`는 **검은 경계 기준** 한 변 (예: 검은 경계 16mm면 `0.016`, 흰 여백 포함 20mm와 구분)
- Isaac ROS AprilTag의 CUDA 백엔드는 tag36h11 지원. family가 다르면 ID 검출이 아예 안 됨

### 작은 태그의 인식 거리
- 영상에서 태그 한 변의 크기 $p \approx f_x s / Z$
- 교안 예시: $f_x = 600$px, $s = 0.016$m → 0.5m에서 약 19.2px, 1.0m에서 약 9.6px
- 이 값은 성공 거리 보장이 아님 (기울기 · 흐림 · 노출 · 해상도로 코너와 비트가 사라짐) → 거리별 ID 성공률과 자세 오차를 실측해 접근 거리를 정함

### 태그 중심 → 물체 중심
$$
T_{co} = T_{ct}\,T_{to}, \qquad T_{bo} = T_{bc}\,T_{co}
$$

- $T_{ab}$: b 좌표를 a 좌표로 바꾸는 4×4 동차변환 / c 카메라, t 태그, o 물체, b 로봇 기준
- 카메라→태그 측정값에 태그→물체 장착 변환을 곱함
- 예: 높이 60mm 퍽의 윗면 태그와 물체 중심은 약 30mm 차이. 태그 축 방향과 두께도 측정

## 좌표계 · 보정 · 동기화
| | x | y | z |
|---|---|---|---|
| ROS 본체 | 전방 | 왼쪽 | 위 |
| 카메라 optical | 오른쪽 | 아래 | 전방 |

- [261021](../261021/ROS2.md#카메라가-아래를-보는-것처럼-보였던-이유)의 `*_link` / `*_optical_frame` 차이와 같은 규칙
- 길이 m, 각도 rad. 쿼터니언은 xyzw 순서인지 확인. 픽셀 좌표와 미터 좌표를 섞지 않음
- OpenGL / OpenCV 축 변환 여부를 학습 · 평가 · ROS에서 일치시킴
- CameraInfo의 $K$ · $D$, 영상 해상도, 왜곡 보정 상태가 서로 맞아야 함
- 동기화
  - image stamp 기준으로 관측을 연결, 허용 시간차를 넘으면 버림
  - TF도 **관측 시각의** 변환을 사용 (움직이는 카메라의 지연을 물체 움직임으로 착각하지 않게)

### 크롭 · 리사이즈 후 좌표 보정
- 크롭 · 리사이즈는 픽셀 좌표계를 바꾸는 연산 → YOLO ROI를 잘라 CenterPose에 넣으면 $K$도 같이 바꿔야 함
- 크롭 원점 $(x_0, y_0)$, 배율 $s$일 때

$$
u' = s(u - x_0), \quad v' = s(v - y_0), \qquad f'_x = s f_x, \quad c'_x = s(c_x - x_0)
$$

- $y$도 같은 식. letterbox 여백이 있으면 $c'$에 `pad_x`, `pad_y`를 더함
- 보정된 $K$를 쓰거나, 키포인트를 원본 좌표로 되돌려 PnP → **둘 중 하나만** (중복 적용 금지)
- 원본 CameraInfo를 그대로 쓰면 자세가 틀어짐

## 데이터와 라벨
### 수집 계획
- 여러 개체 · 거리 · 회전 · 배경 · 조명 · 흐림 · 부분 가림 · 태그 상태를 섞음
- 같은 장면의 연속 프레임만 많이 모으지 않음
- `manifest.csv`에 image, session_id, object_id, split, label_version, camera_id 기록
- 먼저 소규모 데이터로 전체 경로를 통과시킨 뒤 실패 조건을 보충

### 오픈데이터 선택
| 데이터 | 정답 | 쓰임 |
|---|---|---|
| COCO | 일상 물체 2D 상자 · 분할 | 검출 학습의 출발점 |
| Objectron | 범주별 영상 + 3D 상자 + 카메라 정보 | 범주 단위 자세 학습 |
| BOP | 물체 모델(.ply) + 6D 자세 | 6D 자세 평가 |

- 이름이 같은 데이터라도 주는 정답이 다름 → 먼저 모델의 입력 · 출력 표를 작성
  - YOLO: RGB → 클래스 · 상자 / CenterPose: RGB + $K$ → 자세 / 추적: 연속 관측 → 유지되는 ID와 상태
- COCO 상자로 CenterPose 6D 라벨을 만들 수 없음. 퍽의 빨강 · 초록 클래스는 직접 라벨링
- 사용 전 확인 4가지: 라이선스 · 인용 / 카테고리 · 촬영 조건 / 라벨 필드 · 좌표계 · 단위 / 학습 · 평가 분할
  - manifest에 출처 URL, 버전, 받은 날짜, 파일 SHA-256, 원본 split 기록
- 형식 변환 주의
  - Objectron → CenterPose: 원본 라벨 파싱 → 프레임 추출 → 이미지와 같은 이름(stem)의 JSON
  - BOP: 이동 단위가 mm일 수 있음 → $t_m = t_{mm}/1000$, 회전행렬 $R$은 배율 변환 안 함
  - BOP → CenterPose: 모델에서 기준 3D 상자를 정하고 $R, t, K$로 투영점 9개(중심 + 꼭짓점 8) 계산. JSON 이름만 바꿔 넣으면 안 됨
- 변환 후 첫 검수: 3D 상자를 $u \sim K(RX + t)$로 투영해 원본 위에 겹쳐 봄 (20장, 앞뒤 뒤집힘 · 중심 이동 · 1000배 크기 오류)

### COCO → YOLO 좌표
- COCO `[x, y, w, h]`: 왼쪽 위 + 폭 · 높이 (픽셀) / YOLO `class cx cy bw bh`: 중심 + 크기, 0~1 정규화

$$
c_x = \frac{x + w/2}{W}, \quad c_y = \frac{y + h/2}{H}, \quad b_w = \frac{w}{W}, \quad b_h = \frac{h}{H}
$$

- 교안 예시: $W{=}640, H{=}480$, `[100,120,80,60]` → `0.21875 0.3125 0.125 0.125`
- COCO `category_id`는 연속 번호가 아님 → 이름으로 골라 0부터 새로 매김, `data.yaml`의 names도 같은 순서
- 검사: $0 \le$ 좌표 $\le 1$, 폭 · 높이 $> 0$, 이미지와 TXT 이름 일치, 객체가 없으면 빈 TXT 가능

### 분할과 누수
- 연속 영상의 100번과 101번 프레임은 거의 같음 → 하나는 train, 하나는 test에 넣으면 성능이 부풀려짐
- 촬영 세션 · 물체 개체 · 배경 단위로 train/val/test를 나눔 (70/15/15는 시작안)
- val로 임계값 선택, test는 마지막에 한 번. 새 장소 · 조명 · 물체는 별도 holdout으로

### 라벨 정책
- YOLO 클래스 예: `red_cylinder`, `red_prism`, `green_cylinder`, `green_prism`
  - 한 객체에 상자 하나. 가림은 "원래 윤곽 추정"과 "보이는 부분만" 중 하나를 정해 문서화
  - CVAT 자동 보간 결과를 그대로 정답으로 쓰지 않음
- CenterPose 라벨: 중심 1점 + 꼭짓점 8점의 `projected_cuboid`(픽셀), `camera_data`(fx, fy, cx, cy, projection matrix), `scale`, `quaternion_xyzw`, `location`, `keypoints_3d`
  - 꼭짓점 순서를 로더 · PnP의 3D 기준점 순서와 맞춤
- AprilTag ID는 메타데이터일 뿐 꼭짓점 정답을 대신하지 않음
- AprilTag로 자세 라벨 보조 생성(pseudo-label): 태그 자세 + 장착 변환 → 실측 3D 상자를 투영해 키포인트 생성
  - 태그가 가려지거나 잘못 읽힌 프레임은 자동 승인 안 함
  - 태그 자세로 라벨을 만들었다면, 같은 태그 자세와 비교하는 것은 **독립적인 정확도 검증이 아님**
- 합성 데이터: 자세 · $K$ · 가림을 정확히 기록하기 쉬움, 도메인 랜덤화로 다양성 → 실제 영상의 실패 분포는 따로 평가 ([261020](../261020/ROS2.md#4-실습-2--카메라와-합성-데이터), [261021 도메인 랜덤화](../261021/ROS2.md#도메인-랜덤화))
- 검수 순서: 정적 검사 → 원본 위 시각 검사 → 한 배치 과적합 시험 → 새 세션 평가

## 학습
### PyTorch 학습 구조
| 부품 | 역할 |
|---|---|
| Dataset | 이미지와 정답 읽기 |
| DataLoader | 배치 구성 |
| Model | 예측 계산 (순전파) |
| Loss | 예측과 정답의 차이 |
| Optimizer | 가중치 갱신 |
| Validation | 학습 없이 성능 확인 |
| Checkpoint | 가중치 · 상태 저장 |

$$
\theta \leftarrow \theta - \eta\, \nabla_\theta L
$$

- $\theta$: 가중치, $\eta$: 학습률, $\nabla_\theta L$: 손실이 커지는 방향 → 반대로 이동
- 학습률이 크면 불안정, 작으면 수렴이 느림
- train loss 감소와 val 성능 개선은 다른 것 → 둘 다 기록

```python
model.train()
for image, target in loader:
    optimizer.zero_grad()          # 이전 기울기 초기화
    pred = model(image)            # 순전파
    loss = loss_fn(pred, target)   # 오차 계산
    loss.backward()                # 역전파
    optimizer.step()               # 가중치 갱신
```

- 검증은 `model.eval()` + `torch.inference_mode()`, `optimizer.step()` 호출 안 함
- 재현성: best 가중치 선택 기준, 데이터 목록 · seed · 버전 · 설정 저장. 학습 재개 시 optimizer · scheduler 상태 포함 여부 확인
- CenterPose 손실 개념: $L = \sum_j \lambda_j L_j$ (중심 · 키포인트 · 변위 · 상대 크기를 각각 감독해 가중합)
  - 손실이 줄어도 축 방향 · 스케일이 맞는지는 따로 검사

### YOLO 학습 설정
- 공개 사전학습 가중치(`yolov8n.pt`)에서 시작해 자체 퍽 라벨로 파인튜닝
- 첫 실행: 작은 모델, 작은 배치로 메모리 확인, 고정 seed와 같은 분할. 50 epoch는 시작값
- 퍽이 작게 찍히면 촬영 거리 · 해상도부터 검토
- 색이 클래스 기준이면 색 증강(hue)이 정답을 바꾸지 않는지 확인 (실습 저장소는 hue 증강 0)
- 공개 데이터와 섞을 때: A(자체만) vs B(공개 일부 + 자체)를 같은 holdout에서 비교, 혼합 비율 기록

### TAO CenterPose
- 학습은 NVIDIA TAO GPU 컨테이너에서 (`tao model centerpose train / evaluate / export`)
- 교안 시작안: category `puck_prism`, num_classes 1, batch 4, num_symmetry 1, max_objs 12, backbone DLA34, 140 epoch, lr 0.00006, lr_steps [90, 120]
- 평가: 위치 오차, 회전 오차, 대칭을 고려한 3D IoU

## 배포
- YOLO ONNX: 고정 입력, NMS 없는 출력으로 내보내고 디코더에 연결

```shell
yolo export model=runs/detect/pucks/weights/best.pt format=onnx imgsz=640 batch=1 dynamic=False nms=False
```

- CenterPose ONNX (공식 ROS 예제): 입력 `1×3×512×512`(NCHW), 출력 7개 `bboxes`, `scores`, `kps`, `clses`, `obj_scale`, `kps_displacement_mean`, `kps_heatmap_mean` → 내 export와 이름 · 차원 대조
- TensorRT: FP32로 먼저 ONNX와 출력 비교 → FP16 최적화 후 재평가. **파싱 성공 ≠ 정확도 검증**

```shell
/usr/src/tensorrt/bin/trtexec --onnx=/models/puck.onnx --saveEngine=/models/puck.plan
```

- Isaac ROS 쪽
  - `isaac-ros activate` 후 `ROS_DISTRO`가 lyrical인지, `isaac_ros_centerpose` · `isaac_ros_yolov8` 패키지 확인
  - 공식 CenterPose 예제(신발 모델 + rosbag)부터 → rosbag으로 입력 고정, 결과 확인 후 카메라 · 자체 모델로 교체
  - 결과 확인: 상자가 물체와 맞는지, 축이 움직임과 일치하는지, 단위 · `frame_id` · stamp
  - 자체 모델은 Triton 폴더(`config.pbtxt` + `1/model.plan`), config의 name · input · output이 엔진과 일치해야 함
  - AprilTag 노드: image + camera_info 입력 → `/tag_detections`, `/tf` 출력

## 추적과 행동 정책
### 연결 모듈 설계 (교안의 함수 나누기)
| 함수 | 역할 |
|---|---|
| `normalize_detection` | 각 출력의 ID · 시각 · frame · 단위 정리 |
| `associate` | 겹침 · 거리 · ID 조건으로 후보 연결 |
| `transform_pose` | 관측 시각의 TF로 공통 좌표계 변환 |
| `update_track` | 시간 상태와 신뢰도 갱신 |
| `choose_action` | 행동 제안 (모터 명령은 안 냄) |

- 입력에 값과 함께 stamp · frame_id · source · unit 저장, 관측이 없으면 None/상태 코드 (이전 값을 새 측정처럼 쓰지 않음)
- gating: 시간차 · 재투영 오차 · 태그 ID · 상자 겹침 · 예측 위치 · 크기 · 양의 깊이를 통과한 후보만 연결
  - 가장 가까운 후보만 고르면 교차 때 ID가 바뀜 → ID 충돌 · 후보 여럿 · 크게 튀는 자세는 보류 후 재관측

### 시간 필터
$$
x_\text{pred} = F x_\text{prev}, \qquad x_\text{est} = x_\text{pred} + K\,(z - H x_\text{pred})
$$

- $F$: 운동 모델, $H$: 관측 모델, $z$: 관측, $K$: 칼만 이득 (카메라 $K$와 다른 것)
- 예측과 관측의 차이(잔차)를 불확실성에 따라 반영. 보충: 공분산도 함께 예측 · 갱신해 이득이 정해짐
- 회전은 쿼터니언으로, 오일러 각을 그냥 평균내지 않음

### track_id와 tag_id
- `track_id`: 추적기 내부의 임시 번호 (ByteTrack 등) / `tag_id`: 물체에 붙인 표식 번호
- 가려졌다 나타나 새 track_id가 생겨도 tag_id로 같은 물체인지 확인
- 겹친 상자에 태그가 동시에 들어가면 연결 보류, 태그 재등장은 과거 위치로 검증

### 상태 전이
- SEARCH → CONFIRM → TRACK, 미검출 → LOST, 재검출 → CONFIRM, ID 충돌 · 오래된 측정 → HOLD

| 상태 | 의미 |
|---|---|
| CONFIRM | 연속 유효 관측을 요구 |
| TRACK | 선택된 ID 유지 |
| LOST | 마지막 위치만 보존 |
| HOLD | 접근 · 집기 명령 보류 |

- **새 관측 없이 마지막 자세로 계속 움직이지 않음**
- 교안 예시 시작값: 연속 확인 3프레임, 유효 관측 최대 나이 0.3초, 허용 위치 변화 0.15m → 로봇 속도 · FPS · 지연에 맞춰 조정
- 신뢰도 점수를 실제 성공 확률로 바로 해석하지 않음

### 규칙 정책과 강화학습
- 규칙: 사람이 조건과 행동을 정의 / RL: 보상으로 $\pi(a \mid o)$ 학습
- 검출기 지도학습과 로봇 행동 정책 학습은 다른 문제 → 지각 모델과 제어기 경계를 유지
- 교안의 확장 예: 카메라 시점 선택을 RL로 (관측: 대상 위치 · 불확실성 · 가림 / 행동: 시점 · 속도 / 보상: 재인식 성공 − 지연 − 충돌)
- 최종 실행은 규칙으로 제한

### 지연과 처리량
- 카메라부터 행동 판단까지 전체 지연과 관측 나이를 기록
- 모델별 단독 FPS를 더해도 통합 FPS가 아님
- 예: YOLO 매 프레임, CenterPose 낮은 주기, 태그는 필요한 영역 · 주기만
- 큐가 쌓이면 오래된 영상을 버리고 최신 관측 우선

## 평가와 실패 점검
| 계층 | 지표 |
|---|---|
| 검출 | Precision, Recall, mAP |
| 자세 | 위치 · 회전 · 재투영 오차 |
| 추적 | ID 교체, 재획득 시간 |
| 통합 | 목표 선택 정확도, 가림 후 복구율, 잘못된 접근/집기 횟수, 관측 나이 p95, 최대 메모리 |

- 보충: Precision = TP/(TP+FP), Recall = TP/(TP+FN), mAP50은 IoU 0.5 기준, mAP50-95는 IoU 0.5~0.95 평균
- 단계별 비교: A 태그만 / B YOLO + 2D 추적 / C CenterPose + 시간 연결 / D 셋 다 → 태그 보임 · 가림, 원기둥 · 직육면체로 나눠 평가, 줄어든 오류와 늘어난 지연을 함께 보고

| 증상 | 먼저 볼 것 |
|---|---|
| 검출 없음 | 클래스 · 조명 · 해상도 |
| 자세 뒤집힘 | 점 순서 · 축 · $K$ |
| 거리 배율 오류 | 실측 크기 · 단위 |
| 태그 없음 | family · 크기 · 흐림 |
| ID 교체 | 연결 임계값 · 시간차 |
| 영상 멈춤 | QoS · 토픽 · GPU 메모리 |
| 오래된 명령 | stamp · 큐 · TTL |

- 실패 영상을 고정하고 한 번에 한 조건만 바꿔 같은 rosbag으로 재시험

## Waffle 4WD 계획과 연결
- [261021](../261021/ROS2.md#태스크가-가능한-범위)에서 물체 자세는 Isaac ROS CenterPose로 받기로 함 → 이 교안의 구조가 그 관측 계층
- CenterPose 크기는 상대값 → RealSense 깊이나 실측 퍽 치수로 스케일 검증이 필요
- 팔 끝 Arducam 영상을 ROI로 잘라 쓰면 $K$ 보정 필요, 카메라가 움직이므로 관측 시각의 TF 사용
- 강화학습 관측으로 쓸 때는 관측 나이 · LOST/HOLD 상태와 추정 잡음을 시뮬레이션에도 반영해야 함

## 실습
- 저장소 README와 velog 설치 가이드를 따라 진행
- 흐름
  1. 호스트에서 Ubuntu · GPU 확인 → 학습용 venv(`.venv-yolo`)에 고정 버전 설치 (torch 2.9.1 + torchvision 0.24.1 cu128, ultralytics 8.3.221, numpy 1.26.4, opencv-python 4.11.0.86, onnx 1.17.0)
  2. 공개 이미지 한 장 추론, COCO8 1 epoch 학습으로 설치 점검
  3. 퍽 4클래스 라벨 검사 → 학습 → test 평가 → ByteTrack 영상 추적 → ONNX 내보내기
  4. Isaac ROS 5.0 컨테이너에서 TensorRT 엔진 생성 → YOLOv8 ROS 검출 실행
- 주의점 (자료 기준)
  - 시스템 Python에 `sudo pip`, `--break-system-packages` 쓰지 않음 → venv
  - 기존 `configs/pucks.yaml`을 덮지 않고 `pucks-local.yaml`을 새로 만듦
  - 저장소의 합성 퍽(원 · 사각형)은 코드 흐름 확인용 → 실제 인식 성능을 뜻하지 않음
  - `trtexec`은 학습 venv가 아니라 Isaac ROS 컨테이너에서, 엔진은 대상 GPU에서 다시 생성
  - Isaac ROS 5.0 x86 조건: Ampere 이상 GPU, VRAM 8GB 이상, 드라이버 595 이상, CUDA 13.2 이상, 여유 디스크 32GB 이상

```shell
# 학습용 환경 (호스트)
python3 -m venv .venv-yolo && source .venv-yolo/bin/activate
python -m pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu128
python -m pip install numpy==1.26.4 opencv-python==4.11.0.86 ultralytics==8.3.221 onnx==1.17.0
python -m pip check && yolo checks

# 설치 점검: 한 장 추론, 짧은 학습
yolo detect predict model=yolov8n.pt source=data/demo/bus.jpg imgsz=640 device=0 save=True
yolo detect train model=yolov8n.pt data=coco8.yaml epochs=1 imgsz=640 batch=2 device=0

# 퍽 데이터: 라벨 검사 → 학습 → 평가 → 추적 → ONNX
python scripts/validate_labels.py data/yolo/labels --classes 4
python scripts/train_yolo.py --data configs/pucks-local.yaml --epochs 50 --batch 4 --device 0
export YOLO_WEIGHTS=runs/detect/pucks/weights/best.pt   # 콘솔에 나온 실제 경로로
yolo detect val model="$YOLO_WEIGHTS" data=configs/pucks-local.yaml split=test device=0
python scripts/track_yolo.py --weights "$YOLO_WEIGHTS" --source data/test.mp4 --device 0
python scripts/export_onnx.py --weights "$YOLO_WEIGHTS" --output models/pucks.onnx

# Isaac ROS 컨테이너
isaac-ros activate
printenv ROS_DISTRO   # lyrical
```

- 실행 결과는 이 TIL에 기록하지 않음
