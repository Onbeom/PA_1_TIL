# Jetson 에지 컴퓨팅과 실시간 배포 (63~69강)

> 학습일·정리일 2026-11-02 (자료를 받은 날 기준)
> 자료: Jetson 에지 컴퓨팅과 실시간 배포 · 63–69강 (KANT, 로컬 `ref/ROS2/`에만 보관)
> 관련: [261019 CUDA·TensorRT 기초와 Isaac ROS](../261019/ROS2.md#cuda), [261021 도메인 랜덤화](../261021/ROS2.md#도메인-랜덤화), [261021 정책 관측과 진단 정보 분리](../261021/ROS2.md#정책-관측과-진단-정보를-분리)
> 개념 정리이고 실습 결과는 아직 없음. 그래프 수치는 모두 **교안 예시 (Jetson 실측 아님)**

## 강의 구성
| 강 | 주제 | 남길 산출물 |
|---|---|---|
| 63 | ONNX Runtime | ONNX 정합 로그, EP·최적화 비교 |
| 64 | TensorRT와 양자화 | 정확도 허용선, 캘리브레이션 설계 |
| 65 | Jetson 배포 구조 | 자원 배치도, 버전 목록 |
| 66 | 실시간성과 지연 | 지연 예산, 미스 정책 |
| 67 | 변환 실습 | 엔진, 동작점 결정서 |
| 68 | 프로파일링 | 성능 시트, 30분 소크 |
| 69 | ROS 2 통합 | 1시간 통합 시험, RUNBOOK |

- 앞 강의 산출물이 다음 강의 입력이 됨
- 역할 분리: **PC(RTX)** 시뮬레이션·학습 → **모델 패키지**(ONNX + 설정 + 해시) → **Jetson(Arm64)** TensorRT 추론과 ROS 2 → **MCU·구동기** 주기 제어와 타임아웃
- 버전 고정(강의 기준): JetPack 7.2 / Ubuntu 24.04, ROS 2 Lyrical + Isaac ROS release-5.0, Isaac Sim 6.1 + Isaac Lab v3.0.0-EA(main은 6.2용), TensorRT·CUDA·ORT는 설치된 정확한 버전 기록
  - 이름이 같아도 태그·CPU 아키텍처·드라이버가 다르면 재현 안 됨
  - [261019](../261019/ROS2.md) 강의는 Sim 6.2 기준이었고 이번 덱은 6.1 조합임

---

## 63강 ONNX와 ONNX Runtime

### 이름 구분
| 이름 | 정체 | 이번 실습 역할 |
|---|---|---|
| PyTorch | 모델 정의·학습 프레임워크 | 학습된 모델과 기준 출력 |
| ONNX | 연산 그래프 + 가중치 교환 형식 | PC → Jetson 전달 파일 |
| ONNX Runtime (ORT) | ONNX 실행 런타임 | CPU·CUDA·TensorRT EP로 실행 |
| TensorRT | NVIDIA 추론 최적화 SDK | 대상 GPU용 엔진 빌드·실행 |
| TensorRT 엔진 | 최적화된 실행 계획 | Jetson에서 로드하는 `.plan` |

- ONNX는 **전달 형식**일 뿐 → 변환 후 정확도 검사는 따로, GPU 속도 향상도 자동 아님
- 파일 구조: ModelProto(IR 버전·opset) > GraphProto(입출력·노드·initializer) > NodeProto(Conv·MatMul 같은 연산) / TensorProto(가중치) / ValueInfoProto(입출력 이름·dtype·차원 = 런타임 입력 계약)
- 공식 예 선형 회귀 $Y = XA + B$: A·B는 학습으로 정해진 **initializer**, X는 매 프레임 바뀌는 **입력**

### 입출력 계약 (YOLO 퍽 검출 예)
| 항목 | 값 | 잘못 바꾸면 |
|---|---|---|
| 입력 | `images` / 1×3×640×640 | shape 불일치 |
| dtype·채널 | float32 / RGB / NCHW | 색·축을 잘못 읽음 |
| 전처리 | letterbox + 0~1 정규화 | 박스 좌표가 한쪽으로 밀림 |
| 후처리 | conf·IoU·NMS·좌표 복원 고정 | mAP 비교가 불공정 |

- 출력 차원은 실제 ONNX 메타데이터로 확인한 뒤 ROS 디코더 연결
- 보충: letterbox = 비율 유지 축소 + 남는 곳 패딩으로 정사각형 입력을 만드는 것 → 박스를 원본 좌표로 돌릴 때 패딩·배율을 역으로 적용

### 연산 융합과 실행 제공자(EP)
- 융합: Conv → BatchNorm → ReLU를 따로 돌리면 중간 결과를 메모리에 썼다 다시 읽음 → 한 커널로 합쳐 왕복 감소 (전체 지연 효과는 측정해야 앎)
- ORT는 하나의 API 아래 **EP**(Execution Provider)가 하드웨어별 계산을 맡음
  - EP가 지원하는 부분 그래프만 그 EP에 배정, 미지원 연산은 **CPU fallback**
  - CUDA → CPU → CUDA처럼 경계가 생기면 **복사 + 대기** 추가 → providers에 GPU가 있어도 전부 GPU에서 도는 건 아님
- TensorRT만 배포해도 ORT는 **변환 검증 기준선**으로 씀 (CPU EP로 입출력 오류부터 분리)

```python
so = ort.SessionOptions()
so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
so.enable_profiling = True
sess = ort.InferenceSession("model.onnx", so,
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
```

- 추론만 줄이면 이득이 제한됨 (교안 예시, 전처리 + 추론 + 전달·후처리)
  - 기준 3 + 12 + 5 = 20ms → 그래프 최적화 3 + 9 + 5 = 17ms → 복사 감소 3 + 9 + 2 = 14ms
  - 추론은 25% 줄었는데 전체는 15%만 줄어듦
  - 보충(암달의 법칙): 비율 $p$인 구간을 $k$배 빠르게 하면 전체는 $(1-p) + p/k$ 배 → $p=0.6,\ k=4/3$이면 $0.85$

### 정합 관문 (통과해야 다음 단계)
| 검사 | 방법 | 완료 기준 |
|---|---|---|
| 구조 | `onnx.checker` + 입출력 메타데이터 | 파싱 성공, 계약 일치 |
| 수치 | 같은 입력의 abs/rel 오차 | 허용 오차를 **미리** 정함 |
| 과제 | 같은 test 세트 mAP·성공률 | 기준 성능 유지 |
| 실행 | EP 프로파일·복사 구간 | 원치 않는 fallback 설명 |
| 제출 | ONNX·해시·환경·로그 | 다른 사람이 재실행 가능 |

---

## 64강 TensorRT와 양자화

### 빌드와 실행
- ONNX → 그래프 최적화 → **tactic** 탐색·workspace 선택 → 직렬화 엔진 `.plan`
  - tactic: 같은 계산을 하는 여러 구현 중 실제로 고른 GPU 커널
  - 빌드 단계 객체: Parser → NetworkDefinition(연결·dtype·동적 차원) → BuilderConfig(workspace 상한·profile·플러그인)
  - 엔진 저장 때 GPU·TRT·CUDA·모델 해시 기록
- PC에서 만든 엔진을 Jetson에 복사하는 것을 기본 경로로 삼지 않음
  - 보충: 엔진은 빌드한 GPU와 TensorRT 버전에 맞춘 계획이라 대상 장치에서 빌드
- 실행 단계 객체: Runtime(엔진 역직렬화, 시작 때 1번) → Engine → Context(버퍼·CUDA stream 준비)
  - 매 프레임: 입력 shape·tensor address 설정 → `execute_async_v3` / `enqueueV3`로 stream에 제출 → 동기화 후 출력 사용·결과 age 검사
  - **제출 시점 ≠ GPU 완료 시점** (비동기)
  - Engine은 공유, 동시 추론은 Context를 여러 개로 (보충: Context 하나를 여러 스레드가 동시에 쓰지 않음)
- 동적 shape: 최적화 프로파일 min 1×3×320×320 / opt 640 / max 960 → 경계값과 실제 해상도에서 정확도·지연·메모리 확인
  - 고정 shape(모두 640)가 메모리·검증이 단순 → 이번 실습은 고정

### 정밀도
| 표현 | 방식 | 판단 |
|---|---|---|
| FP32 | 넓은 범위·높은 정밀도 | 비교 기준, 민감 연산 |
| FP16 | 16비트 부동소수점 | 범위 초과·작은 값 소실 검사 |
| INT8 | 정수 + scale/zero point | 분포 대표성·클리핑 검사 |
| 혼합 | 연산별 dtype / Q/DQ | 민감 층은 높은 정밀도 유지 |

- 목적: 제한된 자원에서 **필요한 주기 확보**. 비트를 줄여도 정확도 유지나 일정한 배속은 보장 안 됨
- 과제 확인점: FP16은 작은 퍽·멀리 있는 태그 주변 오차, INT8은 어둠·반사·가림이 들어간 대표 데이터
- 선택 규칙: 허용 정확도를 만족하는 것 중 빠른 것. 속도만 오르고 집기 실패가 늘면 미채택

### INT8 양자화
$$
q = \mathrm{clip}\big(\mathrm{round}(x/s) + z,\ -128,\ 127\big), \qquad \hat{x} = s\,(q - z)
$$

- $s$: 눈금 간격(scale), $z$: zero point, $\hat{x}$: 복원값
- 범위를 넓히면($s$ 증가) 이상치는 살지만 작은 차이를 구분 못 함, 좁히면 범위 밖 값이 잘림
- 보충: 대칭 양자화($z=0$)에서 흔히 $s = \max|x| / 127$, 범위 안 값의 반올림 오차는 최대 $s/2$
- 캘리브레이션 세트는 현장을 대표해야 함
  - 물체(빨강·초록, 직육면체·원기둥), 자세(서기·눕기·부분 가림), 빛(밝음·어두움·아크릴 반사), 거리(크게·작게)
  - 희귀 클래스 누락 금지, 같은 장면 연속 프레임이 세트 사이로 새지 않게, calibration / validation / test 분리
  - 대표 샘플 수백 장부터. 수량보다 **빠진 상황 채우기**가 먼저 ([261021 랜덤화 축](../261021/ROS2.md#랜덤화하는-네-계열)과 같은 생각)
- Q/DQ: QuantizeLinear(실수 → 정수)와 DequantizeLinear(정수 → 계산용 실수)를 그래프에 넣어 양자화를 표현
  - 가중치와 activation은 범위가 달라 채널별·텐서별 설정을 따로
  - TensorRT는 지원 패턴만 저정밀 커널로 바꿈 → INT8 파일이어도 전부 INT8로 도는 건 아님 (레이어 dtype·fallback 확인)

### TRT 10.x와 11.x를 섞지 않음
| 기능 | 10.x | 11.x |
|---|---|---|
| FP16 | `--fp16` (weak typing) | 모델 dtype/Cast로 표현 후 빌드 |
| INT8 | 기존 calibrator 또는 Q/DQ | Q/DQ 모델 → 빌드 |
| 민감 층 | precision 설정 | 그래프에 dtype으로 표현 |
| 전달 비용 측정 | 포함 옵션 확인 | 기본 제외, `includeDataTransfers` |

### 속도와 정확도를 함께 결정 (교안 예시)
- mAP 감소: FP32 0 / FP16 0.2%p / INT8 1.4%p → 허용선 1.0%p면 INT8은 바로 채택 불가
- 모델마다 판정 지표가 다름
  - YOLO: mAP50-95, 클래스별 recall (작은 물체·가림·오검출)
  - BC 정책: 성공률, 행동 오차 (접촉 직전 미세 행동)
  - Diffusion 정책: 성공률, **K-step 전체 지연** (seed·denoise step 고정)
  - 퍽 CenterPose: 중심 mm 오차, 축·대칭 오차, 유효 출력 비율
  - AprilTag: ID recall, 오ID, 위치 오차 (검출기가 애초에 DNN 양자화 대상인지 구분)

---

## 65강 Jetson 배포 구조

### Orin Nano Super의 조건
- Arm64 CPU + Ampere GPU, **8GB 메모리를 CPU·GPU가 공유**, 전력·온도·대역폭이 함께 제한 ([261019](../261019/ROS2.md#cuda) 표)
- **Nano Super에는 DLA가 없음** → Orin NX·AGX의 자원 배치를 그대로 옮기지 않음
- 에지 컴퓨팅 = 데이터가 생기는 곳 가까이에서 계산. 로봇이 이동하고 네트워크가 끊길 수 있으니 매 프레임을 서버로 보내지 않음
  - 그래도 필요한 것: 전원·냉각·메모리 예산, **제어기의 독립 타임아웃**
- 로봇 사진은 부품보다 경계로 읽음: 카메라 → 관측 / 모델 → 행동 추정 / 제어기 → 구동 명령

### 전력 모드·메모리·패키지
- 전력 모드와 온도는 **실험 조건**: 모드 이름·클럭·온도 기록, 실제 제공 모드만 비교, 30분 이후 성능도 확인
  - 공식 화면은 JetPack 6.1 때 예시 → mode 번호를 7.2에 그대로 쓰지 않음

| 메모리 사용처 | 기록할 값 | 바꿀 수 있는 것 |
|---|---|---|
| 엔진·가중치 | 로드 전후 차이 | 모델 크기·정밀도 |
| TRT workspace | 빌드/실행 피크 | tactic, 동시 실행 |
| 카메라·텐서 | 해상도 × dtype × 버퍼 수 | 버퍼 재사용, 큐 제한 |
| ROS·시스템 | 프로세스 RSS, 전체 사용량 | 컴포지션, 불필요 서비스 |
| 여유 | 실측 피크 대비 | 누수·일시 부하 대비 |

- 공유 메모리라 프로세스별 값을 더하면 중복될 수 있음 → 시스템 전체 계측으로 확인
- 보충 계산: 1×3×640×640 float32 = $3 \times 640 \times 640 \times 4\,\text{B} \approx 4.9\,\text{MB}$, 버퍼 3개면 약 15MB
- 배포 패키지 = 엔진 + ONNX 해시 → 전후처리(클래스·shape) → ROS 노드(launch·QoS) → 운영 문서(감시·롤백)
  - 같은 `best.pt`라도 클래스 순서나 정규화가 바뀌면 다른 시스템
- 공식 벤치마크(Nano → Nano Super, ViT 계열, FP16)의 배속을 내 YOLO에 대입하지 않음

### 보드 인수 검사
```shell
uname -m
cat /etc/nv_tegra_release
python3 -c "import tensorrt as t; print(t.__version__)"
nvpmodel -q
tegrastats --interval 1000
```
- aarch64·OS(`/etc/os-release`)·BSP·TensorRT·전력 모드를 한 세트로 보관, `ROS_DISTRO`·패키지 버전·엔진 SHA256도 기록
- `nvpmodel -q`: 현재 전력 모드 조회 / `tegrastats --interval 1000`: 1000ms 간격으로 CPU·GPU·메모리·온도·전력 출력

---

## 66강 실시간성과 지연

### 주기·지연·지터
- 입력 발생 $t_0$, 결과 도착 $t_1$, 다음 입력 $t_2$ → 지연 $= t_1 - t_0$, 주기 $= t_2 - t_0$, 지터 = 회마다 흔들리는 정도(정의를 기록에 명시)
- **FPS가 높아도 오래된 프레임을 처리하면 로봇은 늦게 반응**
  - 보충: FPS는 처리량($1/\text{주기}$), 지연은 한 프레임이 겪는 시간 → 파이프라인이면 30FPS이면서 지연 100ms도 가능

### 지연 예산 (교안 예시, deadline 50ms)
| 구간 | 예산 | 측정점 |
|---|---|---|
| 캡처 | 5ms | 센서 timestamp → 수신 |
| 전처리 | 3ms | 수신 → tensor 준비 |
| 추론 | 28ms | GPU 작업 시작 → 완료 |
| 후처리 | 2ms | 출력 → 검출/행동 |
| 제어·통신 | 7ms | 판단 → 명령 도착 |
| 여유 | 5ms | 남는 몫 |

- 구간별 P99의 합 ≠ 전체 P99 (각 구간의 최악이 같은 프레임에 겹치지 않음) → 전체도 따로 측정

### 꼬리 지연 (교안 예시)
| | P50 | P95 | P99 | 최대 |
|---|---|---|---|---|
| 조건 A | 12 | 15 | 20 | 31ms |
| 조건 B | 11 | 19 | 48 | 76ms |

- 중앙값은 B가 빠른데 B는 50ms를 넘는 프레임이 있음
- 꼬리 원인은 분리 실험으로 하나씩
  - 초반 급증 → 워밍업·할당 (초기화 후 구간만 비교)
  - 동시 노드 때 급증 → GPU/CPU 경쟁 (단독 ↔ 동시)
  - 온도와 함께 상승 → 클럭 제한 (온도·클럭 동시 로그)
  - 주기적 스파이크 → GC·주기 작업 (trace 대조)
  - 수신 지연 증가 → 큐 적체·네트워크 (입력 age·queue depth)
- 패턴이 비슷해 보인다고 원인을 확정하지 않음

### 미스 정책과 실시간 수단
- 정상(유효 결과 사용) → 한 번 늦음(늦은 결과 폐기) → 연속 누락(HOLD + 경고) → 복구 검사(조건 만족 시 **명시적으로** 복귀)
  - 파라미터: 마감, 결과 유효 시간, 연속 누락 허용 수, 복귀 조건

| 수단 | 기대 효과 | 해결 못 하는 것 |
|---|---|---|
| PREEMPT_RT | 스케줄링 꼬리 감소 | GPU 실행 시간 보장 |
| 우선순위·코어 배치 | CPU 간섭 완화 | 잘못 정한 우선순위 역전 |
| 사전 할당 | 핫루프 할당 변동 감소 | 모델 자체 연산량 |
| 최신 프레임 슬롯 | 백로그 제한 | 처리 중인 옛 프레임 취소 |
| watchdog | 침묵·기한 초과 대응 | 시스템 전체 안전 인증 |

- 실시간성 = 평균 속도가 아니라 **기한과 실패 대응의 설계**

---

## 67강 변환 실습

- 세 관문: 원본 → ONNX 출력 정합 / FP32 → FP16·INT8 과제 지표 / Jetson 지연·메모리 → 동작점 결정(채택 + 롤백)
  - 실패하면 다음 최적화로 가기 전에 원인 기록

```python
from ultralytics import YOLO
model = YOLO("runs/detect/<학습이름>/weights/best.pt")
model.export(format="onnx", imgsz=640, batch=1,
      dynamic=False, simplify=False, nms=False)
```
- 바꿀 것: 체크포인트 경로, 검증한 입력 크기 / 고정: class 순서, letterbox, NMS 설정 / 확인: 실제 input·output 이름·shape·dtype
- `nms=False` → NMS와 원본 좌표 복원을 후처리에서 따로 검증

```shell
# TensorRT 10.x (Jetson에서, 고정 shape ONNX)
trtexec --version
trtexec --onnx=model.onnx --saveEngine=model_fp32.plan
trtexec --onnx=model.onnx --fp16 --saveEngine=model_fp16.plan

# TensorRT 11.x: 정밀도를 그래프에 표현한 뒤 빌드
python -m modelopt.onnx.autocast \
 --onnx_path model.onnx --output_path model_fp16.onnx
trtexec --onnx=model_fp16.onnx --saveEngine=model_fp16.plan
trtexec --onnx=model_int8_qdq.onnx --saveEngine=model_int8.plan
```
- 10.x: FP32 기준 엔진부터. TF32 허용 여부도 기록 (보충: Ampere는 FP32 연산 일부를 TF32로 처리할 수 있어 "FP32 기준"이 무엇인지 남김), 빌드 로그·엔진 해시·TRT 버전 저장
- 11.x: INT8 입력은 대표 데이터로 캘리브레이션을 끝낸 오프라인 Q/DQ 모델. `--fp16`, `--int8`, `--calib`를 그대로 붙이지 않음
- 정책은 행동까지 검증
  - BC: 관측 → 행동 직접 예측 (관측 이력·행동 형식 비교)
  - Diffusion: 노이즈에서 K번 복원해 행동 생성 → 한 스텝이 아니라 대략 $K \times$(한 스텝) + 전후처리가 정책 지연
- INT8 실패 분석 순서
  1. 입력: RGB·정규화·shape가 같은가 → 같은 입력 dump 비교
  2. 분포: 어두운·반사 장면이 빠졌나 → calibration 구성 변경
  3. 연산: 특정 층에서 오차가 커지나 → 민감 층 FP16 유지
  4. 과제: 어떤 클래스·자세에서 실패하나 → 조건별 오류 지도
  5. 채택: 허용선 회복 못 하면 FP16 롤백 (속도로 정확도 실패를 정당화하지 않음)
- 공식 영상의 Torch-TensorRT는 ONNX를 거치지 않는 PyTorch 통합 경로 → ONNX 경로와 비교 대상
- 동작점 결정서: 선택(모델·정밀도·엔진 SHA256), 정확도(기준 대비/허용선), 성능(P50/P99·처리율·메모리), 조건(보드·전력 모드·shape·버전·열 상태), 데이터 목록·해시, 빌드 명령·로그·롤백 엔진
  - 이 문서만 보고 다른 팀원이 같은 엔진을 만들 수 있어야 함

---

## 68강 프로파일링

- 측정 범위부터: 카메라 timestamp → 전처리 시작/끝 → GPU 시작/완료(CUDA event) → 결과 발행(frame age)
  - **GPU 호출 반환 시각 ≠ GPU 작업 완료 시각**
  - "빠르다"가 GPU-only인지 capture-to-publish(E2E)인지 명시

```python
p50, p95, p99 = np.percentile(latency_ms, [50, 95, 99])
miss_rate = np.mean(latency_ms > deadline_ms)
```
- `latency_ms`는 warm-up 이후 같은 범위로 잰 배열
- 매 프레임 print 대신 사전 할당 버퍼에 `frame_id, capture_stamp, pre, infer, post, publish`를 모아 나중에 분석
- 보고: 분위수·미스율·**연속 미스**·표본 수 (보충: 표본 1000개의 P99는 꼬리 10개로 정해져 흔들리기 쉬움)
- 동시 실행 비용 (교안 예시, P99): YOLO 단독 12ms, 정책 단독 18ms, **둘 동시 39ms**, 주기 조정 후 24ms
  - 단독 합 30ms보다 큼 → 단독 성능을 더해 시스템 성능을 예측할 수 없음

### 전력과 에너지
| 지표 | 계산·계측 | 해석 |
|---|---|---|
| 모듈 전력 | tegrastats 레일·단위 확인 | 센서·팬·외부 장치 포함 여부 |
| 전체 전력 | 입력 전력계 | 로봇 배터리 예산 |
| 총 에너지 | $E = \int P(t)\,dt$ | 측정 구간 명시 |
| J/추론 | $E / N_{\text{완료}}$ | 실패·드롭 처리 기준 명시 |
| 동적 에너지 | $\int (P(t) - P_{\text{idle}})\,dt$ | 총 에너지와 구분 |

- 전력이 낮아도 실행 시간이 길면 추론당 에너지는 커질 수 있음 (보충 예: 10W × 20ms = 0.2J, 7W × 40ms = 0.28J)

### 30분 소크와 성능 시트
- 대표 부하 30분 → 온도·클럭 로그 → 시간창별 P99 → 초반과 열 평형 이후 비교
  - 초반 몇 초의 빠른 결과를 지속 성능으로 보고하지 않음 (보충: 온도가 오르면 클럭이 내려가는 스로틀링)
- 성능 시트는 **조건이 숫자보다 먼저**: 환경(보드·OS·JetPack·TRT·전력 모드), 입력(해상도·배치·dtype·공급 방식), 범위(GPU-only/E2E·warm-up·표본 수), 분포(P50/P95/P99/max·miss·연속 미스), 자원(메모리·전력·J/추론), 지속성(30분 온도·클럭·시간창 P99)
  - 빈 칸은 "미측정"으로 두고 다른 장비 숫자로 채우지 않음

---

## 69강 ROS 2 통합

- ROS 2로 묶는 이유: 영상·CameraInfo·TF의 timestamp 정합, 결과를 다른 기능이 토픽으로 사용, 기능별 주기 차이(QoS·큐·실행기·age 정책), 운영 중 진단·watchdog·재시작
  - ROS 2는 학습 도구가 아니라 센서·추론·계획·제어를 함께 돌게 하는 연결 기반

### 추론 노드 구조
- 구독 콜백은 **최신 슬롯만 교체** → 작업 스레드가 전처리 + TRT → 결과 age 검사(유효/폐기) → 발행 + 진단, **원본 header 유지**
- `depth=1`과 결과 수명 검사를 같이 씀 (큐만 줄이면 처리 중인 옛 프레임 문제가 남음)
- 원본 stamp를 유지해야 뒤쪽 노드가 $\text{age} = t_{\text{now}} - t_{\text{stamp}}$로 신선도 판단

| QoS | 역할 | 주의 |
|---|---|---|
| History / depth | 대기 표본 수 제한 | 드라이버·앱 큐는 별개 |
| Reliability | best effort / reliable | 센서와 구독자 호환 확인 |
| Deadline | 기대 메시지 간격 감시 | GPU 완료 기한을 강제하지 않음 |
| Lifespan | 메시지 유효 기간 | 노드의 결과 age 검사도 필요 |
| Liveliness / watchdog | 노드·데이터 침묵 감시 | 구동기까지 타임아웃 연결 |

- 명령의 신선도는 앱과 제어기에서도 검사
- 보충: Reliability는 발행 best effort + 구독 reliable 조합이면 연결 안 됨

### 시뮬 카메라 → Jetson, 퍽 인식
- PC Isaac Sim 6.1(RGB + CameraInfo) → ROS 2 bridge(시간·QoS) → 유선망·DDS(도메인·방화벽) → Jetson Lyrical(추론 → 진단)
  - 이미지 한 장과 CameraInfo부터 확인한 뒤 모델을 붙임
  - 공식 YOLOv8 비교표(A100·CPU 기준)를 Nano Super 속도로 해석하지 않음
- 퍽 인식의 세 출력은 의미가 다름
  - YOLO: 종류·색·박스·신뢰도 → 물체 후보
  - CenterPose(필요하면 YOLO ROI): 중심·자세·유효성
  - AprilTag(같은 영상 + CameraInfo): ID·태그 pose
  - 후단에서 시간·좌표계·면 가설을 검사해 물체별 상태로 통합 (태그 위치와 물체 중심은 TF로 연결)
- 시험 입력은 실제 프로젝트 합성 장면: 고정 seed 평가 세트, 조명·반사·가림 조건 분리, 위치·자세 GT 보관
  - 4K 렌더링은 데이터 생성 조건일 뿐, 추론 입력 크기는 따로
- 다중 모델은 **요구 주기부터 배분**: 검출은 이동 속도(입력 크기·주기 조정), 중심·자세는 집기 오차(ROI·유효 검출만), 태그는 ID 변화 빈도(별도 주기·추적 재사용), 정책은 제어 안정성(우선 실행), 진단·저장은 저속·비동기

### 장애 주입과 1시간 소크
| 주입 | 기대 반응 | 증거 |
|---|---|---|
| 카메라 발행 중단 | 입력 timeout → HOLD | 중단 → HOLD 시간 |
| 추론 프로세스 종료 | 제어기 timeout → 정지 | 마지막 명령 이후 로그 |
| 지연 주입 | 늦은 결과 폐기 | age·drop·연속 miss |
| 부하 증가 | 감시·보조 주기 조정 | P99·온도·클럭 |
| 복구·재시작 | 조건 확인 뒤 복귀 | 재연결, 중복 명령 없음 |

- 기대 반응을 **먼저** 적고 주입. 로봇 형상이 없는 단계라 상태 전이와 메시지 경로부터 검증
- 1시간 소크 합격선을 미리 명세: E2E(시간창별 P99 + 초과율), 미스 처리, 워밍업 후 메모리 증가 없음, 온도·클럭, 초반·후반 같은 과제 평가, 복구
  - "한 시간 켜져 있었다" ≠ "요구사항을 만족했다"
- RUNBOOK: 기동(버전·해시 검사) → 정상 확인(토픽·진단·결과) → 이상 대응(증상 → 조치) → 롤백(이전 엔진·설정)
  - 최종 산출물 = 엔진 + 노드 + 설정 + 성능 시트 + 운영 절차

### 내 로봇에 옮길 때 생각할 것
- Waffle 4WD는 Jetson에 카메라 3개(RealSense 2, Arducam 1)를 씀 → 카메라 버퍼를 메모리 예산표에 카메라별로 적어야 함
- [261021](../261021/ROS2.md#태스크가-가능한-범위)에서 계획한 CenterPose 관측은 지연·유효 비율을 재서 시뮬레이션 관측의 지연·잡음에 반영
- 통신 단절 시 멈추는 주체는 제어기 쪽 타임아웃 (Jetson이 죽어도 동작해야 함)

---

## 확인 문제 (내 답)
1. ONNX 출력값은 원본과 비슷한데 박스 위치만 어긋나면 먼저 볼 것은?
   - letterbox 복원 (패딩·배율을 원본 좌표로 되돌리는 후처리)
2. providers에 CUDA EP가 있는데도 느린 이유 후보는?
   - 미지원 연산의 CPU fallback으로 EP 경계마다 복사·대기 발생 → 프로파일로 노드 배치 확인
3. FP16 mAP −0.2%p, INT8 −1.4%p, 허용선 1.0%p면?
   - FP16 채택. INT8은 실패 분석으로 허용선을 회복할 때만 재검토
4. 통신이 끊기면 누가 멈추는가?
   - 구동기 쪽 제어기(MCU)의 독립 타임아웃
5. P50이 더 빠른 조건이 더 나쁠 수 있는 이유는?
   - 꼬리(P99·max)가 deadline을 넘을 수 있음. 초과율과 연속 미스로 판단
6. QoS Deadline을 50ms로 걸면 추론이 50ms 안에 끝나는가?
   - 아님. 메시지 간격 위반을 알릴 뿐, 계산 기한은 노드의 age 검사와 미스 정책으로 처리
7. "빠르다", "다시 만들 수 있다"는 무엇으로 증명하나?
   - 측정 범위(GPU-only/E2E)·warm-up·표본 수·열 평형 이후 P99 / 해시·입력 계약·빌드 명령·데이터 목록
