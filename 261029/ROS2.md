# CenterPose 객체 추적 — YOLO · PyTorch · AprilTag

> 학습일 2026-10-29 (자료를 받은 날 기준), 정리일 2026-11-02. 자료: KANT 교안 (2026.10.29 공식 문서 기준, 100쪽, 로컬 `ref/ROS2/`에만 보관)
> 실습: [SeongminJaden/yolov8-ubuntu24-practice](https://github.com/SeongminJaden/yolov8-ubuntu24-practice), [Ubuntu 24.04 YOLOv8 실습 설치 가이드 (velog)](https://velog.io/@roboticsmaster/Ubuntu-24.04-YOLOv8-%EC%8B%A4%EC%8A%B5-%EC%84%A4%EC%B9%98-%EA%B0%80%EC%9D%B4%EB%93%9C)
> 관련: [260930 OpenCV·RealSense](../260930/ROS2.md), [261019 Isaac ROS 컨테이너](../261019/ROS2.md#isaac-ros-개발-컨테이너), [261020 카메라와 합성 데이터](../261020/ROS2.md#4-실습-2--카메라와-합성-데이터), [261021 태스크가 가능한 범위](../261021/ROS2.md#태스크가-가능한-범위)

## 목표와 역할 분리
- 검출 상자 · 태그 ID · 물체 자세를 **같은 시각, 같은 좌표계**로 연결
- 가려져도 같은 물체인지 판단하고, 측정이 오래되면 행동을 멈춤

| 요소 | 답하는 질문 | 출력 |
|---|---|---|
| YOLO | 무엇이 어디에 있나 | 클래스 · 2D 상자 · 점수 |
| CenterPose | 물체가 어떻게 놓였나 | 회전 · 이동 · 상대 크기 (3D 자세) |
| AprilTag | 이 표식은 몇 번인가 | ID · 코너 · 태그 자세 |
| PyTorch | 모델을 어떻게 학습하나 | 텐서 · 자동미분 · 최적화 (학습 도구) |

- YOLO와 PyTorch는 대체 관계가 아님 → **모델**과 **학습 도구**의 관계
- YOLO만으로는 3D 위치 · 회전 · 영구 ID를 모름 → CenterPose · AprilTag · 추적 계층과 역할을 나눔
- YOLO는 CenterPose의 필수 전처리가 아님 → 클래스 선택 · 후보 제한 · 재탐색 용도로 앞에 둘 수 있음

| | 하는 일 | 주의 |
|---|---|---|
| 검출 | 프레임마다 후보를 찾음 | 검출 번호는 영구 ID가 아님 |
| 자세 추정 | 물체 좌표를 $R, t$로 표현 | CenterPose ROS 출력은 `Detection3DArray` |
| 추적 | 이전 물체와 현재 후보를 연결 | 출력을 이어 붙여도 안정된 ID · 가림 복구는 저절로 안 생김 |

- 파이프라인: RGB + CameraInfo($K$) → YOLO · CenterPose · AprilTag 병렬 → 동기화 → 후보 연결 → TF 변환 → 추적 상태 → 행동 허용 판정 → 제어기

## 버전과 배포 흐름
- Ubuntu 24.04 + ROS 2 Lyrical + Isaac ROS 5.0 (Jetson Orin은 JetPack 7.2)
- YOLOv8을 쓰는 이유: Isaac ROS 5.0에 **YOLOv8 전용 디코더**가 있음. YOLO26은 출력 형식이 달라 디코더를 직접 구현해야 함
- `.pt`(PyTorch 가중치) → ONNX → TensorRT 엔진 → ROS 디코더 → 검출 메시지
  - 학습 PC: 데이터 검사 · GPU 학습 · ONNX 내보내기 / Jetson: 엔진 생성 · 추론 · 추적 · 행동 판단
  - **엔진은 대상 장비에서 생성**. FP32로 ONNX와 출력 비교 후 FP16 → **파싱 성공 ≠ 정확도 검증**
- Isaac ROS: 공식 CenterPose 예제(신발 모델 + rosbag)부터 확인 후 카메라 · 자체 모델로 교체, 자체 모델은 Triton 폴더(`config.pbtxt` + `1/model.plan`)

## YOLOv8
- Backbone(특징 추출) → Neck(여러 크기 특징 결합) → Head(클래스와 상자 예측), 중복 상자는 NMS로 줄임
- $\mathrm{IoU} = |A \cap B| / |A \cup B|$
- **신뢰도 임계값**(이 후보를 물체로 볼지)과 **IoU 임계값**(두 상자를 같은 물체의 중복으로 볼지)은 역할이 다름
- 상자 중심 픽셀 ≠ 3D 물체 중심 → 깊이나 자세 추정과 연결해야 로봇 좌표 목표가 됨
- 2D 추적 성공이 6D 자세 성공을 뜻하지 않음

## CenterPose
- 입력 영상 → 특징 추출(DLA34 등) → 헤드: 물체 중심(히트맵 · 오프셋 · 2D 크기), 키포인트(3D 상자 꼭짓점 8개), 상대 크기(3)
- 후처리: 2D 키포인트 + $K$ → PnP → 6-DoF 자세와 크기
- 꼭짓점 순서는 **물체 좌표계 기준으로 모든 영상에서 같게** (화면 왼쪽 점을 매번 1번으로 붙이면 안 됨)
- 공개 시연은 우리 장비 결과가 아님. 퍽이 신발 모델로 검출될 거라 가정하지 않음

### 투영과 PnP
- 투영 $u \sim K(RX + t)$, 즉 $u = f_x X/Z + c_x$, $v = f_y Y/Z + c_y$ (6D = 이동 3축 + 회전 3축)
- PnP: 3D 기준점 $P_i$(상자 꼭짓점)와 영상점 $u_i$의 **재투영 오차**를 최소화하는 자세를 찾음

$$
R^*, t^* = \arg\min_{R,t} \sum_i \big\| u_i - \pi\big(K(RP_i + t)\big) \big\|^2
$$

- 실패 원인: 점 순서 오류 → 뒤집힌 자세 / $K$ 오류 → 거리 · 방향 오차 / 가림 → 부정확한 점. 잔차와 양의 깊이($Z > 0$) 검사

### 크기 모호성과 대칭
- 작고 가까운 물체와 크고 먼 물체는 영상에서 비슷 → CenterPose 크기는 **상대 크기**, 이것만으로 절대 거리(m)를 확정하지 않음
- 실측 치수 · 깊이 · 기준 표식으로 스케일 검증 (`cuboid_scaling_factor` 조정 후 여러 거리에서 실제 길이와 비교)
- 원기둥은 축 둘레, 정사각 기둥은 90°마다 외형 반복 → 태그가 안 보이면 yaw 판단 보류, 축과 대칭을 라벨 정책에 명시

## AprilTag
- 검은 경계 · 코너를 찾고 내부 비트로 ID 해독 → 한 변의 실제 길이와 $K$로 태그 자세 계산
- 태그 ID는 의미가 없음 → **ID → 물체명 · 치수 · 장착 변환** 매핑 파일을 따로 작성
- `size`는 **검은 경계 기준** 한 변 (16mm면 `0.016`). Isaac ROS CUDA 백엔드는 tag36h11, family가 다르면 검출 안 됨
- 영상 속 태그 한 변 $p \approx f_x s / Z$ → 예: $f_x = 600$px, $s = 0.016$m면 0.5m에서 약 19.2px, 1.0m에서 약 9.6px
  - 성공 거리 보장이 아님 → 거리별 ID 성공률과 자세 오차를 실측해 접근 거리를 정함
- 태그 → 물체 중심: $T_{co} = T_{ct}\,T_{to}$, $T_{bo} = T_{bc}\,T_{co}$ (c 카메라, t 태그, o 물체, b 로봇 기준)
  - 예: 높이 60mm 퍽의 윗면 태그와 물체 중심은 약 30mm 차이

## 좌표계 · 동기화 · 크롭
- ROS 본체 x 전방 · y 왼쪽 · z 위 / 카메라 optical x 오른쪽 · y 아래 · z 전방 ([261021](../261021/ROS2.md#카메라가-아래를-보는-것처럼-보였던-이유)과 같은 규칙)
- 길이 m, 각도 rad, 쿼터니언 xyzw 확인. CameraInfo의 $K$ · $D$, 해상도, 왜곡 보정 상태가 서로 맞아야 함
- image stamp 기준으로 관측 연결, 허용 시간차를 넘으면 버림. TF도 **관측 시각의** 변환 사용
- 크롭 · 리사이즈는 픽셀 좌표계를 바꿈 → YOLO ROI를 잘라 CenterPose에 넣으면 $K$도 바꿔야 함
  - 크롭 원점 $(x_0, y_0)$, 배율 $s$: $u' = s(u - x_0)$, $f'_x = s f_x$, $c'_x = s(c_x - x_0)$ ($y$도 같음, letterbox면 pad를 더함)
  - 보정된 $K$를 쓰거나 키포인트를 원본 좌표로 되돌려 PnP → **둘 중 하나만**. 원본 CameraInfo를 그대로 쓰면 자세가 틀어짐

## 데이터와 라벨
- COCO(2D 상자) · Objectron(범주별 3D 상자) · BOP(6D 자세)는 주는 정답이 다름 → COCO 상자로 CenterPose 6D 라벨을 만들 수 없음
- 형식 변환 후 3D 상자를 $u \sim K(RX + t)$로 원본 위에 투영해 검수 (앞뒤 뒤집힘 · 중심 이동 · 1000배 크기 오류)

### COCO → YOLO 좌표
- COCO `[x, y, w, h]`(왼쪽 위 + 폭 · 높이, px) → YOLO `class cx cy bw bh`(중심 + 크기, 0~1 정규화)

$$
c_x = \frac{x + w/2}{W}, \quad c_y = \frac{y + h/2}{H}, \quad b_w = \frac{w}{W}, \quad b_h = \frac{h}{H}
$$

- 교안 예시: $W{=}640, H{=}480$, `[100,120,80,60]` → `0.21875 0.3125 0.125 0.125`
- COCO `category_id`는 연속 번호가 아님 → 이름으로 골라 0부터 새로 매김, `data.yaml`의 names도 같은 순서
- 검사: 좌표 0~1, 폭 · 높이 $> 0$, 이미지와 TXT 이름 일치

### 분할과 라벨 정책
- 연속 프레임을 train · test에 나눠 넣으면 성능이 부풀려짐 → 촬영 세션 · 물체 개체 · 배경 단위로 분할
- val로 임계값 선택, test는 마지막에 한 번
- YOLO 클래스 예: `red_cylinder`, `red_prism`, `green_cylinder`, `green_prism` (한 객체에 상자 하나)
- CenterPose 라벨: 중심 1 + 꼭짓점 8의 `projected_cuboid`, `camera_data`, `scale`, `quaternion_xyzw` → 꼭짓점 순서를 PnP 3D 기준점 순서와 맞춤
- 태그 자세로 만든 pseudo-label을 같은 태그 자세와 비교하는 것은 **독립적인 정확도 검증이 아님**

## 학습
- PyTorch: Dataset → DataLoader → Model → Loss → Optimizer, $\theta \leftarrow \theta - \eta\, \nabla_\theta L$

```python
model.train()
for image, target in loader:
    optimizer.zero_grad()          # 이전 기울기 초기화
    loss = loss_fn(model(image), target)
    loss.backward()                # 역전파
    optimizer.step()               # 가중치 갱신
```

- 검증은 `model.eval()` + `torch.inference_mode()`. train loss 감소와 val 성능 개선은 다른 것 → 둘 다 기록
- YOLO: `yolov8n.pt`에서 자체 퍽 라벨로 파인튜닝. 색이 클래스 기준이면 hue 증강이 정답을 바꾸지 않는지 확인
- CenterPose 학습은 NVIDIA TAO 컨테이너 (`tao model centerpose train / evaluate / export`)

## 추적과 행동 정책
- 관측에 stamp · frame_id · source · unit 저장, 관측이 없으면 None (이전 값을 새 측정처럼 쓰지 않음)
- gating: 시간차 · 재투영 오차 · 태그 ID · 상자 겹침 · 양의 깊이를 통과한 후보만 연결 → ID 충돌 · 후보 여럿은 보류 후 재관측
- 시간 필터 $x_\text{est} = x_\text{pred} + K(z - Hx_\text{pred})$ ($K$는 칼만 이득, 카메라 $K$와 다름). 회전은 쿼터니언으로
- `track_id`(추적기 임시 번호) vs `tag_id`(물체 표식) → 새 track_id가 생겨도 tag_id로 같은 물체인지 확인
- 상태: SEARCH → CONFIRM → TRACK, 미검출 → LOST, 재검출 → CONFIRM, ID 충돌 · 오래된 측정 → HOLD(접근 · 집기 보류)
- **새 관측 없이 마지막 자세로 계속 움직이지 않음**
  - 교안 시작값: 연속 확인 3프레임, 유효 관측 최대 나이 0.3초, 허용 위치 변화 0.15m → 속도 · FPS · 지연에 맞춰 조정
- 검출기 지도학습과 행동 정책 학습은 다른 문제 → 지각 모델과 제어기 경계 유지, 최종 실행은 규칙으로 제한
- 모델별 단독 FPS 합 ≠ 통합 FPS. 큐가 쌓이면 오래된 영상을 버리고 최신 관측 우선
- 평가: 검출 Precision · Recall · mAP / 자세 위치 · 회전 · 재투영 오차 / 추적 ID 교체 · 재획득 시간
- 실패 영상을 고정하고 한 번에 한 조건만 바꿔 같은 rosbag으로 재시험

## Waffle 4WD 계획과 연결
- [261021](../261021/ROS2.md#태스크가-가능한-범위)에서 물체 자세를 Isaac ROS CenterPose로 받기로 함 → 이 교안이 그 관측 계층
- 상대 크기 → RealSense 깊이나 실측 퍽 치수로 스케일 검증. 팔 끝 Arducam ROI는 $K$ 보정 + 관측 시각 TF
- 강화학습 관측으로 쓸 때는 관측 나이 · LOST/HOLD 상태와 추정 잡음을 시뮬레이션에도 반영

## 실습
- 저장소 README와 velog 가이드: venv에 고정 버전 설치 → 한 장 추론 · COCO8 1 epoch로 점검 → 퍽 4클래스 라벨 검사 · 학습 · 평가 · 추적 · ONNX → Isaac ROS 컨테이너에서 TensorRT 엔진
- 주의: `sudo pip` 쓰지 않음, `configs/pucks.yaml`을 덮지 않고 `pucks-local.yaml` 생성, 저장소의 합성 퍽은 코드 흐름 확인용

```shell
python3 -m venv .venv-yolo && source .venv-yolo/bin/activate
python -m pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu128
python -m pip install numpy==1.26.4 opencv-python==4.11.0.86 ultralytics==8.3.221 onnx==1.17.0
yolo detect train model=yolov8n.pt data=coco8.yaml epochs=1 imgsz=640 batch=2 device=0

python scripts/validate_labels.py data/yolo/labels --classes 4
python scripts/train_yolo.py --data configs/pucks-local.yaml --epochs 50 --batch 4 --device 0
export YOLO_WEIGHTS=runs/detect/pucks/weights/best.pt   # 콘솔에 나온 실제 경로로
python scripts/track_yolo.py --weights "$YOLO_WEIGHTS" --source data/test.mp4 --device 0
python scripts/export_onnx.py --weights "$YOLO_WEIGHTS" --output models/pucks.onnx

# Isaac ROS 컨테이너
/usr/src/tensorrt/bin/trtexec --onnx=/models/puck.onnx --saveEngine=/models/puck.plan
```

- 실행 결과는 이 TIL에 기록하지 않음
