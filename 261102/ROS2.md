# Jetson 에지 컴퓨팅과 실시간 배포 (63~69강)

> 학습일·정리일 2026-11-02 / 자료: Jetson 에지 컴퓨팅과 실시간 배포 63–69강 (KANT, 로컬 `ref/ROS2/`에만 보관)
> 관련: [261019 CUDA·TensorRT 기초와 Isaac ROS](../261019/ROS2.md#cuda), [261021 도메인 랜덤화](../261021/ROS2.md#도메인-랜덤화)
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

- 역할 분리: **PC(RTX)** 시뮬레이션·학습 → **모델 패키지**(ONNX + 설정 + 해시) → **Jetson(Arm64)** TensorRT 추론과 ROS 2 → **MCU·구동기** 주기 제어와 타임아웃
- 버전 고정(강의 기준): JetPack 7.2 / Ubuntu 24.04, ROS 2 Lyrical + Isaac ROS release-5.0, Isaac Sim 6.1 + Isaac Lab v3.0.0-EA → 이름이 같아도 태그·CPU 아키텍처·드라이버가 다르면 재현 안 됨

## 63강 ONNX와 ONNX Runtime
- ONNX = 연산 그래프 + 가중치의 **전달 형식**일 뿐 → 변환 후 정확도 검사는 따로, GPU 속도 향상도 자동 아님
- ORT는 하나의 API 아래 **EP**(Execution Provider)가 하드웨어별 계산을 맡음
  - 미지원 연산은 **CPU fallback** → EP 경계마다 복사 + 대기 추가
  - TensorRT만 배포해도 ORT는 **변환 검증 기준선**으로 씀
- 입출력 계약 (YOLO 퍽 검출 예): 입력 `images` 1×3×640×640, float32 / RGB / NCHW, letterbox + 0~1 정규화, 후처리(conf·IoU·NMS·좌표 복원) 고정
  - 어긋나면 shape 불일치, 색·축 오독, 박스 밀림, 불공정한 mAP 비교
- 추론만 줄이면 이득이 제한됨 (교안 예시: 추론 12→9ms로 25% 감소해도 전체 20→17ms로 15% 감소)

### 정합 관문 (통과해야 다음 단계)
| 검사 | 방법 | 완료 기준 |
|---|---|---|
| 구조 | `onnx.checker` + 입출력 메타데이터 | 파싱 성공, 계약 일치 |
| 수치 | 같은 입력의 abs/rel 오차 | 허용 오차를 **미리** 정함 |
| 과제 | 같은 test 세트 mAP·성공률 | 기준 성능 유지 |
| 실행 | EP 프로파일·복사 구간 | 원치 않는 fallback 설명 |
| 제출 | ONNX·해시·환경·로그 | 다른 사람이 재실행 가능 |

## 64강 TensorRT와 양자화

### 빌드와 실행
- ONNX → 그래프 최적화 → **tactic**(실제로 고른 GPU 커널) 탐색 → 직렬화 엔진 `.plan`, 저장 때 GPU·TRT·CUDA·모델 해시 기록
- 엔진은 빌드한 GPU·TRT 버전용 → PC 엔진을 Jetson에 복사하는 것을 기본 경로로 삼지 않음
- 실행: Runtime → Engine → Context, 매 프레임 `enqueueV3`로 stream에 제출 → **제출 시점 ≠ GPU 완료 시점**
- Engine은 공유, 동시 추론은 Context를 여러 개로
- 이번 실습은 고정 shape(640) → 동적 shape보다 메모리·검증이 단순

### 정밀도와 INT8
- FP32 비교 기준 / FP16 범위 초과·작은 값 소실 검사 / INT8 분포 대표성·클리핑 검사 / 혼합은 민감 층만 높은 정밀도
- 선택 규칙: 허용 정확도를 만족하는 것 중 빠른 것. 속도만 오르고 집기 실패가 늘면 미채택

$$
q = \mathrm{clip}\big(\mathrm{round}(x/s) + z,\ -128,\ 127\big), \qquad \hat{x} = s\,(q - z)
$$

- $s$ 증가 → 이상치는 살지만 작은 차이 구분 못 함, 감소 → 범위 밖 값이 잘림
- 캘리브레이션 세트는 현장 대표: 물체·자세(가림)·빛(어둠·반사)·거리, 희귀 클래스 누락 금지, calibration / validation / test 분리
  - 수량보다 **빠진 상황 채우기**가 먼저 ([261021 랜덤화 축](../261021/ROS2.md#랜덤화하는-네-계열)과 같은 생각)
- Q/DQ로 양자화를 그래프에 표현해도 TensorRT는 지원 패턴만 INT8로 바꿈 → 레이어 dtype·fallback 확인

### TRT 10.x와 11.x를 섞지 않음
| 기능 | 10.x | 11.x |
|---|---|---|
| FP16 | `--fp16` (weak typing) | 모델 dtype/Cast로 표현 후 빌드 |
| INT8 | 기존 calibrator 또는 Q/DQ | Q/DQ 모델 → 빌드 |
| 전달 비용 측정 | 포함 옵션 확인 | 기본 제외, `includeDataTransfers` |

- 교안 예시: mAP 감소 FP16 0.2%p / INT8 1.4%p, 허용선 1.0%p → INT8은 바로 채택 불가
- 판정 지표는 모델마다 다름 (YOLO mAP50-95·클래스별 recall, 정책 성공률, Diffusion은 **K-step 전체 지연**)

## 65강 Jetson 배포 구조
- Orin Nano Super: Arm64 + Ampere GPU, **8GB 메모리를 CPU·GPU가 공유**, **DLA 없음** ([261019](../261019/ROS2.md#cuda) 표)
- 에지 = 데이터가 생기는 곳 가까이에서 계산. 네트워크가 끊길 수 있으니 **제어기의 독립 타임아웃** 필요
- 전력 모드·온도는 **실험 조건**: 모드 이름·클럭·온도 기록, 30분 이후 성능도 확인
  - 공식 화면은 JetPack 6.1 예시 → mode 번호를 7.2에 그대로 쓰지 않음
- 메모리 예산: 엔진·TRT workspace·카메라 버퍼·ROS 프로세스·여유를 나눠 기록
  - 공유 메모리라 프로세스별 값을 더하면 중복될 수 있음 → 시스템 전체 계측
- 배포 패키지 = 엔진 + ONNX 해시 + 전후처리 + ROS 노드(launch·QoS) + 운영 문서
  - 같은 `best.pt`라도 클래스 순서나 정규화가 바뀌면 다른 시스템
- 보드 검사: `cat /etc/nv_tegra_release`, `nvpmodel -q`(전력 모드), `tegrastats --interval 1000`(CPU·GPU·메모리·온도·전력)

## 66강 실시간성과 지연
- 입력 $t_0$, 결과 $t_1$, 다음 입력 $t_2$ → 지연 $= t_1 - t_0$, 주기 $= t_2 - t_0$, 지터 = 회마다 흔들리는 정도
- **FPS가 높아도 오래된 프레임을 처리하면 로봇은 늦게 반응**
- 지연 예산 (교안 예시, deadline 50ms): 캡처 5 / 전처리 3 / 추론 28 / 후처리 2 / 제어·통신 7 / 여유 5ms
  - 구간별 P99의 합 ≠ 전체 P99 → 전체도 따로 측정
- 꼬리 지연 (교안 예시): 조건 B가 P50 11ms로 A(12ms)보다 빠르지만 P99 48·최대 76ms로 50ms 초과 프레임 있음
- 꼬리 원인은 분리 실험으로 하나씩: 워밍업·할당, GPU/CPU 경쟁, 온도·클럭 제한, 주기 작업, 큐 적체
- 미스 정책: 정상 → 한 번 늦음(늦은 결과 폐기) → 연속 누락(HOLD + 경고) → 복구 검사 후 **명시적으로** 복귀
  - 파라미터: 마감, 결과 유효 시간, 연속 누락 허용 수, 복귀 조건
- PREEMPT_RT·우선순위·사전 할당·최신 프레임 슬롯·watchdog은 각각 한계가 있음 (예: PREEMPT_RT는 GPU 실행 시간을 보장 못 함)
- 실시간성 = 평균 속도가 아니라 **기한과 실패 대응의 설계**

## 67강 변환 실습
- 세 관문: 원본 → ONNX 출력 정합 / FP32 → FP16·INT8 과제 지표 / Jetson 지연·메모리 → 동작점 결정(채택 + 롤백)

```python
from ultralytics import YOLO
model = YOLO("runs/detect/<학습이름>/weights/best.pt")
model.export(format="onnx", imgsz=640, batch=1,
      dynamic=False, simplify=False, nms=False)
```
- class 순서·letterbox·NMS 설정 고정, `nms=False` → NMS와 좌표 복원은 후처리에서 따로 검증

```shell
# TensorRT 10.x (Jetson에서, 고정 shape ONNX)
trtexec --onnx=model.onnx --saveEngine=model_fp32.plan
trtexec --onnx=model.onnx --fp16 --saveEngine=model_fp16.plan

# TensorRT 11.x: 정밀도를 그래프에 표현한 뒤 빌드
trtexec --onnx=model_int8_qdq.onnx --saveEngine=model_int8.plan
```
- 10.x는 FP32 기준 엔진부터, 빌드 로그·엔진 해시·TRT 버전 저장
- 11.x는 `--fp16`, `--int8`, `--calib`를 그대로 붙이지 않음
- INT8 실패 분석: 입력(같은 입력 dump) → 분포(calibration 구성) → 연산(민감 층 FP16 유지) → 과제(조건별 오류) → 회복 못 하면 FP16 롤백
- 동작점 결정서: 모델·정밀도·엔진 SHA256, 정확도, P50/P99·메모리, 보드·전력 모드·버전, 빌드 명령·롤백 엔진 → 다른 팀원이 같은 엔진을 만들 수 있어야 함

## 68강 프로파일링
- "빠르다"가 GPU-only인지 capture-to-publish(E2E)인지 명시, **GPU 호출 반환 시각 ≠ GPU 작업 완료 시각**

```python
p50, p95, p99 = np.percentile(latency_ms, [50, 95, 99])
miss_rate = np.mean(latency_ms > deadline_ms)
```
- warm-up 이후 같은 범위로 측정, 분위수·미스율·**연속 미스**·표본 수 보고
- 동시 실행 (교안 예시, P99): YOLO 단독 12ms, 정책 단독 18ms, 둘 동시 39ms → 단독 성능을 더해 예측할 수 없음
- 에너지: $E = \int P(t)\,dt$, J/추론 $= E / N_{\text{완료}}$ → 전력이 낮아도 실행이 길면 추론당 에너지는 클 수 있음
- 30분 소크: 초반과 열 평형 이후의 시간창별 P99 비교, 초반 빠른 결과를 지속 성능으로 보고하지 않음
- 성능 시트는 **조건이 숫자보다 먼저**, 빈 칸은 "미측정"으로 두고 다른 장비 숫자로 채우지 않음

## 69강 ROS 2 통합
- 추론 노드: 구독 콜백은 **최신 슬롯만 교체** → 작업 스레드가 전처리 + TRT → 결과 age 검사(유효/폐기) → 발행, **원본 header 유지**
- `depth=1`과 결과 수명 검사를 같이 씀 (큐만 줄이면 처리 중인 옛 프레임 문제가 남음)

| QoS | 역할 | 주의 |
|---|---|---|
| History / depth | 대기 표본 수 제한 | 드라이버·앱 큐는 별개 |
| Reliability | best effort / reliable | 센서와 구독자 호환 확인 |
| Deadline | 기대 메시지 간격 감시 | GPU 완료 기한을 강제하지 않음 |
| Lifespan | 메시지 유효 기간 | 노드의 결과 age 검사도 필요 |
| Liveliness / watchdog | 노드·데이터 침묵 감시 | 구동기까지 타임아웃 연결 |

- 다중 모델(YOLO·CenterPose·AprilTag·정책)은 **요구 주기부터 배분**, 정책은 우선 실행, 진단·저장은 저속·비동기
- 장애 주입은 기대 반응을 **먼저** 적고 시험: 카메라 중단 → HOLD, 추론 종료 → 제어기 timeout 정지, 지연 → 늦은 결과 폐기
- 1시간 소크 합격선(E2E P99·미스 처리·메모리 증가 없음·온도·복구)을 미리 명세 → "한 시간 켜져 있었다" ≠ "요구사항을 만족했다"
- RUNBOOK: 기동(버전·해시 검사) → 정상 확인 → 이상 대응 → 롤백(이전 엔진·설정)
- 내 로봇: Waffle 4WD 카메라 3개 버퍼를 메모리 예산에 반영, [261021](../261021/ROS2.md#태스크가-가능한-범위) CenterPose 관측의 지연·유효 비율을 시뮬레이션에 반영, 통신 단절 시 멈추는 주체는 제어기 쪽 타임아웃

## 확인 문제 (내 답)
1. providers에 CUDA EP가 있는데도 느린 이유 후보는?
   - 미지원 연산의 CPU fallback으로 EP 경계마다 복사·대기 발생
2. FP16 mAP −0.2%p, INT8 −1.4%p, 허용선 1.0%p면?
   - FP16 채택. INT8은 실패 분석으로 허용선을 회복할 때만 재검토
3. QoS Deadline을 50ms로 걸면 추론이 50ms 안에 끝나는가?
   - 아님. 메시지 간격 위반을 알릴 뿐, 계산 기한은 age 검사와 미스 정책으로 처리
