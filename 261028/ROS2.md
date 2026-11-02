# 팀별 로봇 자율주행 2 — nvblox·Nav2·예측 카메라 정책

> 학습일 2026-10-28 (자료를 받은 날), 정리일 2026-11-02
> 자료: 팀별 로봇 자율주행 2 — nvblox·Nav2·예측 카메라 정책 (KANT, 로컬 `ref/ROS2/`에만 보관). 시연 로봇은 교안 저장소의 M38
> 이전: [261027 팀별 로봇 미로 주행 — 보상 설계·cuVSLAM·Nav2 실습](../261027/ROS2.md)
> 기초는 링크로: Nav2·costmap·AMCL [261015](../261015/ROS2.md), PPO·VSLAM·Sim to Real [261019](../261019/ROS2.md), 태스크 구성·내 로봇 Waffle 4WD [261021](../261021/ROS2.md)
> 실습은 교안 순서대로 진행 (실행 결과는 이 TIL에 기록하지 않음)

## 1. 전체 흐름과 이번 범위
- 목표 파이프라인
  - 깊이 영상 → **nvblox** 거리 지도 → **Nav2** 비용지도 → 경로 재계획 → 경로를 **정책 관측**으로 → 속도 명령
  - 여기에 차체 주행과 팔 카메라 제어를 연결 (경로 앞쪽을 팔 카메라가 미리 봄 = "예측 카메라")
- 저장소에 있는 것과 없는 것을 먼저 구분

| 구분 | 내용 |
|---|---|
| 제공 | URDF·USD·메시·`model_parameters.json`, 가상 고정 스테레오 카메라(`m38_stereo.usda`), 정적 검사·렌더 스크립트, `launch/cuvslam_sim.launch.py` 초안, 문서(`UBUNTU_SETUP.md`, `CAMERA_AND_TF.md`) |
| 추가 작성 | ROS 센서 그래프, nvblox·Nav2 설정, 정책 task·경로 어댑터 |
| 확장 설계(미포함) | nvblox·Nav2·PPO 통합, 이중 IMU·EKF·AMCL |

- 0.95 m/s는 기존 설계 예시일 뿐 → 실제 속도 제한은 팀별로 검증
- 버전 기준은 `versions.json`: Ubuntu 24.04 / Python 3.12 / Isaac Sim 6.1.0.0 / Isaac ROS release-5.0 / ROS 2 Lyrical / Isaac Lab v3.0.0-EA
  - 스크립트가 6.1.0.0만 허용 → 6.2로 임의 교체 금지 ([261019](../261019/ROS2.md) 강의 기준 조합은 6.2였으니 혼동 주의)
  - nvblox 전용 설치 스크립트 없음, 대상 Ubuntu에서의 실행도 미검증

## 2. 저장소로 시작하는 4단계
### 01 모델 정적 검사
```shell
python3 -m venv .venv-check
.venv-check/bin/pip install usd-core
.venv-check/bin/python scripts/validate_model.py
```
- 결과 `checks/model_validation.json`: `status = PASS_STATIC_ONLY`, 16 links / 15 joints / 13 movable (교안 예시)
- 검사 내용: 누락 메시, 트리 순환, 스테레오 기준선, 광학축
- **정적 PASS는 주행 성공이 아님** (실행 전 구조만 본 것)

### 02 스테레오 렌더
```shell
source .venv-sim61/bin/activate
python scripts/render_stereo.py --headless
```
- 결과: `checks/sim61_left.png`, `sim61_right.png`, `sim61.json` → 640×480, 좌우 시야, 시차 확인
- 렌더 성공 ≠ ROS 발행. 물리 구동·주행 검사는 다음 단계
- 현재 스크립트는 **RGB만** 생성 → 깊이 입력은 별도 구현 필요

### 03 ROS 입력 연결
- Sim 그래프에 추가할 것: 좌·우 Camera → RenderProduct → Image + CameraInfo 동시 발행, `/clock`·`/joint_states`, robot_state_publisher로 TF
- 좌우 영상은 **같은 스텝 timestamp**, 30 Hz부터 측정, QoS 일치

```shell
ros2 topic echo /clock --once
ros2 run tf2_ros tf2_echo base_link sim_left_optical
```
- 좌·우 `image_rect_color`의 hz, CameraInfo의 K·P·frame_id까지 확인

