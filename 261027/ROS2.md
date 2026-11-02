# 팀별 로봇 미로 주행 — 보상 설계 · cuVSLAM · Nav2

> 학습일 2026-10-27 (자료를 받은 날 기준), 정리일 2026-11-02
> 자료: 팀별 로봇 미로 주행 — 보상 설계·cuVSLAM·Nav2 실습 (KANT, Lv.2 프로젝트, 54쪽, 로컬 `ref/ROS2/`에만 보관)
> 시연 로봇은 M38(스워브 구동 + 팔 카메라). 아래 수치는 모두 **교안 예시·교안 시연 값**이고 내 실행 결과가 아님
> 기초: [261013 SLAM](../261013/ROS2.md), [261015 Nav2·AMCL](../261015/ROS2.md), [261019 강화학습·VSLAM](../261019/ROS2.md#강화학습), [261020 보상 계산](../261020/ROS2.md#5-실습-3--보상-계산), [261021 태스크 구성](../261021/ROS2.md#isaac-sim--isaac-lab-태스크-구성)

## 1. 목표와 환경
- 각 팀이 **자기 URDF·USD**로 미로 주행 정책을 만드는 실습. 검증 순서: 기구학 → 센서 → 정책 → 폐루프
- 완료 기준: 목표 오차 < 0.10 m, 최고 속도 ≤ 0.951 m/s, 바퀴 아닌 부분 접촉 ≤ 0.5 N, 센서 누락 시 정지·복구
- 환경: Ubuntu 24.04 / ROS 2 Lyrical, Isaac Sim 6.1.0.0(`~/isaacsim6_venv`), Isaac Lab(`~/IsaacLab/.venv`, `uv sync --frozen`). Python 환경을 섞지 않음
- 시연 미로는 CAD 지도와 알려진 시작점 사용 → 모르는 미로 탐험 문제는 아님

## 2. 전체 연결
```text
OpenCR IMU ×2 ─┐
엔코더 13축 ────┴→ 평균 IMU + wheel odometry ─┐
팔 RGBD·stereo → cuVSLAM → body 속도 ─────────┼→ robot_localization(EKF) → 연속 odom·속도
                   └→ 팔 깊이 → Nav2 AMCL(CAD 지도) ─┘                 ↓
                                     경로 preview + PPO(가감속·팔 yaw) → 조향·제동 제약 → 관절 명령
```

- 실제 pose(시뮬레이션 정답)는 **평가 전용**, 제어에는 측정·추정값만 ([261021 관측/진단 분리](../261021/ROS2.md#정책-관측과-진단-정보를-분리))
- 정상 주행에서는 팔과 차체를 **동시에** 제어 (팔이 다음 진행 방향을 미리 봄)

## 3. 팀별로 바꿀 값
| 구분 | M38 시연 예시 | 팀별로 바꿀 것 | 검증 |
|---|---|---|---|
| 기구학 | 바퀴 반경 0.030687 m, 기어 4 | URDF 축·반경·모듈 위치 | 직진·횡이동·회전 |
| 동역학 | 질량·토크·관성에 가정 포함 | 실측 질량·COM·모터 한계 | 전류·정지거리·슬립 |
| 카메라·IMU | 가상 stereo, CAD 장착값 | intrinsic·TF·시각·잡음 | 정지·회전·가속 기록 |
| 정책 배포 | 관측 24 / 행동 2 | 정규화·단위·제약 | 실제 영상 폐루프 평가 |

- 내 로봇([261021](../261021/ROS2.md)·[261022](../261022/ROS2.md) Waffle 4WD)은 스키드 스티어라 $v_y$ 없음 → 스워브 역기구학·Omni 모델 그대로 못 씀. 라이다 2개를 AMCL 입력으로 사용 가능 (내 정리)

## 4. 관측 · 행동 · 리셋
- 관측 24개: 경로 preview, 속도, 팔 yaw 오차, IMU 기울기·각속도, 시야 상태. 순서·단위·정규화가 다르면 오류 내고 멈춤
- 행동 2개 ($[-1, 1]$ → 물리 단위): $a$ 차체 가감속 ±0.6 m/s², $b$ 팔 기저 yaw 각속도 ±0.5 rad/s
- reset: 이전 행동·속도·시야 상태도 **같이** 초기화 (안 하면 리셋 직후 보상이 튐)
- 시간: 물리 200 Hz, decimation 13 → 정책 약 15.38 Hz. 보상식은 $\Delta t = 1/15$ s 기준

## 5. 보상 설계 (v5)
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
| $8\Delta s$ | 경로를 따라 진행한 거리 (직선 거리 아님 → 벽 뒤 지름길 방지) |
| $0.25(\lvert e_{t-1}\rvert - \lvert e_t\rvert)$ | 팔 yaw 오차가 줄어든 만큼 |
| $-0.08\Delta t$, 행동·Δ가속 비용 | 시간 비용, 큰 행동·급변 억제 |
| $\pm 5 I$ | 성공·실패 이벤트 (한 번만) |
| $\max(v^2/1.2 + 0.18 - d_\text{seen}, 0)$ | 정지거리 $v^2/(2 \cdot 0.6)$ + 여유 0.18 m 가 **본 거리**보다 길면 벌점 |
| $(q_x^2+q_y^2)/0.09$ | 차체 기울기 (전복 방지) |
| $0.3\lvert e_t\rvert$, $0.15 d_\text{cross}$ | 진행 방향 미관측, 경로 옆 이탈 |

- 안전 속도: $v_\text{safe} = \sqrt{2(0.6)\max(d_\text{seen} - 0.18, 0)}$, $v_\text{cmd} = \min(v_t^*, v_\text{safe})$
- 확인할 점: 시간 비용 > 실패 비용이면 자살 종료 유인, 행동 비용 > 진행 항이면 정지가 이득, 후진을 항상 벌하면 막다른 길 탈출 불가
- 증상별 수정 예: 보너스 반복 수령 → 최초 도달 시 지급 후 종료 / 우회 중 감점 → 경로 잔여 길이 사용 / 좌우 진동 → $\lVert a - a_\text{prev}\rVert^2$ 추가 / Sim에서만 잘 움직임 → 잡음·지연 추가, 추정 pose로 평가
- 팔 카메라: 진행 보상은 볼 수 있을 때만, 시야 확인 보상을 계속 주면 회전만 반복

## 6. 배포 제한기
- PPO는 가감속 $a$와 팔 yaw $b$만 냄. 조향·제동 한계는 **배포용 제한기**가 따로 걺

$$
\begin{aligned}
v_i^\text{curve} &= \min\!\big(0.92,\ 0.6/\max(|\kappa_i|, 10^{-6})\big) \\
v_i^\text{path} &= \min\!\Big(v_i^\text{curve},\ \sqrt{(v_{i+1}^\text{path})^2 + 2(0.4)\Delta s_i}\Big) \\
v_t^\text{cmd} &= \min\!\Big(v_t^*,\ v^\text{path},\ \sqrt{1.2\max(d_\text{seen} - 0.32, 0)}\Big), \qquad |\Delta\omega_\text{wheel}| \le (0.6/R)\Delta t
\end{aligned}
$$

- 곡률(회전 속도 제한), 경로 끝에서 거꾸로 계산한 감속, 시야 정지거리, 바퀴 slew 제한. 평가도 "정책 + 제한기" 조합으로

## 7. PPO: 손실 · GAE · 튜닝
- 클립 목적함수는 [261019 PPO](../261019/ROS2.md#ppo)

$$
\mathcal{L} = -L^{CLIP} + c_v\,\mathbb{E}_t\big[(V_\theta - \hat R_t)^2\big] - c_e\,\mathbb{E}_t\big[\mathcal{H}(\pi_\theta)\big]
$$

$$
\delta_t = r_t + \gamma(1-d_t)V(s_{t+1}) - V(s_t), \quad \hat A_t = \delta_t + \gamma\lambda(1-d_t)\hat A_{t+1}, \quad \hat R_t = \hat A_t + V(s_t)
$$

- 시간 초과(truncated)는 실패 종료와 구분 → bootstrap 검토 (현재 구현은 timeout도 terminal → value 편향 가능)

| 항목 | 기준 | 조정 방향 | 볼 지표 |
|---|---|---|---|
| 학습률 | 3e−4 | 불안정하면 1e−4 | KL, 성능 급락 |
| clip ε | 0.2 | 갱신이 크면 0.1 | clip fraction |
| update epoch | 4 | 과적합이면 2 | KL, 새 평가 성능 |
| entropy 계수 | 0.005 | 탐색 부족 시 0.01 | 행동 std, 충돌 |
| gamma / lambda | 0.99 / 0.95 | 0.995 / 0.9 비교 | advantage 분산 |

- 좋은 정책 ≠ 마지막 파일 → 고정 평가(완주·충돌·시간)로 고름

## 8. 학습 실행
```shell
PY=~/IsaacLab/.venv/bin/python
$PY scripts/lab_python.py rl/train_ppo.py --iterations 100 --num-envs 8 --seed 7 --output runs/maze_ppo
scripts/run_predictive_async.sh evidence/repeat-first   # 최종 통합 평가
```

- 순서: 동작 부호·관절 제한 → 센서·TF → 보상 각 항의 **평균 크기** → PPO. 가중치는 한 번에 한 항씩, 같은 seed·경로로 비교

## 9. cuVSLAM과 팔 카메라
- 기본 개념은 [261019 VSLAM](../261019/ROS2.md#vslam). 이번 실습은 **VO만** 사용, 전역 보정은 EKF + AMCL
- 역할 구분: cuVSLAM = 위치 추정 / Nav2 = 경로·주행 제어 / PPO = 행동 학습
- 설정: `tracking_mode` 2(RGBD), `enable_imu_fusion` false (팔 카메라가 움직여 body IMU를 고정 extrinsic으로 못 묶음)
- 팔이 회전하는 시간만큼 앞을 미리 봐야 코너 진입 전에 관측 가능

## 10. 센서 통합
$$
T_{VB}(t) = T_{VC}(t)\,T_{BC}(q(t))^{-1}, \quad T_{MB}(t) = T^\text{AMCL}_{MO}(t)\,T^\text{EKF}_{OB}(t)
$$

- 카메라가 팔 위라 $T_{BC}$가 관절각에 따라 바뀜 → **영상 촬영 시각의 $q(t)$**로 FK (최신 관절각이면 팔 회전이 차체 이동으로 보임)
- 이중 IMU: body 축으로 회전 후 레버암 항을 빼서 기준점 값으로 맞춤. 두 값이 일치할 때만 평균, 불일치·누락이면 평균 금지
- 엔코더: atan2로 래핑 풀기 ($|\omega_\text{max}|\Delta t < \pi$), 속도는 약 30 ms 차분창 (짧으면 양자화 잡음)

## 11. EKF + AMCL + Nav2
- 프레임: EKF가 odom→base, AMCL이 map→odom ([261013](../261013/ROS2.md#mapodombase-프레임)). TF 발행자는 각각 하나씩만

| 입력 | 쓰는 것 | 빼는 것 | 이유 |
|---|---|---|---|
| wheel odometry | 차체 $v_x, v_y$ | 적분 위치 | 같은 정보 중복 융합 방지 |
| 이중 IMU | 보정 yaw rate | AHRS yaw | 공통 축·시각 |
| VO + 팔 FK | 위치 차분 → 속도 | VO yaw | 팔 회전과 차체 회전 분리 |

- AMCL: 스워브라 `OmniMotionModel`, scan은 팔 깊이로 만든 가상 scan ([261015 AMCL](../261015/ROS2.md#3-amcl--저장-지도에서-위치-추정))
- 이번 실행은 AMCL + EKF + 지정 경로, 주행 제어는 PPO + 제한기. **MPPI와 PPO가 동시에 명령하지 않게** 한 모드만 활성화
- MPPI([261015](../261015/ROS2.md#5-지역-계획제어--dwb와-mppi)) `motion_model`은 구동 구조와 일치, 미관측 방향은 안전한 빈 공간이 아님

## 12. 교안 시연 결과와 배운 점
- 교안 시연(M38, 내 결과 아님): 두 미로 모두 약 57~63 s, 목표 오차 약 4 cm, 접촉 0 N. 센서를 끊으면 0.355 s 안에 정지 후 재개
- 보상은 항마다 **한 step에 얼마인지** 검산해야 편법(정지·자살 종료·반복 수령)이 보임
- 정지거리 $v^2/2a$ 하나로 보상 벌점·안전 속도·배포 제한기를 일관되게 만듦
- 정책은 가감속·팔 방향만, 조향·제동 한계는 제한기 → 정책에 모든 걸 맡기지 않음
- 움직이는 카메라로 VO를 쓰면 **시각이 맞는 FK**가 필수
- 같은 정보를 두 경로로 EKF에 넣지 않음 (적분 위치·AHRS yaw·VO yaw 제외)
