# 로봇팔 제어와 정책학습 — MoveIt 2 · cuMotion · Isaac Lab (Isaac Sim 6.1 · ROS 2 Lyrical)

> 학습일 2026-10-30 (자료를 받은 날 기준), 정리일 2026-11-02
> 자료: 로봇팔 제어와 정책학습 · Isaac Sim 6.1 · ROS 2 Lyrical (KANT, 64장. 로컬 `ref/ROS2/`에만 보관)
> 실습 저장소: [SpartaPA/manipulator-isaac61-lyrical-practice](https://github.com/SpartaPA/manipulator-isaac61-lyrical-practice) (비공개)
> 이전: [261019 Isaac 생태계와 강화학습](../261019/ROS2.md#nvidia-isaac-생태계와-강화학습) · [261021 Waffle 4WD URDF·MoveIt·USD](../261021/ROS2.md)

## 오늘의 목표
- 직접 만든 URDF 로봇으로 목표 위치까지 이동 → 같은 작업을 학습 정책으로 수행 → 같은 조건에서 비교
- **URDF를 불러온 것 ≠ 작업 성공** → 단계마다 통과 기준을 따로 둠

## 1. 버전과 지원 범위
| 구성 | 실습 기준 | 확인할 점 |
|---|---|---|
| ROS 2 | Lyrical (LTS) | Ubuntu 24.04(Noble), Isaac ROS Buildfarm 패키지 |
| Isaac ROS | 5.0 | Lyrical용 패키지 |
| Isaac Sim | 6.1.0 | Lyrical 브리지는 실험적 경로 |
| Isaac Lab | v3.0.0-EA | Sim 6.1 대응. 정식·LTS 아님 |

- Lab 정식 v3.0.0은 Sim 6.2 대상 → Sim 6.1을 유지하려면 EA 태그에 고정
- ROS·Ubuntu가 LTS여도 NVIDIA 스택 전체가 LTS가 되는 건 아님
- Sim 6.1 브리지의 공식 권장은 Humble·Jazzy → Lyrical은 관절·TF·시계·Action이 모두 통과하기 전에는 "통합 성공"이라 쓰지 않음

## 2. 전체 구조: 계획 · 제어 · 학습
- 계획기(planner): 경로·궤적 생성 / 제어기(controller): 실제 상태를 읽으며 구동기에 명령 / 정책(policy): 관측을 보고 행동 선택
- 흐름: 카메라·관절 피드백 → 인식·좌표변환(TF) → 계획 또는 정책 → 구동기. 시간·좌표계·관절 이름을 모든 단계에서 일치
- **계획 궤적 추종과 정책 추론은 다른 실행 모드** → 같은 관절에 두 노드가 동시에 명령하지 않게 명령 모드 선택기(selector)를 둠

## 3. 로봇 기술 파일: URDF · SRDF · XRDF · USD
| 파일 | 맡는 것 | 쓰는 곳 |
|---|---|---|
| URDF | 링크·관절·질량·형상 (기구) | ROS 전체, 변환의 출발점 |
| SRDF | 계획 그룹, 엔드 이펙터, 충돌 제외 쌍 | MoveIt |
| XRDF | 충돌 구(sphere), cuMotion용 로봇 구성 | cuMotion(cuRobo 기반 GPU 계획기) |
| USD | 물리·센서·장면 | Isaac Sim / Lab |

- **관절 이름과 TCP(도구 기준점)는 네 파일 모두에서 같아야 함**
- Waffle 4WD는 URDF → SRDF → USD까지 만듦([261021](../261021/ROS2.md)). XRDF는 아직 없음

## 4. 기구학
- 순기구학(FK): 관절값 $q$ → TCP의 위치·자세
  - $T_{\text{base,TCP}}(q) = T_1(q_1)\,T_2(q_2)\cdots T_n(q_n)$ ($T_i$: $i$번째 관절의 4×4 동차 변환)
  - 확인법: 관절 하나씩 (+) 방향으로 움직여 URDF의 축 방향·원점 확인
- 역기구학(IK): 목표 TCP → 관절값
  - 해가 여러 개(팔꿈치 위/아래)거나 없을 수 있음 → 관절 한계·충돌·현재 자세와의 거리로 선택
  - 자유도가 부족한 팔에 임의의 6D 자세를 요구하지 않음 (Waffle 4WD 5자유도 팔의 `position_only_ik: true`와 같은 이야기)

## 5. MoveIt Setup Assistant
- 교안 예제는 Panda, 실습은 자기 로봇으로 진행
- 계획 그룹: `arm`에 넣을 관절 체인 선택. **집게 관절을 팔 체인에 섞지 않음**
- 엔드 이펙터: 손목 링크와 TCP는 다를 수 있음 → 목표 좌표가 어느 링크에 걸리는지 확인
- 자기충돌 제외 목록: 자동 결과를 그대로 믿지 말고 실제 관절 범위에서 확인, 제외 이유 기록

## 6. 충돌 검사와 cuMotion
- 검사 대상: 팔 + 집게 + **잡은 물체**. 충돌 쌍을 다 제외하면 경로는 쉽게 나오지만 실제로는 통과 불가
- XRDF 충돌 구: 너무 작음 → 충돌을 놓침 / 너무 큼 → 지나갈 통로를 막음
- cuMotion: GPU로 로봇 모델·목표·장애물을 함께 고려한 궤적을 계산
  - 필요한 것: MoveIt 플러그인 + cuMotion 서버 + 내 URDF/XRDF
  - 모터 통신은 ros2_control·드라이버 담당. 계획 계산 시간 ≠ 전체 시스템 지연 (추종·통신 포함)
  - cuRobo(V2)는 GPU 운동 생성 연구 도구 → 공통점은 GPU 계획이지만 구현은 구분
- nvblox: 깊이 영상 + TF로 형상 지도를 갱신해 장애물로 사용. 보정·TF·시간 맞춘 뒤 ESDF 연결 (초기 실습은 `read_esdf_world=false`)

## 7. 제어: ros2_control · Servo · 힘 제어
- ros2_control: controller → hardware interface → 모터·센서
  - command interface: 목표를 씀 (구동기가 **실제로 지원하는** position / velocity / effort)
  - state interface: 관절 상태를 읽음
  - 명령값을 측정값처럼 되돌려 보내지 않음 (가짜 피드백이면 추종 실패를 못 봄)
  - 컨트롤러 이름·관절 목록·MoveIt Action 경로를 맞춤. **계획 성공과 실행 성공은 따로 확인**
- MoveIt Servo: 짧은 주기로 오차를 반복 보정. 전역 이동 = 계획기, 마지막 위치 보정 = Servo
- 힘 제어: 임피던스(위치 오차 → 힘) vs 어드미턴스(측정된 힘 → 운동)
  - 모터 전류만으로 손목 외력을 정확히 안다고 가정하지 않음 → 센서·구동기 기능·주기·안정성 먼저 확인

## 8. 작업 구조: 접근 → 집기 → 놓기
- 목표 자세 하나로 집기 작업 전체를 설명할 수 없음
- 접근 전 장애물 확인 → 집게 닫힘 확인 → 옮기는 동안 물체 유지 확인 → 놓은 뒤 손 떼기
- 실패 시 재탐색 / 재접근 / 종료 중 어디로 갈지 미리 정함 → 상태 머신. MTC(MoveIt Task Constructor)가 이를 다룸

## 9. 정책학습 (Isaac Lab)
- RL 용어·PPO 식은 [261019 강화학습](../261019/ROS2.md#강화학습)·[PPO](../261019/ROS2.md#ppo), 수치 예는 [261020 PPO 설정](../261020/ROS2.md#ppo-설정-rsl_rl-onpolicyrunner)
- 정책 $a_t \sim \pi_\theta(a \mid o_t)$: 학습 = $\theta$를 바꿈 / 추론 = 고정된 가중치로 실행
- PPO = 정책 갱신 **알고리즘**, RSL-RL = 학습을 돌리는 **라이브러리**
- 시뮬레이터만 아는 참값은 **Critic에만** 넣을 수 있음. 배포할 Actor 입력은 실기에서 얻을 수 있는 값이어야 함

| 항목 | 넣을 것 / 정할 것 | 주의 |
|---|---|---|
| 관측 | 관절 위치·속도, TCP 오차, 집게 상태, 이전 행동 | 이름·순서·단위·좌표계 문서화 |
| 행동 | 관절 위치 / 증분 / 속도 / 토크 중 하나 | 기준값 명시 |
| 보상 | 목표 접근, 동작 변화 비용, 충돌 비용, 작업 성공 | 성공 판정을 별도 항으로 |
| 리셋·종료 | 초기조건 샘플 / 성공·실패·시간 종료 | 실패 종료와 시간 종료 구분 |

- 행동 변환: $q_\text{target} = \text{clip}(q_\text{ref} + s \cdot a,\ q_\text{min},\ q_\text{max})$
  - $q_\text{ref}$가 **현재 관절값인지 고정 기준(기본 자세)인지** 반드시 적어 둠
- 보상: $r = -w_d\,d - w_a\lVert \Delta a \rVert^2 - w_c\,c + w_s\,s$
  - $d$: 목표까지 거리, $\Delta a$: 직전 대비 행동 변화, $c$: 충돌, $s$: 성공
  - 거리만 줄이고 물체를 놓치는 편법을 막으려고 성공 판정을 따로 둠
- 종료: terminated(낙하·충돌 등 상태 때문) vs truncated(시간 제한)
- Task 만들기: `robot_cfg` / `env_cfg` / `observations` / `rewards` / `terminations` 채움, 실제 관절 이름·자유도 사용 ([261021 태스크 명세](../261021/ROS2.md#태스크-명세))
- 실행 순서: 무행동 → 작은 임의 행동 → 짧은 PPO 학습 → checkpoint 재생 → 병렬 규모 확대
- Lab 3.0 EA는 통합 `isaaclab train/play` 명령, 물리 백엔드 명시 (`physics=isaacsim_physx`)

## 10. 평가와 Sim-to-Real
- 학습 보상만 보지 않음 → 학습에 안 쓴 초기조건(holdout)에서 성공률·실패 유형 측정
- 기록: 성공 횟수/총 시도, 위치 오차, 충돌, 완료 시간, 추론 지연
- 계획기 · PPO · 모방학습을 같은 목표·같은 초기조건으로 비교
- 현실 이전: 단일 관절·접촉 응답으로 모델 보정 → 측정한 범위에서 [도메인 랜덤화](../261021/ROS2.md#도메인-랜덤화) → 실제 실패 원인과 비교

## 11. 모방학습과 VLA
- 모방학습: 시연의 (관측, 행동)을 정답 쌍으로 학습 ([261019 모방학습](../261019/ROS2.md#모방학습))
  - train/validation/test는 **에피소드·촬영 세션 단위로** 나눔 (프레임 단위로 섞으면 성능이 부풀려짐)
  - Isaac Lab Mimic: 원격 조작 시연을 다른 물체 배치로 옮겨 데이터를 늘림. 작업 구간·물체 프레임·성공 조건은 직접 정의

| 방법 | 핵심 |
|---|---|
| BC (행동 복제) | 시연 행동을 그대로 맞추도록 학습 |
| ACT | Transformer로 행동 묶음(chunk)을 한 번에 예측 |
| Diffusion Policy | 잡음에서 시작해 반복 잡음 제거로 행동 시퀀스를 복원 |

- 비교할 땐 같은 데이터에서 입력·출력·주기·평가를 맞춤. Diffusion은 여러 단계 추론 → 지연 측정
- VLA(GR00T): 영상·언어·로봇 상태 → 행동 ([261019 VLA](../261019/ROS2.md#vla))
  - 새 로봇에는 **자체 데이터** 필요: 같은 시각 기준 저장 → modality 설정 → 미세조정 → 폐루프 평가

## 12. 배포와 문제 진단
- 배포 구조: 관측 어댑터 → 정책·제한·선택 → 구동기 드라이버
  - 상태가 오래되었거나(watchdog) NaN이면 유지 또는 정지. 계획기·Servo·정책 중 **하나만** 제어권을 가짐
- 진단 순서: 모델 형상 → 한 관절 → 상태 수신 → 작은 명령 → 계획 → 학습
  - 여러 개를 한꺼번에 바꾸지 않음. 학습 전 단계 실패를 긴 학습으로 해결하려 하지 않음
- ROS 브리지 통과 순서: `/clock` → `/joint_states` → TF → 작은 명령 → Action 결과
- 완료 기준: 다른 사람이 재현하고 성공·실패 원인을 확인할 수 있어야 함. 실기 미검증 항목은 미검증으로 표시

## 실습
- 실습 저장소 README 흐름: CPU만으로 예제 3축 팔 점검·단위 테스트(설치 점검용일 뿐 학습·실물 성공 아님)
  → URDF 점검 → USD 변환 → 내 팔 Reach Task 학습·재생 → MoveIt 2/cuMotion 설정 → Lyrical과 Sim 연결 검증

```shell
# Isaac ROS 컨테이너 안에서 배포판·cuMotion 확인
isaac-ros activate
printenv ROS_DISTRO
ros2 pkg prefix isaac_ros_cumotion

# 자기 로봇 MoveIt 설정 생성 (가상 제어로 OMPL 계획 먼저, 그다음 cuMotion)
ros2 launch moveit_setup_assistant setup_assistant.launch.py

# Lab 환경은 Isaac ROS 컨테이너와 다른 호스트 폴더에 별도 설치 후 학습
bash scripts/install_lab.sh
bash scripts/lab.sh train --task Practice-Reach-OwnArm
```

- 순서 원칙: 가상 Plan·Execute(OMPL)로 설정 확인 → cuMotion 서버와 planning YAML 추가 → 비교
- 실행 결과는 이 TIL에 기록하지 않음