### 04 cuVSLAM 실행
```shell
source /opt/ros/lyrical/setup.bash
ros2 pkg prefix isaac_ros_cuvslam
ros2 launch ./launch/cuvslam_sim.launch.py
```
- launch는 영상을 발행하지 않음 → 좌우 영상·CameraInfo·TF가 먼저 있어야 함. 현재 `enable_imu_fusion=false`
- 추적 시험: 정지 → 직진 → 좌우 → 제자리 회전 → 같은 경로로 시작점 복귀. 초기화 시간·추적 손실·오차 기록
- 주의
  - 추정값과 ground truth를 분리해서 기록, 시간·좌표를 정렬한 뒤 오차 비교
  - **같은 TF를 두 노드가 발행하지 않기** (예: cuVSLAM과 다른 오도메트리가 둘 다 `odom→base_link`)

## 3. 카메라: 차체 고정 vs 팔 부착
| 항목 | 현재 저장소 (차체 고정) | 팔 부착형으로 바꿀 때 |
|---|---|---|
| TF | `base_link → sim_left/right_optical` (고정) | parent를 실제 팔 링크로, USD 카메라 경로도 같이 변경 |
| 위치 | (0.25, ±0.025, 0.25) m, 기준선 0.05 m | 관절값 $q(t)$ + 고정 장착 변환으로 FK |
| 내부 파라미터 | 640×480, $f_x = f_y = 400$ px (합성값, 실측 아님) | 실물 보정값 |
| 처리 | 고정이라 시각 문제 적음 | **촬영 시각의 TF를 조회한 뒤** 영상 처리 |

- 보충: 스테레오 깊이 $Z = \dfrac{f_x B}{d}$ ($B$ 기준선, $d$ 시차 px)
  - 교안 값이면 $Z = 400 \times 0.05 / d = 20/d$ m → $d = 10$ px일 때 2 m
  - 깊이 오차 $\Delta Z \approx \dfrac{Z^2}{f_x B}\Delta d$ → 2 m에서 시차 1 px 오차가 약 0.2 m. 기준선 5 cm라 먼 거리 깊이는 거칠다는 뜻

## 4. nvblox: 깊이 영상에서 거리 지도까지
| 표현 | 의미 | 쓰임 |
|---|---|---|
| TSDF | 표면 주변의 부호 있는 거리 (truncated signed distance) | 영상마다 측정을 **가중 누적** |
| Mesh | TSDF에서 복원한 표면 | 시각화 |
| ESDF | 가장 가까운 장애물까지의 거리 (Euclidean signed distance) | 2D slice → Nav2 비용 |

- 입력: 깊이 영상 + 포즈 필수, RGB 색은 선택
- 보충: TSDF 가중 누적은 복셀마다 $D \leftarrow \dfrac{W D + w\,d}{W + w}$, $W \leftarrow \min(W + w,\ W_{max})$ ($d$ 이번 측정 거리, $w$ 측정 가중치) → 한 장의 잡음이 평균으로 줄어듦
- 입력 연결 (NVIDIA RealSense 예시 구조도)
  - 스테레오 영상 → VSLAM → Pose
  - 깊이 영상 + Pose → nvblox → RViz
  - 즉 **영상과 깊이는 다른 경로**. 현재 저장소는 RGB 렌더뿐이라 깊이 생성과 ROS 발행을 추가해야 함

### 동적 장애물과 사람
- 지도를 둘로 나눔
  - 정적 공간: 누적한 표면 지도 (TSDF)
  - 동적 물체: 현재 점유 영역 (occupancy)
- 확인할 것: **사람이 지나간 자리가 벽처럼 남지 않는지**
- 사람 분리: 인식 결과(mask)로 깊이 영상에서 사람 영역을 떼고 → 정적 지도 + 사람 점유 지도를 따로 만든 뒤 합침
  - 사람을 정적 지도에서 지우는 것 ≠ 충돌을 무시하는 것 (사람은 점유 지도로 계속 회피 대상)
- Dynablox (ASL 연구): 움직이는 물체 검출 연구 예시. 물체가 떠난 뒤 남는 영역을 비교해 봄. 이 구성 전체가 추가 확장 대상

