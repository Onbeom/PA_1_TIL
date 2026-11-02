# 팀별 로봇 미로 주행 — 보상 설계 · cuVSLAM · Nav2

> 학습일 2026-10-27 (자료를 받은 날 기준), 정리일 2026-11-02
> 자료: 팀별 로봇 미로 주행 — 보상 설계·cuVSLAM·Nav2 실습 (KANT, Lv.2 프로젝트, 54쪽, 로컬 `ref/ROS2/`에만 보관)
> 시연 로봇은 M38(스워브 구동 + 팔 카메라). 아래 수치는 모두 **교안 예시·교안 시연 값**이고 내 실행 결과가 아님
> 실습은 교안 순서대로 진행 (실행 결과는 이 TIL에 기록하지 않음)
> 기초 개념: [261013 SLAM](../261013/ROS2.md), [261015 Nav2·AMCL](../261015/ROS2.md), [261019 강화학습·VSLAM](../261019/ROS2.md#강화학습), [261020 보상 계산·Cartpole PPO](../261020/ROS2.md#5-실습-3--보상-계산), [261021 태스크 구성·도메인 랜덤화](../261021/ROS2.md#isaac-sim--isaac-lab-태스크-구성)
> 내 로봇: [261021](../261021/ROS2.md)·[261022](../261022/ROS2.md) Waffle 4WD

## 1. 실습 목표와 완료 기준
- 각 팀이 **자기 URDF·USD**로 미로 주행 정책을 만드는 실습. M38은 시연 예시일 뿐
  - 관절명·축·영점·물성·센서 TF를 자기 로봇에 맞게 바꿈
  - 검증 순서: 기구학 → 센서 → 정책 → 폐루프
- 완료 증거 (교안 기준): 목표 오차 < 0.10 m, 차체 최고 속도 ≤ 0.951 m/s, 바퀴 아닌 부분 접촉 ≤ 0.5 N, 센서 누락 시 정지·복구, 로그·GUI 녹화·설정 파일 제출, 실물 미측정 가정은 따로 적기

## 2. 환경과 프로젝트 구성
- Sim·Lab·ROS를 **각자 다른 환경**에 두고 Python 환경을 섞지 않음

| 역할 | 버전·위치 |
|---|---|
| OS / ROS | Ubuntu 24.04 / ROS 2 Lyrical (`/opt/ros/lyrical`) |
| Isaac Sim | 6.1.0.0, `~/isaacsim6_venv` |
| Isaac Lab | 소스 커밋 78b12ae, `~/IsaacLab/.venv` (`uv sync --frozen`) |

```shell
# Isaac Sim (한 줄 명령). 시작 전 nvidia-smi / df -h 로 자원 확인
python3 -m venv ~/isaacsim6_venv
~/isaacsim6_venv/bin/python -m pip install --no-cache-dir "isaacsim[all,extscache]==6.1.0.0" --extra-index-url https://pypi.nvidia.com

# ROS 쪽 팀 패키지
source /opt/ros/lyrical/setup.bash
colcon build --packages-select <팀_패키지>
```

- 프로젝트 폴더: `assets/`(로봇·미로·경로), `rl/`(환경·정책·학습·평가), `config/`(센서·EKF·AMCL), `scripts/`(실행·촬영·분석), `evidence/`(결과·로그·영상)
- `uv sync --frozen`: lock 파일 버전 그대로 설치 → 팀원끼리 같은 의존성

## 3. 시연 미로와 전체 연결
- 시연 미로: 바닥 4.464 × 6.364 m, 닫힌 미로 구역 2개, 구역마다 지정 경로 약 8.16 m
- 전제: **CAD 지도와 알려진 시작점** 사용 → 모르는 미로 탐험 문제는 아님. 바닥 무늬는 합성이라 실물 무늬·조명에서 재검증 필요

```text
OpenCR IMU ×2 ─┐
엔코더 13축 ────┴→ 평균 IMU + wheel odometry ─┐
팔 RGBD·stereo → cuVSLAM → body 속도 ─────────┼→ robot_localization(EKF) → 연속 odom·속도
                   └→ 팔 깊이 → Nav2 AMCL(CAD 지도) ─┘                 ↓
                                     경로 preview + PPO(가감속·팔 yaw) → 조향·제동 제약 → 관절 명령
```

- 실제 pose(시뮬레이션 정답)는 **평가 전용**, 제어에는 측정·추정값만 ([261021 관측/진단 분리](../261021/ROS2.md#정책-관측과-진단-정보를-분리))
- 정상 주행에서는 팔과 차체를 **동시에** 제어 (팔이 다음 진행 방향을 미리 봄)

## 4. 팀별로 바꿔야 할 값
| 구분 | M38 시연 예시 | 팀별로 바꿀 것 | 검증 |
|---|---|---|---|
| 기구학 | 바퀴 반경 0.030687 m, 기어 4 | URDF 축·반경·모듈 위치 | 직진·횡이동·회전 |
| 동역학 | 질량·토크·관성에 가정 포함 | 실측 질량·COM·모터 한계 | 전류·정지거리·슬립 |
| 카메라·IMU | 가상 stereo, CAD 장착값 | intrinsic·TF·시각·잡음 | 정지·회전·가속 기록 |
| 정책 배포 | 관측 24 / 행동 2 | 정규화·단위·제약 | 실제 영상 폐루프 평가 |

### 내 로봇(Waffle 4WD)과 다른 점 (내 정리, 교안 밖)
| 항목 | M38 | Waffle 4WD | 영향 |
|---|---|---|---|
| 구동 | 스워브 (조향 4 + 바퀴 4) | 4WD 스키드 스티어 | $v_y$ 없음 → 15장 스워브 역기구학·Omni 모델 그대로 못 씀 |
| 바퀴 반경 | 0.030687 m | 33 mm | 속도 환산·제한기 수치 재계산 |
| VO 카메라 | 팔 끝 stereo (움직임) | 상단 RealSense 2개 (고정) + 팔 끝 Arducam | 고정 카메라는 extrinsic 일정 → 영상 시각 FK 불필요 |
| scan | 팔 깊이로 만든 가상 scan | 라이다 2개 | AMCL 입력으로 라이다 사용 가능 |

- 보충: Nav2에서 스키드 스티어는 보통 차동 모델로 다룸 (AMCL `DifferentialMotionModel`, MPPI `motion_model: DiffDrive`). 회전 때 바퀴가 옆으로 미끄러져 odom 오차가 크므로 IMU yaw rate 융합이 더 중요

## 5. 학습 코드: 관측 · 행동 · 리셋
- 관측 24개: 경로 preview, 속도, 팔 yaw 오차, IMU 기울기·각속도, 시야 상태
  - 항상 같은 순서·단위. 정규화나 checkpoint 구조가 다르면 오류를 내고 멈춤 (`assert obs.shape[-1] == 24`)
- 행동 2개 ($[-1, 1]$ → 물리 단위): $a$ 차체 가감속 ±0.6 m/s², $b$ 팔 기저 yaw 각속도 ±0.5 rad/s. 나머지 팔 4축은 0 고정
- step: 관측 → 정책 → 관절 명령 → 물리 진행 → 보상·종료 판정
- reset: 이전 행동·속도·시야 상태도 **같이** 초기화 (안 하면 리셋 직후 보상이 튐)
- 시간: 물리 200 Hz, decimation 13 → 정책 약 15.38 Hz. 보상식은 $\Delta t = 1/15$ s 기준
  - 주기 계산 방식은 [261021 병렬 환경과 주기](../261021/ROS2.md#병렬-환경과-주기)
- 속도: 기어 48T → 12T(속도 4배) 적용 후 차체 0.95 m/s, 바퀴 상한 30.96 rad/s

## 6. 보상 설계
### 6.1 v5 구현식 (가감속과 팔 yaw를 함께 학습)
$$
v_t^* = \text{clip}(v_{t-1}^* + 0.6\,a_t\Delta t,\ 0,\ 0.95), \qquad q_t^* = \text{clip}(q_t + 0.5\,b_t\Delta t,\ -\pi,\ \pi)
$$

$$
\begin{aligned}
r_t =\ & 8\Delta s + 0.25(|e_{t-1}| - |e_t|) - 0.08\Delta t - 0.005(a_t^2 + b_t^2)\Delta t - 0.01(a_t - a_{t-1})^2 \\
& + 5 I_\text{success} - 5 I_\text{failure} - 2\max\!\left(\tfrac{v_t^2}{1.2} + 0.18 - d_\text{seen},\ 0\right)\Delta t \\
& - 2\,\tfrac{q_x^2 + q_y^2}{0.09}\Delta t - 0.3|e_t|\Delta t - 0.15\,d_\text{cross}\Delta t
\end{aligned}
$$

| 항 | 뜻 |
|---|---|
| $8\Delta s$ | 경로를 따라 진행한 거리 (직선 거리 아님 → 벽 뒤 목표로 가는 지름길 방지) |
| $0.25(\lvert e_{t-1}\rvert - \lvert e_t\rvert)$ | 팔 yaw 오차 $e = q_\text{preview} - q$ 가 줄어든 만큼 |
| $-0.08\Delta t$ | 시간 비용 |
| $-0.005(a^2+b^2)\Delta t$, $-0.01(a_t-a_{t-1})^2$ | 큰 행동, 급변하는 가감속 억제 |
| $\pm 5 I$ | 성공·실패 이벤트 (한 번만) |
| $\max(v^2/1.2 + 0.18 - d_\text{seen}, 0)$ | 정지거리 $v^2/(2 \cdot 0.6)$ + 여유 0.18 m 가 **본 거리**보다 길면 벌점 |
| $(q_x^2+q_y^2)/0.09$ | 차체 quaternion의 x·y 성분 = 기울기 (전복 방지) |
| $0.3\lvert e_t\rvert$, $0.15 d_\text{cross}$ | 팔이 진행 방향을 못 보는 상태, 경로에서 옆으로 벗어난 거리 |

- 같은 정지거리로 안전 속도도 계산: $v_\text{safe} = \sqrt{2(0.6)\max(d_\text{seen} - 0.18, 0)}$, $v_\text{cmd} = \min(v_t^*, v_\text{safe})$
  - "보이는 거리 안에서 0.6 m/s²로 멈출 수 있는 속도"까지만 허용
- [261020](../261020/ROS2.md#5-실습-3--보상-계산)의 보상(거리 차이 + 시간 + 도착/충돌)에 **시야·기울기·경로 이탈** 항이 더해진 형태

### 6.2 항의 크기 검산 (교안 기초 예제, $\Delta t = 1/15$ s)
| 상황 | 해당 항 | 값 |
|---|---|---|
| 1 cm 전진 / 후퇴 | 진행 (계수 4) | +0.60 / −0.60 |
| 행동 두 축 최대 ($\lvert a\rvert = 1$) | 행동 비용 (0.01) | −0.02 |
| 8초 정지 (120 step) | 시간 비용 (0.02/step) | −2.4 |

- 내 검산: $4 \times 0.01 / (1/15) = 0.6$ → 기초 예제의 진행 항은 거리 감소를 $\Delta t$로 나눈 **속도**에 계수를 곱한 꼴. $0.02 \times 120 = 2.4$
- 확인할 점
  - 오래 버티는 시간 비용이 실패 비용보다 크면 → 일부러 넘어져 일찍 끝내는 게 유리 ("자살 종료 유인")
  - 행동 비용이 진행 항보다 크면 → 안 움직이는 게 이득
  - 후진을 항상 벌하면 막다른 길에서 못 빠져나옴 → 후진도 목표 진행으로 평가

### 6.3 증상별 수정 사례 (교안 표 요약)
| 증상 | 원인 | 수정 방향 |
|---|---|---|
| 목표를 지나쳐도 성공 | 거리만으로 판정 | 속도 조건 추가 (정지 후 도착) |
| 목표 보너스 반복 수령 | 매 step +2 | 최초 도달 시 지급 후 종료 |
| 넘어져 빨리 끝냄 | 실패 비용 없음 | 실패 비용 추가, 모델 점검 |
| 벽에 계속 밀기 | 접촉 벌점만, 벽 관측 없음 | 거리·접촉 관측 추가 |
| 우회 중 감점 | 직선 거리 사용 | 경로 잔여 길이 사용 |
| 코너에서 정체 | lookahead가 너무 멂 | 6점 → 3점 비교 |
| 좌우 명령 진동 | 행동 변화 비용 없음 | $\lVert a - a_\text{prev}\rVert^2$ 추가 |
| 보상만 급상승 | reset 때 이전 거리 미초기화 | reset 상태 함께 초기화 |
| Sim에서만 잘 움직임 | 정답 pose로 학습 | 잡음·지연을 단계적으로, 추정 pose로 평가 |

- 빠르면서 안정적인 주행: 기울기 비용 2→4, 팔 yaw 감소 0.25→0.5, Δ가속 비용 0.01→0.03, 실패 −5→−10을 **각각 따로** 비교. 충돌률을 먼저 잡고 그다음 속도
- 팔 카메라 보상 원칙
  - 진행 보상은 볼 수 있는 상태에서 움직일 때만 (멈춰서 점수 얻기 방지)
  - 시야 확인(ready) 보상을 계속 주면 회전만 반복 → 지속 지급 금지
  - 시야 없이 이동하면 (속도 × 미관측)으로 강하게 감점

## 7. 정책과 제한기: 역할 나누기
- PPO가 내는 것은 가감속 $a$와 팔 yaw $b$뿐. 조향·제동 한계는 **배포용 제한기**가 따로 걸어 줌

$$
\begin{aligned}
v_i^\text{curve} &= \min\!\big(0.92,\ 0.6/\max(|\kappa_i|, 10^{-6})\big) \\
v_i^\text{path} &= \min\!\Big(v_i^\text{curve},\ \sqrt{(v_{i+1}^\text{path})^2 + 2(0.4)\Delta s_i}\Big) \\
v_t^\text{cmd} &= \min\!\Big(v_t^*,\ v^\text{path},\ \sqrt{1.2\max(d_\text{seen} - 0.32, 0)}\Big), \qquad |\Delta\omega_\text{wheel}| \le (0.6/R)\Delta t
\end{aligned}
$$

- 해석 (내 정리)
  - 곡률: $v\kappa$ = yaw rate → $v \le 0.6/\kappa$ 는 회전 속도 0.6 rad/s 제한
  - 경로 속도: 경로 끝에서 거꾸로 계산 → 코너 앞에서 0.4 m/s²로 미리 감속 가능한 속도
  - 시야: 본 거리에서 0.32 m 여유를 두고 0.6 m/s²로 멈출 수 있는 속도
  - 바퀴 slew: 바퀴 각가속도를 차체 0.6 m/s² 상당으로 제한 ($R = 0.0306872$ m), 급제동 기울어짐 방지
- 정책에 안전을 전부 맡기지 않는 구조. 평가도 "정책 + 제한기" 조합으로 해야 함

## 8. PPO: 손실 · GAE · 튜닝
- 클립 목적함수는 [261019 PPO](../261019/ROS2.md#ppo). 이번에 추가로 본 것은 **전체 손실과 GAE**

$$
\mathcal{L} = -L^{CLIP} + c_v\,\mathbb{E}_t\big[(V_\theta - \hat R_t)^2\big] - c_e\,\mathbb{E}_t\big[\mathcal{H}(\pi_\theta)\big]
$$

- 가치 오차는 줄이고 엔트로피(탐색)는 키우는 방향. 시작 예시 $\epsilon = 0.2$, $c_v = 0.5$, $c_e = 0.005$

$$
\delta_t = r_t + \gamma(1-d_t)V(s_{t+1}) - V(s_t), \quad \hat A_t = \delta_t + \gamma\lambda(1-d_t)\hat A_{t+1}, \quad \hat R_t = \hat A_t + V(s_t)
$$

- $\gamma = 0.99$: 먼 미래 보상 반영 / $\lambda = 0.95$: 편향과 분산 절충
- $d_t$는 종료 여부. **실패 종료와 시간 초과를 구분**
  - 시간 초과(truncated)는 상태가 나빠서 끝난 게 아님 → 마지막 $V(s_{t+1})$를 이어 붙이는(bootstrap) 처리 검토
  - 교안 기준 현재 구현은 timeout도 terminal로 처리 → value 편향 가능

| 항목 | 기준 | 조정 방향 | 볼 지표 |
|---|---|---|---|
| 학습률 | 3e−4 | 불안정하면 1e−4 | KL, 성능 급락 |
| clip ε | 0.2 | 갱신이 크면 0.1 | clip fraction |
| update epoch | 4 | 과적합이면 2 | KL, 새 평가 성능 |
| entropy 계수 | 0.005 | 탐색 부족 시 0.01 | 행동 std, 충돌 |
| gamma / lambda | 0.99 / 0.95 | 0.995 / 0.9 비교 | advantage 분산 |
| rollout | 64 step | 긴 의존성이면 128 | 메모리·표본 수 |

- 팔 카메라 버전 예: rollout 128 × 환경 16 = 2,048 표본, minibatch 256 → 8묶음 × epoch 4 = 업데이트당 32회, 신경망 64-64 Tanh
- 이어 학습: optimizer 상태까지 복원되므로 바꾼 lr이 실제로 반영됐는지 출력해서 확인
- 좋은 정책 ≠ 마지막 파일 → 고정 평가(완주·충돌·시간)로 고름

## 9. 학습 실행과 실험 순서
```shell
PY=~/IsaacLab/.venv/bin/python
export OMNI_KIT_ACCEPT_EULA=YES
$PY scripts/lab_python.py rl/train_ppo.py --iterations 100 --num-envs 8 --seed 7 --output runs/maze_ppo
# 이어 학습: --resume <policy.pt> (환경·관측 버전이 같은지 먼저 확인)

# 최종 통합 평가 (기본 checkpoint v5-final.pt), GUI=1이면 실제 GUI 표시
scripts/run_predictive_async.sh evidence/repeat-first
# 두 번째 미로는 경로 파일을 앞에 지정
ROUTE_FILE=assets/maze/route_clearance_second.json scripts/run_predictive_async.sh evidence/repeat-first
```

- 순서: 동작 부호·관절 제한 → 센서·TF → 보상 각 항의 **평균 크기** → PPO
- 가중치는 한 번에 한 항씩, 같은 seed·경로·초기 조건으로 비교 (기준 A → 진행만 / 시간만 바꾼 B·C → 새 시작점·seed로 최종 D)
- OOM이면 `num_envs`·영상 해상도부터 줄임. 센서·제어 주기를 바꾸면 시간 보상과 정지거리도 다시 확인 ($\Delta t$에 비례하는 항이 많음)

## 10. 경로 예측과 팔 카메라
- 팔이 회전하는 시간만큼 **앞을 미리 봐야** 코너 진입 전에 관측 가능
  - 예: 90° 회전 → $(\pi/2)/0.5 \approx 3.14$ s. 필요한 회전각이 FOV 안(예: 35° 이내)이면 이미 전방 관측 중
- S자 코너 연속: 다음 한 점만 보지 말고 경로 방향열·곡률까지 봄 (안 그러면 팔이 왕복하며 추적이 끊김)
- 팔 회전 범위: 기존 ±0.35 rad(약 ±20°)는 CAD 검증용 임시값 → 기계 한계로 해석 금지. 공식 OMX 기저 yaw ±180°와 배선 한계는 별개

## 11. cuVSLAM
- 기본 개념은 [261019 VSLAM](../261019/ROS2.md#vslam). 입력: 영상 + 보정값 (선택: 깊이·IMU) / 출력: 6자유도 pose와 궤적
- VO: 연속 프레임 사이 이동량만 (누적 오차) / SLAM: 지도와 위치를 함께 추정, 재방문 인식으로 보정
- 구조: 프런트엔드(2D 특징 추적 → 3D pose → 로컬 BA) → 백엔드(재방문 인식 → pose graph 최적화)
  - 이번 실습은 **VO만** 사용, 전역 보정은 EKF + AMCL이 맡음
- 역할 구분: cuVSLAM = 위치 추정 / Nav2 = 경로·주행 제어 / PPO = 행동 학습
- GPU: 특징·대응점·sparse BA는 CUDA, 시간 정렬·TF·FK는 CPU. 같은 GPU를 Sim 렌더·Lab 학습도 씀 → 사용률보다 프레임 지연·누락·추적 실패·완주율로 판단

| 설정 (팔 카메라) | 값 | 의미 |
|---|---|---|
| `tracking_mode` | 2 | RGBD 모드 |
| `rectified_images` | true | 보정된 영상 입력 |
| `depth_scale_factor` | 1000 | 깊이 16UC1, mm 단위 |
| `depth_enable_stereo_tracking` | true | 좌우 영상도 추적에 사용 |
| `enable_imu_fusion` | false | 팔 카메라가 움직이므로 body IMU를 고정 extrinsic으로 묶지 않음 |

- 점검: 좌우 동기·intrinsic·baseline, `ros2 node info /visual_slam`, TF·clock 발행자 중복 제거
- 증상별: 영상 뒤틀림 → K·D·R·P / 추적 끊김 → 노출·무늬·동기 등 입력 품질부터 / 위치 축 틀림 → optical TF

## 12. 센서 통합: 좌표계 · 이중 IMU · 엔코더
### 12.1 카메라 → 차체
$$
T_{VB}(t) = T_{VC}(t)\,T_{BC}(q(t))^{-1}, \quad T_{OB}(t) = T_{VB}(t_0)^{-1}T_{VB}(t), \quad T_{MB}(t) = T^\text{AMCL}_{MO}(t)\,T^\text{EKF}_{OB}(t)
$$

- $V$: VO 원점, $O$: 초기 base, $M$: CAD 지도, $C$: 카메라, $B$: body
- 카메라가 팔 위에 있어 $T_{BC}$가 관절각 $q$에 따라 바뀜 → **영상 촬영 시각의 $q(t)$**로 FK 계산
  - 최신 관절각을 넣으면 팔 회전이 차체 이동으로 보임
- EKF 입력: 바퀴 $[v_x, v_y]$, IMU $[\omega_z]$, VO $[\Delta x, \Delta y]/\Delta t$ (위치 차분을 속도로)

### 12.2 이중 IMU 보정
$$
\boldsymbol\omega_i^B = R_{BS_i}\boldsymbol\omega_i^{S_i}, \quad \mathbf f_{O,i} = \mathbf f_i^B - \boldsymbol\alpha \times \mathbf r_i - \boldsymbol\omega \times (\boldsymbol\omega \times \mathbf r_i)
$$

- body 축으로 회전 → 장착 위치 $\mathbf r_i$ 때문에 생기는 접선·구심 가속도(레버암 항)를 빼서 기준점 $O$ 값으로 맞춤. $\mathbf f$는 중력 포함 specific force
- $\lVert\boldsymbol\omega_1 - \boldsymbol\omega_2\rVert \le 0.35$, $\lVert\mathbf f_{O,1} - \mathbf f_{O,2}\rVert \le 2.0$ 일 때만 평균. 불일치·누락이면 평균 강행 금지
- OpenCR: ±2 g / ±2000°/s, 200 Hz, 보드별 토픽·USB 포트·장치 ID 고정. 펌웨어는 컴파일·ROS 통과까지, 실물 플래시는 미실행 (교안 표기)

### 12.3 엔코더
$$
\Delta\theta_t = \text{atan2}\big(\sin(\theta_t - \theta_{t-1}), \cos(\theta_t - \theta_{t-1})\big), \quad \tilde\theta_t = \tilde\theta_{t-1} + \Delta\theta_t, \quad |\omega_\text{max}|\Delta t < \pi
$$

- 래핑 풀기: $2\pi - 0.05 \to -2\pi + 0.05$ 로 원시값이 튀어도 $\Delta\theta = +0.10$ rad
  - 한 주기에 $\pi$ 이상 돌면 방향을 잘못 읽음 (내 검산: 30.96 rad/s × 0.005 s ≈ 0.15 rad라 여유 큼)
- 카운트 $n_\text{motor} = \text{round}\big(N\tilde\theta / (2\pi g)\big)$, $N = 4096$(CPR, 실측 전 가정), $g = 4$
- 속도는 약 30 ms 차분창 $\hat\omega = \frac{2\pi g}{N}\frac{n_t - n_{t-k}}{t_t - t_{t-k}}$. 5 ms 차분은 양자화 잡음이 큼 → 10/30/50 ms 비교 (잡음 vs 지연)

## 13. 위치추정: EKF + Nav2 AMCL
- 프레임 관계는 [261013 map·odom·base](../261013/ROS2.md#mapodombase-프레임): EKF가 odom→base, AMCL이 map→odom

| 입력 | 쓰는 것 | 빼는 것 | 이유 |
|---|---|---|---|
| wheel odometry | 차체 $v_x, v_y$ | 적분 위치 | 같은 정보 중복 융합 방지 |
| 이중 IMU | 보정 yaw rate | AHRS yaw | 공통 축·시각 |
| VO + 팔 FK | 위치 차분 → 속도 | VO yaw | 팔 회전과 차체 회전 분리 |

- AMCL: `OmniMotionModel`(스워브라 차동 모델 금지), scan은 팔 깊이를 1° bin으로 만든 것(0.23~5 m, 안 보인 방향은 infinity), 입자 500~1500
- TF 발행자는 map→odom→base 각각 하나씩만. AMCL 기본은 [261015 AMCL](../261015/ROS2.md#3-amcl--저장-지도에서-위치-추정)

## 14. Nav2 설정
```shell
sudo apt install ros-lyrical-navigation2 ros-lyrical-nav2-bringup
```

- 이번 실행: AMCL + EKF + 지정 경로, 주행 제어는 PPO + 스워브 제한기 (Nav2 BT·MPPI 전체 통합은 별도 검증)
  - 팀별 확장 시 `Path → preview → PPO → cmd_vel` 연결과 watchdog 검증
  - **MPPI와 PPO가 동시에 명령하지 않게** 한 모드만 활성화, 명령 만료·손실 시 정지
- costmap: `/arm_depth/scan` → obstacle_layer (`marking`·`clearing` true), footprint는 실제 외곽, inflation은 통로 폭과 함께. 미관측 방향은 안전한 빈 공간이 아님
- MPPI ([261015](../261015/ROS2.md#5-지역-계획제어--dwb와-mppi)): `motion_model`은 구동 구조와 일치(스워브 → Omni), vx·vy·wz 제한은 구동기 실측값, `model_dt × time_steps`는 제동·코너 길이 고려
- 목표에서 진동 → goal tolerance를 센서 오차보다 여유 있게. odom은 센서 기반 속도로 (명령 복사 금지)

## 15. 부록: 스워브 역기구학 (M38용)
$$
u_i = v_x - \omega_z y_i, \quad v_i = v_y + \omega_z x_i, \quad \theta_i = \text{atan2}(v_i, u_i) - \beta_i, \quad \dot\phi_i = \sigma_i\frac{\sqrt{u_i^2 + v_i^2}}{r_i}
$$

- 모듈 위치 $(x_i, y_i)$의 속도 = 차체 속도 + 회전에 의한 속도. $\beta_i$: 조향 영점, $\sigma_i$: 바퀴 부호 (±1)
- 검증: 직진 → 옆 이동 → 제자리 회전으로 부호 확인 후 PPO 연결
- 조향 ±90° 제한: 범위 밖이면 $\theta \pm \pi$로 돌리고 바퀴 속도 반전 (경계 채터링은 hold 0.06 rad). 정렬 전에는 바퀴 속도에 $\max(0, \cos(\text{조향 오차}))$를 곱해 감속
- 보충: 내 로봇(스키드 스티어)은 좌우 바퀴 속도 $v_{L,R} = v_x \mp \omega_z W/2$ ($W$: 좌우 바퀴 간격) 형태

## 16. 교안 시연 결과 (M38, 내 결과 아님)
- v5 PPO + 측정 센서 + EKF·AMCL + 배포 제한기, 물리 200 Hz, 실제 영상 폐루프 (교안 표기 2026-10-26)

| 실행 | 시간 | 최고 속도 | 목표 오차 | 접촉 |
|---|---|---|---|---|
| 첫 미로 GUI 1 | 60.45 s | 0.919 m/s | 4.13 cm | 0 N |
| 첫 미로 GUI 2 | 63.18 s | 0.922 m/s | 4.25 cm | 0 N |
| 두 번째 미로 | 57.40 s | 0.824 m/s | 4.43 cm | 0 N |

- 센서 누락 시험(ROS 주입 오류): IMU 2를 2 s, 카메라를 2.5 s 끊으면 0.355 s 안에 정지 후 재개, VO는 reset 후 EKF 증분으로 좌표 연결
- 교안이 밝힌 한계: 같은 설정·두 경로 결과이고 실물·모든 seed를 보장하지 않음, 실물 USB 단선 시험 아님

## 17. 배운 점
- 보상은 항마다 **한 step에 얼마인지** 숫자로 검산해야 편법(정지·자살 종료·반복 수령)이 보임
- 정지거리 $v^2/2a$ 하나로 보상 벌점·안전 속도·배포 제한기를 일관되게 만듦 → 학습과 배포의 안전 기준이 같음
- 정책은 가감속·팔 방향만, 조향·제동 한계는 제한기 → 정책에 모든 걸 맡기지 않음
- 움직이는 카메라로 VO를 쓰면 **시각이 맞는 FK**가 필수. 시간 정렬이 좌표 변환만큼 중요
- 같은 정보를 두 경로로 EKF에 넣지 않음 (적분 위치·AHRS yaw·VO yaw 제외)
- Waffle 4WD에는 스워브·Omni 부분을 그대로 못 쓰고, 라이다와 고정 RealSense를 쓰는 쪽으로 바꿔야 함
