# 팀별 로봇 자율주행 2 — nvblox·Nav2·예측 카메라 정책

> 학습일 2026-10-28 (자료를 받은 날), 정리일 2026-11-02. 자료는 로컬 `ref/ROS2/`에만 보관, 시연 로봇은 M38
> 이전: [261027 팀별 로봇 미로 주행](../261027/ROS2.md) / 기초: Nav2·AMCL [261015](../261015/ROS2.md), PPO·VSLAM [261019](../261019/ROS2.md), Waffle 4WD [261021](../261021/ROS2.md)
> 실습은 교안 순서대로 진행 (실행 결과는 이 TIL에 기록하지 않음)

## 1. 전체 흐름과 이번 범위
- 목표 파이프라인: 깊이 영상 → **nvblox** 거리 지도 → **Nav2** 비용지도 → 경로 재계획 → 경로를 **정책 관측**으로 → 속도 명령
  - 경로 앞쪽을 팔 카메라가 미리 봄 = "예측 카메라"

| 구분 | 내용 |
|---|---|
| 제공 | URDF·USD·메시, 가상 고정 스테레오 카메라, 정적 검사·렌더 스크립트, `launch/cuvslam_sim.launch.py` 초안 |
| 추가 작성 | ROS 센서 그래프, nvblox·Nav2 설정, 정책 task·경로 어댑터 |
| 확장 설계(미포함) | nvblox·Nav2·PPO 통합, 이중 IMU·EKF·AMCL |

- 버전 기준은 `versions.json` (Isaac Sim 6.1.0.0 / Isaac ROS release-5.0 / ROS 2 Lyrical)
  - 스크립트가 6.1.0.0만 허용 → 6.2로 임의 교체 금지 ([261019](../261019/ROS2.md)의 6.2와 혼동 주의)

## 2. 저장소로 시작하는 4단계
```shell
.venv-check/bin/python scripts/validate_model.py   # 01 정적 검사
python scripts/render_stereo.py --headless         # 02 스테레오 렌더
ros2 run tf2_ros tf2_echo base_link sim_left_optical  # 03 TF 확인
ros2 launch ./launch/cuvslam_sim.launch.py         # 04 cuVSLAM
```
- 01: `status = PASS_STATIC_ONLY` → **정적 PASS는 주행 성공이 아님**
- 02: 640×480 좌우 영상. 렌더 성공 ≠ ROS 발행, 현재 **RGB만** 생성 → 깊이 입력은 별도 구현
- 03: 좌·우 Image + CameraInfo, `/clock`·`/joint_states`·TF 발행. 좌우 **같은 스텝 timestamp**, QoS 일치
- 04: launch는 영상을 발행하지 않음 → 영상·CameraInfo·TF가 먼저 있어야 함
  - 추적 시험: 정지 → 직진 → 좌우 → 회전 → 시작점 복귀. 추정값과 ground truth 분리 기록
  - **같은 TF를 두 노드가 발행하지 않기** (예: 둘 다 `odom→base_link`)

## 3. 카메라: 차체 고정 vs 팔 부착
| 항목 | 현재 저장소 (차체 고정) | 팔 부착형으로 바꿀 때 |
|---|---|---|
| TF | `base_link → sim_left/right_optical` (고정) | parent를 팔 링크로, USD 카메라 경로도 변경 |
| 위치 | 기준선 0.05 m | 관절값 $q(t)$ + 장착 변환으로 FK |
| 내부 파라미터 | 640×480, $f_x = f_y = 400$ px (합성값) | 실물 보정값 |
| 처리 | 시각 문제 적음 | **촬영 시각의 TF를 조회한 뒤** 영상 처리 |

- 스테레오 깊이 $Z = \dfrac{f_x B}{d}$ ($B$ 기준선, $d$ 시차 px)

## 4. nvblox: 깊이 영상에서 거리 지도까지
| 표현 | 의미 | 쓰임 |
|---|---|---|
| TSDF | 표면 주변의 부호 있는 거리 (truncated signed distance) | 영상마다 측정을 **가중 누적** |
| Mesh | TSDF에서 복원한 표면 | 시각화 |
| ESDF | 가장 가까운 장애물까지의 거리 (Euclidean signed distance) | 2D slice → Nav2 비용 |

- 입력: 깊이 영상 + 포즈 필수, RGB 색은 선택. 스테레오 → VSLAM → Pose, 깊이 + Pose → nvblox (**영상과 깊이는 다른 경로**)
- 동적 장애물: 정적 공간은 TSDF, 동적 물체는 현재 점유(occupancy)로 분리
  - 확인할 것: **사람이 지나간 자리가 벽처럼 남지 않는지**
  - 사람을 정적 지도에서 지우는 것 ≠ 충돌 무시 (점유 지도로 계속 회피)
- 팔 깊이 카메라 입력 (확장 설계)
  - 깊이가 `16UC1`이면 mm → m 변환 (`32FC1`은 보통 m)
  - **해당 시각 TF가 없으면 적분 보류** (틀린 포즈로 쌓으면 지도가 휘어짐)