### 팔 깊이 카메라 입력 규약 (확장 설계)
- 새 토픽 예시: `/arm_stereo/left/depth`, `/arm_stereo/left/camera_info`, 프레임 `arm_left_optical`(신규)
- 깊이가 `16UC1`이면 mm 단위 → m로 변환 (`32FC1`은 보통 m)
- 영상과 CameraInfo의 시각 일치, `use_tf_transforms`로 TF에서 카메라 포즈를 받는 설계
- **해당 시각 TF가 없으면 적분 보류** (틀린 포즈로 쌓으면 지도가 휘어짐)

### 좌표 연결식
$$
T_{VB}(t) = T_{VC}(t)\, T_{BC}(q(t))^{-1}, \qquad
T_{OB}(t) = T_{VB}(t_0)^{-1}\, T_{VB}(t), \qquad
T_{MB}(t) = T^{AMCL}_{MO}(t)\, T^{EKF}_{OB}(t)
$$
- $V$: VO 원점, $O$: 초기 base(odom), $M$: CAD 지도, $B$: base, $C$: 카메라. $T_{XY}$는 $X$ 기준의 $Y$ 포즈
- ① VO가 준 카메라 포즈에서 팔 FK로 구한 장착 변환을 역으로 빼서 → 차체 포즈
- ② 시작 시점 차체를 원점으로 다시 잡아 → odom 기준 차체 포즈
- ③ EKF가 odom 안의 연속 포즈, AMCL이 map↔odom 보정 → 지도 기준 차체 포즈 (map→odom→base 구조, [261015](../261015/ROS2.md) AMCL과 같음)
- EKF 측정: $\mathbf{z}_{wheel} = [v_x, v_y]$, $\mathbf{z}_{IMU} = [\omega_z]$, $\mathbf{z}_{VO} = [\Delta x, \Delta y]/\Delta t$
  - 보충: 내 Waffle 4WD는 스키드 스티어라 $v_y \approx 0$ 제약이 있고 회전 중 바퀴 미끄럼이 커서 바퀴 $\omega_z$는 IMU보다 믿기 어려움
- 확장 설계식임. 현재 카메라는 `base_link` 고정이고 EKF·AMCL 설정도 별도 구현

### 해상도·주기·범위 (교안 제안 시작값, `config/nvblox_arm.yaml`은 추가 작성 대상)
| 항목 | 시작값 | 조정 방향 | 확인 기준 |
|---|---|---|---|
| voxel_size | 0.025 m | 작게 → 세밀, 메모리 증가 | 얇은 벽, GPU 메모리 |
| 깊이 적분 | 15 Hz | 센서 속도 이하 | 누락, 입력 지연 |
| ESDF 갱신 | 10 Hz | 느리면 반응 지연 | 지도 나이, 정지거리 |
| mesh 갱신 | 2 Hz | 시각화 필요량만 | 렌더링과 GPU 경합 |
| slice 높이 범위 | 0.05–0.65 m | 차체·팔 충돌 높이 | 너무 낮으면 바닥이 장애물로 누적 |
| 표시 높이 | 0.15 m | RViz 표시 위치일 뿐 | 충돌 범위와 혼동 금지 |
| 적분 최대 거리 | 5.0 m | 센서 유효 거리 | 먼 거리 노이즈 누적 |
| 지도 유지 반경 | 6.0 m | 미로 크기·메모리 | 먼 장애물 기록 삭제 |

- 보충: voxel을 0.05 → 0.025 m로 반으로 줄이면 같은 부피의 복셀 수는 $2^3 = 8$배 (2D costmap 해상도 절반이면 4배였던 것의 3D판)
- 높이·거리는 팀별 차체·팔·센서 실측값으로 다시 설정

## 5. Nav2 비용지도와 경로
- 계층 구성
  - StaticLayer: CAD 점유 지도
  - NvbloxCostmapLayer: nvblox ESDF slice에서 온 실측 장애물
  - InflationLayer: 로봇 여유 거리
- 계획: NavFn A*, `allow_unknown: false`, 경로 요청 주기 1 s
- 좌표: nvblox 적분은 `odom`, Nav2 비용지도는 `map` → 플러그인이 두 좌표 사이 TF를 씀
- **CAD 지도의 빈 공간은 관측 증거가 아님**
  - 실제 전진에는 신선한 깊이 관측이 필요
  - 미관측 방향은 감속하고 관측한 뒤 진행

