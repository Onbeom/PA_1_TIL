# 내 로봇의 강화학습 — 용어, PPO 구조, MuJoCo 환경 설계, Isaac Lab 확장

> 학습일 2026-10-23, 정리일 2026-11-02 / 자료: Lv.2 강화학습 강의자료 (KANT, 91장 교안. 로컬 `ref/ROS2/`에만 보관)
> 관련: [261019 강화학습 기초·PPO](../261019/ROS2.md#강화학습) / [261020 Cartpole PPO 실습](../261020/ROS2.md#6-실습-4--isaac-lab-cartpole-ppo) / [261021 태스크 구성·도메인 랜덤화](../261021/ROS2.md#isaac-sim--isaac-lab-태스크-구성)
> 교안 한계: 제작 PC에서 MuJoCo·PyTorch 실행이 막혀 **실제 학습 수렴·Ubuntu·Isaac 실행은 미검증**. 이 문서에도 내 로봇 학습 결과는 없음

## 오늘의 목표
- 제출물: **각자 만든 로봇의 정책**. 예제만 돌리면 완료가 아님
- 필수: 내 URDF → MJCF 장면 + Gymnasium 환경 + SB3 PPO / 확장: 내 USD + Isaac Lab 태스크 + RSL-RL PPO
- 두 경로의 체크포인트는 서로 바로 못 읽음 (SB3 `policy.zip` ≠ RSL-RL 체크포인트)
- 다른 로봇의 관절 수·보상 계수는 복사하지 않음. 재사용하는 건 **학습 흐름과 함수 계약**뿐

## 이름 정리
| 이름 | 종류 | 하는 일 |
|---|---|---|
| PPO | 알고리즘 | 정책을 조금씩 개선 |
| SB3·RSL-RL | 알고리즘 구현 라이브러리 | PPO 실행 (RSL-RL은 로봇용, 모듈명 `rsl_rl`) |
| Gymnasium | 환경 규약 | `reset`·`step`·관측/행동 공간의 약속 |
| MuJoCo | 물리 엔진 | 관절·접촉 계산 |
| Isaac Sim / Isaac Lab | 시뮬레이터 / 학습 프레임워크 | 장면·물리 계산 / 태스크·벡터 환경을 학습기와 연결 |
| URDF·USD·MJCF | 자산 형식 | 로봇·장면 기술 |

- 같은 PPO라도 구현·정규화·하이퍼파라미터·환경이 다르면 결과가 다름

## 환경과 신경망
- 한 스텝: 관측 $o_t$ → 정책이 행동 $a_t$ → 구동기 → 물리 계산 → $o_{t+1}$, 보상 $r_t$, 종료 플래그
- State(시뮬레이터 전체 값) ≠ Observation(정책에 넘기는 값). Transition $(o_t, a_t, r_t, o_{t+1})$을 모은 묶음이 Rollout
- 목표가 바뀌는 과제면 **목표나 목표 오차를 관측에 넣어야** 함
- Actor $\pi_\theta$: 행동 선택. 학습 중엔 행동 분포에서 표본을 뽑아 탐색
- Critic $V(o_t)$: 앞으로 받을 수익 예측. 모터 명령 없이 advantage 계산에만 씀

## 보상, 수익, 가치, Advantage
$$
G_t = \sum_{k=0}^{T-t-1} \gamma^k \, r_{t+k}
$$

- $\gamma$가 1에 가까울수록 먼 미래까지 반영. **제어 주기를 바꾸면 같은 $\gamma$라도 실제 시간 범위가 바뀜**
- Advantage: 예상보다 얼마나 좋았나, $A_t \approx G_t - V(o_t)$. $A_t > 0$이면 그 행동 확률을 높임
- 예 (교안): 보상 1, 2, 3, $\gamma = 0.9$ → $G_t = 5.23$, $V(o_t) = 4$ → $A_t \approx 1.23$
- 실제 구현은 **GAE**: 여러 시간 범위 추정을 섞고 `gae_lambda`로 조절

$$
\delta_t = r_t + \gamma V(o_{t+1}) - V(o_t), \qquad \hat{A}_t = \sum_{l=0}^{\infty} (\gamma\lambda)^l \, \delta_{t+l}
$$

## PPO 갱신
- 식 자세한 건 [261019 PPO](../261019/ROS2.md#ppo). 교안 기호

$$
\rho_t(\theta) = \frac{\pi_\theta(a_t \mid o_t)}{\pi_{\theta_\text{old}}(a_t \mid o_t)}, \qquad
L(\theta) = \mathbb{E}_t\Big[\min\big(\rho_t A_t,\ \text{clip}(\rho_t, 1-\epsilon, 1+\epsilon)\, A_t\big)\Big]
$$

- $\theta_\text{old}$: 자료를 **모을 때**의 정책
- $\epsilon = 0.2$는 목적식에서 확률비 [0.8, 1.2] 밖의 개선 유인을 자를 뿐. **모터 출력 20% 제한이 아님**
- 실제 손실 = 정책 손실 + 가치 손실 + 엔트로피 항

| 로그 지표 | 뜻 | 볼 때 |
|---|---|---|
| entropy | 행동 분포가 퍼진 정도 | 탐색이 충분한지 |
| value loss | 가치 예측 오차 | Critic이 수익을 따라가는지 |
| approx_kl | 갱신 전후 정책 분포 변화량 | 한 번에 너무 바뀌는지 |

- 어느 지표도 **과제 성공을 판정하지 않음** → 평가는 따로

## 첫 목표와 MuJoCo 장면
- 첫 목표는 **수치로 검사할 수 있는 동작 하나** (바퀴: 속도 추종, 팔: 관절 자세 추종, 다족: 초기 자세 유지)
- 제공 환경은 "선택 관절의 속도 추종"이 출발점. **관절 속도가 맞는 것 ≠ 몸체 전진** (바퀴가 공중에서 돌아도 점수 높음)
- URDF 변환 XML은 시작점. 구동기·바닥·초기 자세·자유 베이스 확인, 메시 상대 경로 보존
- `nu` = actuator 개수. actuator가 없으면 `data.ctrl`로 못 움직임. 이름은 실제 모델에서 조회
- `motor`는 힘·토크, `velocity`는 속도 목표 → `ctrl_scale` 단위가 바뀜 (hinge rad/s·N·m, slide m/s·N)
- body(강체 좌표계) / geom(시각·충돌 형상) / site(기준점, 충돌 없음)
- 접촉은 soft contact(`solimp`·`solref`). 보상 튜닝 전에 비정상 접촉·관성·시간 간격부터 확인
- 연결 순서: 경로·단위 확인 → 관절·구동기 매핑 → 0·작은 입력 테스트 → 불안정하면 모델 수정 → 환경 함수 작성
  - 불안정한 모델을 PPO 설정으로 해결하려 하지 않음

## 환경 함수 설계 (Gymnasium 계약)
- 제어 관절 $J$개, 병렬 환경 $N$개: 관측 $(N, 3J)$(위치·정규화 속도·정규화 목표 속도), 행동 $(N, J)$, 보상 $(N,)$
  - 보상은 $J$축만 평균. **$N$축까지 평균 내면 안 됨**
- `qpos`, `qvel` 주소는 따로 조회. 좌표계를 맞춰 비교하고 yaw 오차는 ±π 경계에서 감싸기

| 함수 | 입력 → 출력 | 내용 |
|---|---|---|
| `__init__` | 설정 → 환경 | 모델 로드, 이름·주소 조회, 공간 선언 |
| `_get_obs` | 물리 상태 → float32 배열 | 관측 순서와 스케일 |
| `reset` | seed → `obs, info` | 초기 자세, 목표, 카운터 |
| `step` | action → 결과 5개 | 구동, 물리 진행, 점수, 종료 |
| `_reward` | action → 보상·오차 | 목표 항과 비용 항 (물리 진행 금지) |

- `step` 반환: `observation, reward, terminated, truncated, info`
  - terminated: 과제 자체가 끝남 (전복, 이탈) / truncated: 시간 한도 등 외부 중단
  - 기본 환경은 `terminated`가 항상 False → **내 로봇의 실패 조건을 직접 구현**
- 시간 (교안 예시): physics_dt 0.002s × decimation 10 = 정책 0.02s(50Hz), max_steps 250 = 5s 에피소드

## 보상 함수
$$
e = \frac{\dot q - \dot q_\text{goal}}{s_v}, \qquad
r = \underbrace{\exp\!\big(-\operatorname{mean}(e^2)\big)}_{\text{추종}} - \underbrace{0.01 \cdot \operatorname{mean}(a^2)}_{\text{행동 비용}}
$$

- 단위·범위가 다른 값은 정규화 후 합침. 주행이면 몸체 속도·yaw rate, 팔이면 끝단 위치 오차로 바꿈
- 함정: 비용 항이 크면 **가만히 있는 편이 유리**. 성공 즉시 종료 + 매 스텝 양의 보상이면 **일부러 늦게 끝냄**
- 손계산 검사: 잘하는 / 실패 / 가만히 있는 상태의 점수 순서가 맞는지
- `robot_config.json`: 관절마다 `drives` 항목. `ctrl_scale`(행동 ±1의 구동 크기), `velocity_scale`(오차 정규화 기준), `goal_range`
  - 설정 파일이 구동기를 자동으로 만들어 주지 않음 → 장면 XML에 먼저 준비

## 실행 흐름과 SB3 설정
```bash
.venv/bin/python code/robot_rl.py check --config assets/robot_config.json                                    # API 계약만 확인
.venv/bin/python code/robot_rl.py train --config assets/robot_config.json --steps 100000 --out runs/own-ppo  # 본 학습
.venv/bin/python code/robot_rl.py eval --config assets/robot_config.json --model runs/own-ppo/policy.zip --out runs/own-eval
```

- `check`는 함수 계약만 봄. 행동 부호·단위·접촉·전복은 따로 검증. 본 학습 전 `--steps 2048` smoke 실행

| 설정 | 의미 | 교안 기본값 |
|---|---|---|
| `learning_rate` | 한 번 갱신의 보폭 | 0.0003 |
| `n_steps` | 환경당 수집 길이 | 1024 |
| `batch_size` | gradient 한 번의 표본 수 | 256 |
| `n_epochs` | 같은 rollout 반복 학습 횟수 | 5 |
| `total_timesteps` | 전체 transition 목표 | 100000 |

- 1024개 수집 → 256개씩 4묶음 × 5 epoch = **20번 갱신** → 새 정책으로 다시 수집 (오래된 rollout 재사용 안 함)
- epoch은 에피소드 수가 아님. iteration 정의는 라이브러리마다 다름. 스텝 수가 성공 보증이 아님 ([261020](../261020/ROS2.md#학습-결과))

## 평가와 문제 해결
- 학습 수익 그래프는 단서일 뿐. 학습에 안 쓴 초기 조건으로 성공률·최종 오차·전복·구동 한계 초과를 봄
  - 기준선(무동작·무작위·기존 제어기)과 비교, 실패 사례도 기록, `deterministic=True`
- 편법 찾기: 바퀴만 돌고 몸체는 안 감, 목표 근처 진동, 한 초기 자세에만 맞는 정책

| 순서 | 질문 | 아니면 |
|---|---|---|
| 1 | 수동 입력에 정상 반응? | 구동기 이름·방향, ctrl 범위, 충돌 검사 |
| 2 | 관측·보상이 모두 유한값? | NaN 발생 시점 추적 |
| 3 | 목표 행동의 보상이 더 큰가? | 수치 사례로 보상 수정, 종료·리셋 검사 |
| 4 | 위 셋 통과 | 관측 정보·행동 범위·평가 규약 확인 |

- PPO 하이퍼파라미터 조정은 **그다음**. 한 번에 한 항목만
- 저장 정책은 관측 순서·행동 스케일·정규화 통계(`VecNormalize`)가 학습 때와 같아야 함. 로드된다고 호환되는 건 아님

## Isaac Lab + RSL-RL 확장
- **Isaac Lab = 환경**(물리 상태·관측·보상·종료), **RSL-RL = 학습**(Runner·정책/가치 모델·rollout storage·PPO)
- Direct 방식 함수 ([261021 Manager와 비교](../261021/ROS2.md#manager-방식과-direct-방식))
  - `_pre_physics_step`(행동 스케일) → `_apply_action`(구동기) → `_get_observations` → `_get_rewards` $(N,)$ → `_get_dones`(terminated, truncated) → `_reset_idx`(끝난 환경만)
- Lab 3.0 기본은 Newton 백엔드. `physics=isaacsim_physx`가 물리 선택, `--viz none`은 화면만 끔
- `uv run isaaclab --new` → External project, Direct single-agent, rsl_rl, PPO → 생성 예제 확인 후 로봇·관측·보상 교체 → `train` → `play`
- MuJoCo → Isaac은 **설계 의도**만 옮김. 좌표계·접촉·시간 간격은 다시 검사하고 따로 학습·평가

## 확인 문제 (내 답)
1. 병렬 환경은 수집 경험을 어떻게 늘리나? → 같은 정책으로 $N$개 환경을 진행해 한 번에 환경당 스텝 × $N$개 transition
2. 쉬운 지형에서 어려운 지형으로 바꾸는 이유는? → 처음부터 어려우면 실패만 해서 보상 신호가 없음 ([커리큘럼](../261021/ROS2.md#커리큘럼과-adr))
3. $\epsilon = 0.2$면 모터 출력이 20%로 제한되나? → 아님. 확률비 개선 유인만 자르고 모터 한계는 구동기·행동 스케일에서 정함