### 좌표 연결식 (확장 설계)
$$
T_{VB}(t) = T_{VC}(t)\, T_{BC}(q(t))^{-1}, \qquad
T_{OB}(t) = T_{VB}(t_0)^{-1}\, T_{VB}(t), \qquad
T_{MB}(t) = T^{AMCL}_{MO}(t)\, T^{EKF}_{OB}(t)
$$
- $V$: VO 원점, $O$: odom, $M$: 지도, $B$: base, $C$: 카메라
- VO 카메라 포즈 → 팔 FK 장착 변환 제거 → 차체 포즈 → odom 기준 → EKF + AMCL로 map 기준 ([261015](../261015/ROS2.md) map→odom→base 구조)

## 5. 시작값: nvblox와 Nav2 비용지도
- 계층: StaticLayer (CAD 지도) + NvbloxCostmapLayer (ESDF slice 실측 장애물) + InflationLayer (여유 거리)
- 계획: NavFn A*, `allow_unknown: false`. nvblox 적분은 `odom`, 비용지도는 `map` 좌표
- **CAD 지도의 빈 공간은 관측 증거가 아님** → 미관측 방향은 감속하고 관측한 뒤 진행

| 항목 | 시작값 | 확인 기준 |
|---|---|---|
| voxel_size | 0.025 m | 얇은 벽, GPU 메모리 |
| 깊이 적분 / ESDF / mesh | 15 / 10 / 2 Hz | 입력 지연, 지도 나이, GPU 경합 |
| slice 높이 범위 | 0.05–0.65 m | 너무 낮으면 바닥이 장애물로 누적 |
| 적분 최대 거리 / 유지 반경 | 5.0 / 6.0 m | 먼 거리 노이즈, 메모리 |
| robot_radius / inflation_radius | 0.245 / 0.32 m | 코너 접촉, 통로 폭 |
| cost_scaling_factor | 8.0 | 중앙 선호, 우회 |
| 계획 / 지도 갱신 | 1 Hz / 5 Hz | 경로 지연, 실시간 배율 |

- 교안 제안 시작값이며 높이·거리는 팀별 실측값으로 다시 설정. 팔 돌출은 원형 반경으로 못 덮을 수 있음

## 6. 예측 카메라 정책: Nav2 경로 → PPO 관측
### 경로 입력 규칙
- `ComputePathToPose` action으로 경로 요청
- 검사: map 좌표인지, 유한수인지, 끝점이 목표와 일치하는지
- 중복점 제거 → **0.05 m 간격 재표본화** (플래너마다 점 간격이 달라도 관측 의미가 같게)
- 경로 preview 방향으로 **팔 카메라를 먼저 회전** → 갈 쪽의 신선한 깊이 확보로 감속이 줄어듦

### 정책 계약
- PPO task·체크포인트는 저장소에 없음. 24차원 관측은 기존 설계 예시
- **학습 때의 관측 순서·단위가 기준**, action 차원·스케일·주기, 정규화 통계도 체크포인트와 함께 유지
- 경로 분포가 학습 때와 다르면 재학습 검토 ([261021 도메인 랜덤화](../261021/ROS2.md#도메인-랜덤화)의 OOD 문제)
- 함수 설계 요지
  - 깊이·TF는 단위·frame·촬영 시각을 검사하고, 없으면 invalid + 사유 반환
  - 경로는 검사 → 중복 제거 → 재표본화 후 관측 구성
  - 무효·오래된 입력이면 정지, 아니면 제한된 행동 (`safe_command`)
- **최종 속도는 단일 노드만 발행** (Nav2 컨트롤러와 정책이 동시에 `cmd_vel` 금지)

### 지연·실패 처리
| 상황 | 판정 | 처리 |
|---|---|---|
| 경로 지연 | 2.5 s 초과 | 주행 차단 |
| nvblox 지도 지연 | 1.0 s 초과 | 주행 차단 |
| 계획 실패 | action 실패·거절 | 유효 경로 해제 |
| 영상·IMU 오류 | 기존 freshness 검사 | 기존 감속·정지 유지 |

- 시각은 모두 `/clock` 기준 (시뮬레이션 시간과 벽시계 시간을 섞으면 age 계산이 틀림)
- 복구는 새 입력·새 경로를 확인한 뒤 재개

## 7. 검증 상태와 팀별 적용
- 교안 검증 상태 (2026-10-28 main `48a1de3`): 모델 정적 검사 PASS_STATIC_ONLY, 렌더 결과 미포함, ROS·cuVSLAM 실행 미검증, nvblox·Nav2·PPO 구현 미포함
- 제출: 성공 수/전체 시도 수, 경로 오차·지연·최소 거리. **과거 결과를 새 통합 성적으로 쓰지 않음**
- Waffle 4WD 적용 ([261021](../261021/ROS2.md))
  - 바퀴 반지름 33 mm, 스키드 스티어, root `base_footprint` → M38 값·24차원·속도 그대로 복사 금지
  - 팔 끝 Arducam만으로는 깊이가 없음 → 팔 깊이 확장은 입력 구성부터 다시 정해야 함
- 비교 실험: voxel 0.025/0.05 m, ESDF 5/10 Hz, preview 거리·속도 등을 같은 시작·목표·seed로 반복