| 항목 | 시작값 | 조정 방향 | 평가 기준 |
|---|---|---|---|
| robot_radius | 0.245 m | 실제 외곽 반영 | 코너 접촉, 통로 폭 |
| inflation_radius | 0.32 m | 통로 여유와 절충 | 경로 생성, 벽 여유 |
| cost_scaling_factor | 8.0 | 거리별 비용 변화 | 중앙 선호, 우회 |
| 계획 / 지도 갱신 | 1 Hz / 5 Hz | CPU·반응 시간 비교 | 경로 지연, 실시간 배율 |

- 제공된 Nav2 설정 파일은 없음. footprint와 팔 돌출은 따로 확인 (원형 반경으로 팔이 뻗은 상태를 못 덮을 수 있음)
- 보충: Nav2 inflation 비용 $c(d) = 252 \cdot e^{-k(d - r_{ins})}$ ($r_{ins}$ 내접 반경 이후, $k$ = cost_scaling_factor)
  - 위 값이면 inflation 끝(0.32 m)에서 $252 \cdot e^{-8 \times 0.075} \approx 138$ → 반경 끝에서도 비용이 높게 남아 통로 중앙을 강하게 선호
- 시각화 읽기: 회색 입체 = 복원된 장애물 표면(mesh), 색상 지도 = 거리·비용. 장애물 아래쪽과 로봇이 통과할 높이를 비교 (색의 의미는 표시 설정에 따라 다름)

## 6. 예측 카메라 정책: Nav2 경로 → PPO 관측
### 경로 입력 규칙
- `ComputePathToPose` action으로 경로 요청, 결과는 `/policy/planned_path`에 표시
- 검사: map 좌표인지, 유한수인지, 끝점이 목표와 일치하는지
- 중복점 제거 → **0.05 m 간격 재표본화** (점 간격이 플래너마다 달라도 관측 의미가 같게)
- 새 경로가 오면 가까운 진행점을 다시 고름
- 경로 preview 방향으로 **팔 카메라를 먼저 회전**
  - 내 이해: 미관측 방향은 감속해야 하니(5장), 갈 쪽을 미리 관측해 두면 신선한 깊이가 확보되어 감속이 줄어듦 → 이게 "예측" 카메라

### 정책 계약 (연결 전에 확인)
- PPO task와 체크포인트는 저장소에 없음. 24차원 관측은 기존 설계 예시일 뿐
- **학습 때의 관측 순서·단위가 기준**: 같은 24개라도 순서가 바뀌면 다른 입력
- action 차원·스케일·주기 일치, 정규화 통계도 체크포인트와 함께 유지
- 경로 분포(길이·굽음)가 학습 때와 달라지면 재학습 검토 → [261021 도메인 랜덤화](../261021/ROS2.md#도메인-랜덤화)의 OOD 문제와 같음

### 확장 함수 설계 (교안 설계 예시)
| 함수 | 역할 |
|---|---|
| `validate_depth(image, info)` | 단위·크기·K·frame·시각 검사, 0·NaN·범위 밖 깊이 제외 |
| `lookup_pose(stamp, frame)` | 촬영 시각의 TF만 반환, 없으면 invalid + 사유 |
| `request_path(start, goal)` | 비동기 action의 완료·실패·거절 처리 |
| `prepare_path(path, pose)` | frame·유한수·목표 확인 → 중복 제거 → 재표본화, 반환 `points, stamp, valid, reason` |
| `build_observation(state, path)` | 학습 때 순서·단위·차원으로 관측 구성, 정규화 통계·범위 확인 |
| `apply_action(action, dt)` | 스케일 변환 → 제한 → 구동 명령 |
| `safe_command(valid, age, action)` | 무효·오래된 입력이면 정지, 아니면 제한된 행동 |

```python
def safe_command(valid, age, action):
    if not valid:
        return stop_command
    if age > limit:
        return stop_command
    return bounded(action)
```
- 오류는 명시적으로 처리. 복구는 새 입력·새 경로를 확인한 뒤 재개
- 임계값(`limit`)은 지연과 정지거리로 결정
- **최종 속도는 단일 노드만 발행** (Nav2 컨트롤러와 정책이 동시에 `cmd_vel`을 내면 안 됨)

### 지연·실패 처리
| 상황 | 판정 | 처리 | 검증 기준 |
|---|---|---|---|
| 경로 지연 | 2.5 s 초과 | 주행 차단 | 오래된 경로 추종 없음 |
| nvblox 지도 지연 | 1.0 s 초과 | 주행 차단 | 입력 중단 후 정지 |
| 계획 실패 | action 실패·거절 | 유효 경로 해제 | 막힌 통로 진입 없음 |
| 영상·IMU 오류 | 기존 freshness 검사 | 기존 감속·정지 유지 | 복구 후 재계획 |

- 시각은 모두 `/clock` 기준 (시뮬레이션 시간과 벽시계 시간을 섞으면 age 계산이 틀림)

## 7. 실행 순서와 검증 상태
1. 모델 정적 검사 → `checks/model_validation.json`
2. Sim 6.1 스테레오 렌더 → `sim61_left/right.png`, `sim61.json`
3. ROS 영상·clock·TF 연결
4. cuVSLAM launch
5. nvblox → Nav2 → 정책 확장 (경로 이벤트·거리 지도·비용지도, 완주·접촉·오차·중단 사유 기록)

- `run_predictive_async.sh`는 저장소에 없음
- 교안의 검증 상태표 (2026-10-28 저장소 main `48a1de3` 기준)

| 항목 | 상태 |
|---|---|
| 모델 정적 검사 | PASS_STATIC_ONLY (트리·메시·카메라) |
| 스테레오 렌더 | 결과 미포함 |
| ROS·cuVSLAM | 실행 미검증 |
| nvblox·Nav2·PPO | 구현 미포함 |

- 제출 묶음: 코드 commit·`versions.json`, 팀별 모델·설정 diff·실행 명령, 원본 영상·ROS bag·이벤트 로그, 성공 수/전체 시도 수, 경로 오차·지연·최소 거리
  - 미수행·실패·통과를 구분하고, **과거 결과를 새 통합 성적으로 쓰지 않음**
  - ATE: 전체 궤적 오차, RPE: 구간 이동 오차 (보충: ATE는 정렬 후 전체 위치 차이라 누적 드리프트를, RPE는 일정 구간 상대 이동 차이라 국소 정확도를 봄)

## 8. 팀별 로봇으로 바꿀 항목 (내 로봇: Waffle 4WD)
| 모델·센서 | 주행·정책 |
|---|---|
| URDF와 USD를 같은 로봇으로 지정 | 실제 차체·팔 외곽으로 footprint |
| 메시 상대경로, m 단위, Z-up | 통로 폭·여유·제동거리로 속도 설정 |
| 관절 이름·순서·제한을 실물과 대조 | 경로 frame·관측 차원·action 재정의 |
| 카메라 parent·광학축·K·기준선 | M38의 24차원·속도를 그대로 복사 금지 |
| 휠 반경·조향 부호·팔 도달범위 | 1환경·저속·짧은 경로부터 |
| 질량·관성·충돌 형상 | 수정 전후 설정과 결과를 함께 저장 |

- Waffle 4WD에 대입 ([261021](../261021/ROS2.md) 기준)
  - 바퀴 반지름 33 mm, 스키드 스티어, root `base_footprint` → M38 값 대신 이것으로
  - 카메라: 상단 RealSense 2개(깊이 가능) + 팔 끝 Arducam 1개 → 팔 깊이 확장은 Arducam만으로는 깊이가 없어 입력 구성부터 다시 정해야 함
  - RealSense 광축 35.3° vs 설계 기억값 약 42° 차이는 slice 높이·TF에 바로 영향 → 실물 보정 후 확정
  - 팔 관절 범위가 임시값이라 preview 회전 범위도 임시

## 9. 비교 실험 과제
| 튜닝 실험 | 확장 실험 |
|---|---|
| voxel 0.025 / 0.05 m | 새 장애물로 경로 재계획 |
| ESDF 갱신 5 / 10 Hz | 깊이 입력 중단 후 정지·복구 |
| 팔 preview 거리·속도 | TF 시각 지연에 따른 지도 왜곡 |

- 같은 시작·목표·seed로 반복, 완주 시간·최소 거리·접촉, 프레임 지연·GPU 메모리 기록
- 움직이는 사람은 별도 동적 설정 필요 (`static_tsdf` 확장안과 구분), 실물 센서 노이즈·지연으로 재검증
