# Waffle 4WD 로봇 URDF → ROS 확인 → MoveIt 충돌 확인 → Isaac Sim USD

> 작업일·정리일 2026-10-21. 전부 모의(시뮬레이션·정적 검사)이고 실물 시험 아님
> 학습자료: Isaac Sim / Isaac Lab 태스크 구성 (KANT Lv.2 55), 도메인 랜덤화 (KANT Lv.2 56). 로컬 `ref/ROS2/`에만 보관
> 강의 정리는 아래 [Isaac Sim / Isaac Lab 태스크 구성](#isaac-sim--isaac-lab-태스크-구성), [도메인 랜덤화](#도메인-랜덤화)
> 작업 위치: `~/git/lv2_next_module/` (URDF는 `mine/`, 작업 공간은 `sim_ws/`, Isaac 관련은 `sim/`)
> 이전: [261020 Isaac Sim 6.1·Lab 실습](../261020/ROS2.md)

## 1. 받은 자료와 로봇 구성
- 받은 것 (내가 만든 URDF와 CAD)
  - `urdf.zip`: ROS 패키지 `waffle_4wd_description_261021`
  - `CADai.zip`: CAD·검증 인수인계 묶음, `Assembly_Modular_261021.step`·`.f3d`
  - `VALIDATION_PENDING_AND_FAILURES.md`: 아직 검증 안 된 것과 실패 목록
- 로봇 구성
  - 4륜 구동: XM430-W210 4개
  - 로봇팔: 팔 5관절 + 집게 개폐 모터 (모터 6개)
  - 카메라 3개: Intel RealSense 2개(상단 전·후), Arducam 1개(팔 끝)
  - 라이다: 실물 3개 중 URDF에는 2개만 있음 → 시뮬레이션은 2개로 가정

### URDF 요점
| 항목 | 값 |
|---|---|
| 구조 | 23링크·22관절 (물리 링크 14 + 고정 논리 프레임 9), root `base_footprint` |
| 질량 합 | 4,891.194g (CAD 추정) |
| 바퀴 | 반지름 33mm, 좌우 간격 279.2mm, 앞뒤 간격 160mm |
| 구동 방식 | 네 바퀴 축이 모두 +Y (양수 회전 = 전진) → 스키드 스티어 |
| 팔 관절 범위 | 임시값 (shoulder ±1.5rad 등) |
| effort | 11.1V 순간 stall 값 (팔 3.8N·m, 바퀴 2.7N·m). **연속 허용값 아님** |
| 집게 | 오른쪽 = 왼쪽 × (−1) mimic |

- 스키드 스티어: 바퀴 방향은 고정, 좌우 바퀴 속도 차이로 회전 (바퀴가 옆으로 미끄러지며 돎)
- mimic: 한 관절이 다른 관절 값을 따라가게 하는 URDF 기능 → 집게는 모터 하나로 양쪽이 대칭으로 열리고 닫힘

### 인수인계 문서의 가장 중요한 경고
- 기존 G채널 투입·회수 동작 402자세 중 **159자세가 어깨 상한(1.5rad)을 넘음** (최대 1.912rad)
- 한계를 넓히거나 값을 잘라내는 것은 금지
- 물성·토크는 추정값. ROS·Isaac 실행은 이전에 한 번도 안 됨

### 미검증 항목은 언제 처리하나
- 전부 고치고 시작하지 않음

| 항목 | 처리 시점 |
|---|---|
| ROS 확인, Isaac 가져오기 | 지금 (그 자체가 검증) |
| 충돌 근사, 구동 설정 | 동작 시험 단계 |
| 어깨 범위 문제(159자세) | 퍽 집기 학습 전 (실측 한계 확정 또는 범위 안 새 경로) |
| PLA 강도·출력, 모터 열, 배선, 캘리브레이션 | 실물 단계 (미검증 유지) |

- 이후 강화학습 순서: ① 팔 목표 자세 도달(차체 고정, 상태 기반) → ② 주행 목표 이동 → ③ 퍽 집기. YOLO(별도 venv)는 맨 마지막
  - 강의의 "같은 로봇, 다른 태스크"와 같은 생각: 같은 로봇으로 목표 도달(위치 오차 줄이기) → 집기(물체 이동·유지 판정)로 태스크만 바꿔 감

## 2. 설치
```shell
# RViz 관절 슬라이더(display.launch.py에 필요). 설치 후 2.4.3 확인
sudo apt install ros-lyrical-joint-state-publisher-gui
# 충돌 확인용 MoveIt 2. 설치 후 moveit·moveit-setup-assistant 2.15.0 확인
sudo apt install ros-lyrical-moveit ros-lyrical-moveit-setup-assistant
```

## 3. 1단계: ROS 확인 (6개 모두 성공)
```shell
# (1) 파싱·트리 → "Successfully Parsed XML", root base_footprint, 링크 23개 단일 트리
check_urdf ~/git/lv2_next_module/mine/urdf/waffle_4wd_description_261021/urdf/waffle_4wd.urdf

# (2) 작업 공간: mine/의 패키지를 링크로 연결하고 빌드 → 빌드 성공, package:// 메시 504개 모두 실재
mkdir -p ~/git/lv2_next_module/sim_ws/src
ln -s ~/git/lv2_next_module/mine/urdf/waffle_4wd_description_261021 ~/git/lv2_next_module/sim_ws/src/waffle_4wd_description_261021
cd ~/git/lv2_next_module/sim_ws && colcon build --packages-select waffle_4wd_description_261021

# (3) xacro 펼치기($(find 패키지) 때문에 빌드 후에만 가능) → 링크·관절 이름과 수치가 .urdf와 차이 0
source ~/git/lv2_next_module/sim_ws/install/setup.bash
xacro ~/git/lv2_next_module/mine/urdf/waffle_4wd_description_261021/urdf/waffle_4wd.urdf.xacro > /tmp/xacro_expanded.urdf

# (4) RViz 표시 → 노드 3개 오류 0, 슬라이더 10개(바퀴 4, 팔 5, 왼쪽 집게 1; 오른쪽 집게는 mimic이라 없음)
export ROS_DOMAIN_ID=26 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch waffle_4wd_description_261021 display.launch.py

# (5) TF(관절 0 자세, base_footprint 기준)
ros2 run tf2_ros tf2_echo base_footprint camera_optical_frame
```

- 패키지를 복사하지 않고 심볼릭 링크로 작업 공간에 넣음 → 원본(`mine/`)을 고치면 작업 공간에도 바로 반영
- `package://` 경로는 빌드·source 후에야 실제 폴더로 풀림 → xacro도 빌드 뒤에 펼침
- (6) 화면 확인: 모양 정상, 슬라이더 10개, 관절과 집게 mimic 동작 확인

| 프레임 | 위치 (m) | 렌즈 방향 |
|---|---|---|
| Arducam `camera_optical_frame` | (0.336, 0, 0.374) | 앞쪽 아래 40.8° (설계값 40.83°와 일치) |
| RealSense 전 `top_camera_front_optical_frame` | (−0.061, 0, 0.490) | 앞쪽 아래 35.3° |
| RealSense 후 `top_camera_rear_optical_frame` | (−0.220, 0, 0.490) | 뒤쪽 아래 35.3° |
| 라이다 전 `lidar_front_scan` | (0.185, 0.050, 0.068) | 전방 |
| 라이다 후 `lidar_rear_scan` | (−0.185, −0.050, 0.068) | 후방 (yaw 180°) |

### 카메라가 아래를 보는 것처럼 보였던 이유
- RealSense 본체는 설계부터 아래로 숙여 장착함 → 세 카메라 모두 실물과 같은 방향, 문제 없음
- RViz TF 표시의 노란 선은 카메라 시선이 아니라 **부모-자식 프레임 연결선**
- `*_optical_frame`과 `*_link`는 원점이 같고 회전만 달라 겹쳐 보임
  - `*_link`: x(빨강)가 앞 (ROS 몸체 좌표 규칙)
  - `*_optical_frame`: z(파랑)가 렌즈 방향, x 오른쪽, y 아래 (영상 좌표 규칙)
- 남은 확인: RealSense 설계 기억값 약 42° vs URDF 광축 35.3°(CAD 렌즈 원통 축 기준), 약 7° 차이 → 일단 35.3° 사용, 실물 캘리브레이션 때 측정

## 4. 자기충돌과 관절 연동 제한
- 팔 관절 범위는 다른 관절 상태에 따라 줄어들어야 함 (팔-차체, 팔-팔 충돌)
- URDF·Isaac의 관절 한계는 관절마다 고정된 최소~최대뿐 → "어깨가 이 각도면 팔꿈치는 여기까지" 같은 연동 제한은 못 넣음
- 자기충돌(self-collision)
  - Isaac(PhysX)은 기본적으로 같은 로봇의 링크끼리 통과함
  - 켜면 링크끼리도 충돌 계산 → 부딪히는 자세에서 더 못 움직임 (관절로 바로 붙은 쌍은 자동 제외)
  - 한계 값이 바뀌는 게 아니라 충돌로 막혀서 결과적으로 범위가 줄어드는 효과
- 한계
  - 히트박스(단순 box)가 실제보다 크면 일찍, 작으면 늦게 막힘
  - 모터가 계속 밀면 떨림·큰 힘이 생길 수 있음 → 강화학습에서는 충돌 벌점·종료를 함께 둠
- 결정: 시뮬레이션은 자기충돌을 켜고, 연동 제한 표는 실물 로봇을 가져온 뒤 만듦

## 5. MoveIt 2 충돌 확인 (5개 모두 성공)
- 새 패키지 `sim_ws/src/waffle_4wd_moveit_config`. URDF는 수정하지 않음
- SRDF: URDF에 없는 "계획용 정보"(관절 묶음, 충돌 검사 제외 쌍 등)를 따로 적는 파일

```shell
# SRDF(waffle_4wd.srdf) 요점
#  - group arm: chain base_link → arm_link_5 (5관절), group gripper: gripper_left/right_joint(오른쪽은 mimic)
#  - virtual_joint fixed(world → base_footprint): 충돌 확인은 차체 고정 상태로
#  - 바퀴 4개는 passive_joint(팔 계획 대상 아님)
#  - 충돌 검사 제외(disable_collisions)는 관절로 바로 붙은 인접 13쌍만
# kinematics.yaml: KDL, position_only_ik: true (팔이 5자유도라 6자유도 자세 IK는 일반적으로 안 풀림)
# joint_limits.yaml: URDF 임시 속도 그대로(팔 0.5 rad/s, 집게 0.01 m/s), 가속도 한계는 아직 없음

# 제외할 충돌 쌍 계산(인접 + 관절 0 자세에서 닿는 쌍 + 항상 닿는 쌍)
ros2 run moveit_setup_assistant collisions_updater --urdf <설치된 패키지>/urdf/waffle_4wd.urdf --srdf config/waffle_4wd.srdf --output with_default.srdf --default --always --trials 0
# → 인접 13쌍, 기본 자세·항상 닿는 쌍 0개. 그런데 --trials 0인데도 "한 번도 안 닿음(Never)" 49쌍을 제외하자고 제안했고,
#   그중 arm_link_2–base_link(팔-차체), arm_link_3–arm_link_5(팔-팔)처럼 찾으려는 충돌 쌍이 있어 넣지 않았다(인접 13쌍만 SRDF에 기록)

# 빌드·실행(궤적 실행 없이 move_group + RViz MotionPlanning)
cd ~/git/lv2_next_module/sim_ws && colcon build
ros2 launch waffle_4wd_moveit_config collision_check.launch.py

# 자세별 충돌 검사 도구(/check_state_validity 서비스 호출), 인자 [yaw shoulder elbow pitch roll] rad
python3 ~/git/lv2_next_module/sim/tools/check_arm_collision.py
python3 ~/git/lv2_next_module/sim/tools/check_arm_collision.py 0 1.4992378274631293 -1.3997540600994522 1.6999506914424771 0
python3 ~/git/lv2_next_module/sim/tools/check_arm_collision.py 0 1.5 1.5 1.7 0
```

- position_only_ik: 5자유도 팔은 끝점의 위치(3)와 방향(3)을 동시에 마음대로 정할 수 없음 → 위치만 맞추는 IK로 설정
- 충돌 제외 쌍을 자동 제안대로 다 받으면 안 됨
  - "Never"는 무작위 자세 샘플링에서 안 닿았다는 뜻인데, 샘플 0개(`--trials 0`)로도 제안이 나옴
  - 찾으려는 팔-차체·팔-팔 충돌까지 검사에서 빠지게 됨 → 인접 쌍만 제외

| 항목 | 결과 |
|---|---|
| 빌드 | 성공 |
| move_group | "You can start planning now!", 그룹 arm·gripper 인식. 로그 ERROR 3건(3D 센서 없음, 컨트롤러 없음, `/recognize_objects` 없음)은 일부러 안 넣은 기능이라 정상 |
| 관절 0 자세 | 충돌 0쌍 |
| 인수인계의 접은 시험 자세 [0, 1.499, −1.400, 1.700, 0] | 충돌 0쌍 |
| 극단 자세 [0, 1.5, 1.5, 1.7, 0] | 충돌 3쌍: base_link–arm_link_3 (겹침 8.4mm), base_link–arm_link_4 (3.4mm), gripper_right_link–lidar_rear (14.8mm) |
| RViz 화면 | MotionPlanning > Joints 탭에서 팔을 움직이면 충돌 링크가 빨간색으로 바뀜 |

- 겹침 값은 히트박스 기준이라 실제와 다를 수 있음
- 실수: RViz 설정 파일의 Panels에 MotionPlanning을 잘못 넣어 "plugin failed to load" → 그 항목을 지우고 해결
  - MotionPlanning은 패널이 아니라 Displays 항목으로 들어가는 플러그인

## 6. 2단계 일부: Isaac Sim USD 생성 (USD 생성 성공, importer 오류 0)
- 강의의 "URDF를 가져온 뒤 확인할 것": 길이·질량 단위 / 관절 축·한계·고정 베이스 / 충돌 형상과 관절 드라이브
  - 가져오기 설정이 이 항목들과 그대로 대응됨

```shell
# ~/git/lv2_next_module/sim/isaac/import_waffle_4wd.py (Isaac Sim 6.1 URDF importer 3.11.10, 창 없이 실행)
# merge_fixed_joints=False    : 카메라·라이다 프레임 9개를 합치지 않고 보존
# collision_from_visuals=False: URDF 충돌 형상(box 48, cylinder 4, convex STL 490)을 그대로 사용 → MoveIt과 같은 히트박스
# fix_base=False              : 이동 로봇이라 바닥에 고정하지 않음
# allow_self_collision=True   : 팔-팔, 팔-차체 충돌로 움직임이 막히게 함
# joint_drive_type='force', joint_target_type: Wheel_.* = velocity, RMX52_.* = position, gripper_.* = position
# 강성·감쇠는 지정하지 않음(동작 시험 단계에서 가설을 세워 정함)
~/isaacsim-venv/bin/python import_waffle_4wd.py --urdf <설치된 패키지>/urdf/waffle_4wd.urdf --package-dir <설치된 패키지> --out ~/git/lv2_next_module/sim/isaac/usd/waffle_4wd_r1 --/crashreporter/url=
```

- 관절 드라이브 (강의: 정책이 목표를 내면 드라이브가 그 목표를 추종)
  - 바퀴는 속도 목표, 팔·집게는 위치(목표각) 목표
  - 추종하는 힘은 대략 $\tau = k_p(q_\text{목표} - q) + k_d(\dot q_\text{목표} - \dot q)$ → 강성 $k_p$·감쇠 $k_d$·출력 제한을 정해야 실제로 움직임
  - 이번에는 강성·감쇠를 비워 둠 → 동작 시험 전에 정하고 기록해야 함
- 결과: `sim/isaac/usd/waffle_4wd_r1/waffle_4wd/waffle_4wd.usda` + `payloads/` (19MB)
  - 경고 "Stiffness and damping not available" 관절 11개: 강성·감쇠를 일부러 비워서 생긴 예상 경고
  - 파일 참조가 모두 상대 경로 → 폴더째 옮기면 다른 PC에서도 열림
- 남은 판정 (다음에): USD를 다시 열어 단위, 질량 4.891194kg, 관절 한계, mimic, 센서 프레임, 충돌 형상 542개, 자기충돌 설정 확인
- 주의
  - 이 importer는 mimic을 NewtonMimicAPI로만 기록함 → PhysX에서 오른쪽 집게가 실제로 따라 움직이는지 확인 필요
  - MoveIt은 충돌 메시를 그대로, Isaac은 convex hull로 계산 → 관절 0 자세에서 Isaac에만 겹침이 생길 수 있음

## 7. USD란
- USD(Universal Scene Description): Pixar가 만든 3D 장면 파일 형식, Isaac Sim의 기본 형식
- URDF 로봇을 Isaac Sim에서 쓰려면 USD로 바꿔야 함
- URDF는 "로봇 설계도", USD는 "그 로봇이 들어간 시뮬레이션 장면 파일"

| | URDF | USD |
|---|---|---|
| 쓰는 곳 | ROS (RViz, MoveIt, robot_state_publisher) | Isaac Sim, Isaac Lab, Omniverse |
| 담는 내용 | 링크·관절 구조, 질량·관성, 메시 경로 | 장면 전체(바닥·조명·카메라·물체)와 물리 설정(관절 구동, 충돌, 자기충돌, 마찰) |
| 메시 | 바깥 파일을 가리킴 (`package://...`) | 형상 데이터를 안에 담음 |
| 형식 | XML 하나 | 텍스트(.usda)·이진(.usd), 여러 파일을 층(layer)으로 겹쳐 씀 |

### OpenUSD 기본 단위 (강의)
| 용어 | 뜻 | 이번 USD에서 |
|---|---|---|
| Stage | 조합된 전체 장면 | `waffle_4wd.usda`를 열면 만들어지는 장면 |
| Prim | 경로로 찾는 장면 요소 | 링크·관절이 각각 prim (강의 예: `/World/Robot/base_link`) |
| Attribute | 위치·재질 등 속성 | 질량, 관절 한계, 드라이브 값 |
| Reference·Payload | 다른 파일의 내용을 가져다 씀 | `waffle_4wd.usda`가 `payloads/` 파일들을 참조 |
| Layer | 같은 장면에 겹쳐 쓰는 파일 층 | 구조·형상·물리를 파일별로 나눠 겹침 |

- 강의 권장: 공용 로봇 자산은 참조로 쓰고, 실험별 변경은 별도 레이어로 관리 → 원본 로봇 파일을 안 건드림

### 이번 USD의 파일 구성
| 파일 | 내용 |
|---|---|
| `waffle_4wd.usda` | 여는 파일 |
| `payloads/base.usda` | 링크·관절 구조 |
| `payloads/geometries.usd` | 표시 메시·히트박스 (약 19MB) |
| `instances.usda`, `materials.usda` | 메시 재사용, 재질 |
| `payloads/Physics/physics.usda` | PhysX 물리 설정 |
| `mujoco.usda`, `physx.usda` | 다른 엔진·세부 설정 |

- 그래서 .usda 하나만 옮기면 참조가 끊김 → **폴더째** 옮겨야 함 (강의: 파일 이동 시 참조 경로도 확인)
- Isaac Lab 강화학습도 이 USD를 로봇 자산으로 불러옴

## 8. 다른 담당자용 인수인계 묶음
- `~/git/lv2_next_module/handoff_teammate/`
  - `waffle_4wd_usd_r1.zip`
  - `COMMANDS_waffle_4wd_sim.md`: 기준 환경 버전, 환경 확인·설치·파일 해시·확인 명령과 이 PC 결과, 남은 일, 결과가 달라질 수 있는 요인, 부록(MoveIt 설정·도구·가져오기 스크립트 10개 파일)
  - `urdf.zip`과 함께 세 가지를 전달
- 임시 폴더에서 문서 순서대로 따라 해 빌드·`check_urdf`까지 성공 (다른 PC에서는 미검증)
- 결과 재현성
  - URDF·TF·MoveIt 충돌 판정: 같은 파일이면 같은 결과
  - Isaac 물리 재생: GPU·드라이버에 따라 작은 수치 차이
  - Isaac Lab 학습 곡선: 같은 seed라도 완전히 같지 않음
  - apt 패키지: 설치 시점에 버전이 바뀔 수 있음

---

# Isaac Sim / Isaac Lab 태스크 구성

> 강의일 2026-10-21. KANT Lv.2 55 (모듈 8 이론). 목표: USD 자산과 센서로 로봇 태스크의 구조를 설명

## 역할 나누기
- Sim: 장면과 물리, 센서 출력을 계산
- Lab: 관측·행동·보상과 리셋을 구성
- 정책: 관측을 입력받아 행동을 출력
- 수업 원칙: Sim·Lab 버전 조합을 고정하고 Sim 버전·Lab 커밋·Python·GPU를 기록. 공식 예시 화면과 수업 실측을 구분

## 시뮬레이션으로 얻는 것과 한계
- 얻는 것: 같은 초기 조건에서 반복 실험, 충돌·실패 기록과 재생, 실제 센서로 얻기 어려운 상태 확인

| 항목 | 시뮬레이션에서 얻는 정보 | 실물에서 확인할 것 |
|---|---|---|
| 물리 | 관절·접촉의 계산 결과 | 질량·마찰·지연 차이 |
| 렌더 | RGB·깊이·분할 라벨 | 노출·가림·깊이 결손 |
| 반복 | 초기 상태를 다시 설정 | 실물의 재배치 오차 |
| 성공 판정 | 자동 조건 검사 | 실제 작업 요구와 일치 |

- 오른쪽 열이 그대로 도메인 랜덤화로 넓혀야 할 축이 됨 → 아래 [도메인 랜덤화](#도메인-랜덤화)

## 장면과 로봇 자산
- OpenUSD 기본 단위(Stage·Prim·Attribute)와 참조·레이어는 위 [7. USD란](#7-usd란)에 정리
- 장면 경로 예: `/World` 아래 `/Ground`, `/Robot`(`/base_link`, `/joint_1`), `/Target`, `/Camera` → 코드에서 prim을 이 경로로 찾음
- URDF를 가져온 뒤 확인: 길이·질량 단위 / 관절 축·한계·고정 베이스 / 충돌 형상·관절 드라이브 → 위 [6장](#6-2단계-일부-isaac-sim-usd-생성-usd-생성-성공-importer-오류-0)에서 Waffle 4WD에 적용
- 관절 드라이브와 액추에이터: 정책이 목표각을 내면 드라이브가 추종 → 강성·감쇠·출력 제한을 기록
  - Isaac Lab 3.0의 실행 흐름: 목표값 → ActuatorCollection → (Lab 액추에이터가 힘 계산 / 물리 엔진 내장 PD 드라이브 / Newton 액추에이터) → 물리 백엔드

## 센서
| 센서 | 알려 주는 것 |
|---|---|
| 카메라 RGB | 렌더링한 색 영상 |
| 카메라 Depth | 카메라 기준 거리 |
| 카메라 분할 | 객체 또는 종류의 라벨 |
| 접촉 센서 | 지정한 물체·링크의 접촉 여부와 힘 |

- 접촉 센서는 시뮬레이션 스텝과 갱신 주기를 확인 (정책 주기보다 느리면 놓치는 접촉이 생김)
- [261020](../261020/ROS2.md) 카메라 실습의 RGB·깊이가 이 출력

### 정책 관측과 진단 정보를 분리
- 정책에는 **실행 때 얻을 수 있는 관측**만
- 참값(시뮬레이션만 아는 정확한 위치 등)은 보상·평가·디버깅에만
- 추정값을 관측으로 쓸 거면 그 지연과 잡음도 시뮬레이션에 반영
- 실물에서 못 얻는 관측으로 학습하면 → 실제 로봇에 옮길 때 그 입력이 없어서 정책을 못 씀

## 태스크 명세
| 항목 | 설계 질문 | 회전축 예 |
|---|---|---|
| 장면 | 무엇을 배치하는가 | 회전축·목표·카메라 |
| 관측 | 무엇을 측정하는가 | 각도·속도·목표 오차 |
| 행동 | 무엇을 명령하는가 | 목표각 변화량 |
| 보상·판정 | 어떤 결과를 원하는가 | 추종·정착·제한 준수 |
| 리셋 | 언제 다시 시작하는가 | 시간 초과·실패·초기각 |

- [261020 Cartpole](../261020/ROS2.md#isaac-cartpole-과제-구성)이 이 다섯 항목으로 짜인 예
- 작성 순서: 장면과 관측 목록 작성 → 행동 단위와 종료 조건 확정 → 작은 환경으로 검사 후 학습

### Manager 방식과 Direct 방식
| | Manager 방식 | Direct 방식 |
|---|---|---|
| 구성 | 관측·행동·보상을 항목(term)으로 나누고 설정으로 조합 | 환경 클래스 하나에 계산 흐름을 직접 작성 |
| 장점 | 항목을 갈아 끼우기 쉬움, 항목별 단위·가중치 점검 | 사용자 정의 로직을 자유롭게 |
| 주의 | 항목별 단위·가중치 확인 | 리셋·버퍼·종료 처리를 직접 명시 |

- Cartpole의 `cartpole_manager_env_cfg.py`가 Manager 방식 (보상 항목 5개를 가중치로 조합)

### 병렬 환경과 주기
- 관측 shape: `(환경 수, 관측 차원)` → 예 (32, 12)는 환경 32개 × 관측 12개
- 환경마다 상태와 리셋을 따로 관리, 환경 수는 메모리를 보며 늘림

```python
obs = reset_all()              # 초기 관측
while running:                 # 실행 반복
    actions = policy(obs)      # 환경별 행동 (한 번에 배치로)
    obs = step_all(actions)    # 물리·센서 갱신
    reset_finished_envs()      # 끝난 환경만 리셋
```

| 설정 | 계산 예 | 해석 |
|---|---|---|
| physics dt | 0.005s | 물리 200Hz |
| decimation | 4 | 정책 한 번에 물리 4회 |
| policy dt | 0.005 × 4 = 0.02s | 정책 50Hz |
| episode time | 10s | 정책 스텝 약 500회 |

- [261020](../261020/ROS2.md) Cartpole은 1/120s × 2 → 정책 60Hz, 5s = 300스텝

### 학습 전에 통과해야 할 검사
| 검사 | 확인 방법 | 기록 |
|---|---|---|
| 중력·단위 | 단일 물체 낙하 | 높이와 시간 |
| 관절 | 한 축씩 목표 변화 | 축·부호·한계 |
| 센서 | 정지 장면 반복 | shape·유한값·시각 |
| 리셋 | 서로 다른 환경 종료 | 리셋된 환경 ID |
| 보상 | 성공·실패 수동 생성 | 항목별 값 |

- 중력·단위 검사는 261020의 상자 낙하 실습과 같은 것
- Waffle 4WD: 바퀴 축 +Y(양수 = 전진)는 URDF에서 확인, Isaac에서 한 축씩 움직이는 시험은 다음 단계

## 같은 로봇, 다른 태스크와 도구 선택
- 목표 도달: 위치 오차를 줄임 / 집기: 물체 이동과 유지 판정 / 접촉: 힘과 충돌 조건 추가
  - 로봇은 그대로, 목표(명령)와 보상·판정을 바꾸면 다른 태스크

| 도구 | 주로 볼 특징 | 고르는 질문 |
|---|---|---|
| Isaac Sim / Lab | 렌더·센서·병렬 학습 | 장면과 GPU 예산은? |
| MuJoCo | 동역학·제어 실험 | 접촉·모델 요구는? |
| Gazebo | ROS 시스템 통합 | 플러그인·통신 요구는? |

## 미니 퀴즈 (내 답)
1. USD Prim과 Reference의 차이는?
   - Prim은 경로로 찾는 장면의 요소 하나, Reference는 다른 파일(자산)의 내용을 prim에 가져다 붙이는 방법
2. 실물에서 얻지 못하는 관측을 쓰면 생기는 문제는?
   - 배포할 때 그 입력이 없어서 정책을 그대로 쓸 수 없음. 비슷한 추정값으로 바꾸면 학습 때와 분포가 달라 성능이 떨어짐
3. 관측 shape (32, 12)의 두 숫자는?
   - 병렬 환경 32개, 환경당 관측 차원 12
4. 물리 200Hz, decimation 4일 때 정책 주기는?
   - 0.005s × 4 = 0.02s → 50Hz
5. 같은 로봇으로 다른 태스크를 만드는 요소 두 가지는?
   - 목표(명령)와 보상·판정 (필요하면 리셋 조건도)

---

# 도메인 랜덤화

> 강의일 2026-10-21. KANT Lv.2 56 (모듈 8 이론). 목표: 시각·물리 랜덤화가 일반화에 기여하는 조건을 설명
> [261019](../261019/ROS2.md#sim-to-real)의 Sim to Real에서 이어짐

## 왜 필요한가
- 비슷한 환경에서만 학습하면 그 장면에만 맞춘 좁은 행동을 배움
  - 훈련 조건에서 성공해도 조명·배치·물리가 바뀌면 실패할 수 있음
  - 그래서 평가 조건은 훈련과 따로 준비
- 생각: 환경 파라미터를 **분포에서 뽑아** 여러 조건을 경험하며 학습. 실물 성능은 별도 시험으로 확인

$$
\max_\pi \; \mathbb{E}_{\xi \sim p(\xi)} \big[ J(\pi, \xi) \big]
$$

- $\xi$: 질량·마찰·지연 같은 환경 파라미터 / $p(\xi)$: 그 파라미터를 뽑는 분포 / $\pi$: 정책 / $J(\pi,\xi)$: 조건 $\xi$에서의 성능
- 한 조건이 아니라 **여러 환경의 평균 성능**을 높이는 것이 목표
- 실물이 $p(\xi)$ 안에 들어 있어야 효과가 있음 → 분포 밖(OOD) 조건이면 보장 못 함

## 랜덤화하는 네 계열
| 계열 | 조건 | 단위·기록 |
|---|---|---|
| 시각 | 색, 조명, 카메라 | RGB, 세기, 포즈 |
| 물리 | 질량, 마찰, 감쇠 | kg, 계수, N·m·s/rad |
| 시스템 | 행동 지연, 샘플 주기 | ms, Hz |
| 초기 조건 | 위치, 목표, 초기각 | m, rad |

### 시각
- 물체·배경 재질, 조명 세기·방향을 바꿈
- 바꾼 뒤에도 목표가 계속 관측되는지 확인 (가려지거나 안 보이면 학습할 수 없는 조건)
- 카메라: 작은 위치·각도 오차를 반영, 내부 파라미터와 영상 크기 기록, 카메라 보정 범위 안에서 시작
  - [261021 Waffle](#카메라가-아래를-보는-것처럼-보였던-이유)의 RealSense 각도 차이(35.3° vs 약 42°)가 이런 오차의 예

### 물리
- 질량과 관성
  - 같은 명령에도 질량·관성이 다르면 가속도가 달라짐 ($F = ma$, $\tau = I\alpha$)
  - 그래서 질량을 바꿀 때 관성도 같이 바꿀지 명시. 형상과 물리적으로 맞는 범위로
- 마찰과 감쇠
  - 마찰: 접촉면과 움직임의 관계 / 감쇠: 속도에 비례하는 저항
  - 서로 다른 파라미터라 따로 기록
  - 바로 랜덤화하지 말고 **먼저 측정**한 뒤 범위를 정함
- 강의 그래프에서 본 것 (공식 문서 예시)
  - 관절 마찰을 0 → 1N·m로 키우면 진동하던 관절 속도가 점점 빨리 멈춤
  - 감쇠 0.5 → 100N·m·s/rad: 작으면 크게 출렁이고, 크면 출렁임 없이 아주 천천히 목표에 도달
  - 강성 10 → 1000N·m/rad: 작으면 목표(1.5rad)에 못 미치고 멈추고, 크면 빠르지만 순간적으로 넘침

### 시스템 (행동 지연과 샘플 주기)
- 행동 지연: 지금 계산한 명령이 늦게 적용됨 → 이것도 랜덤화
- **왕복 지연과 적용 지연을 구분**
  - 왕복: 센서 → 계산 → 명령 → 다시 센서에 보이기까지
  - 적용: 명령을 낸 뒤 모터에 실제로 적용되기까지
- 지연 분포와 제어 주기를 함께 기록 (지연을 "스텝"으로 적으면 주기 없이는 ms로 못 바꿈)
- 샘플 주기도 범위로: 예를 들어 공칭 144Hz면 80~144Hz 범위에서 랜덤화
  - 실제 시스템은 부하가 걸리면 공칭보다 느려지는 쪽으로 흔들리니 아래쪽으로 넓힌 범위

### 언제 값을 바꾸나
| 시점 | 적합한 예 | 주의점 |
|---|---|---|
| 시작 시 | 자산·상수 설정 | 실행 중 변경을 지원하는지 확인 |
| 에피소드 리셋 | 질량·마찰·카메라 포즈 | 환경 ID별로 적용 |
| 매 스텝 | 센서 잡음 | 백색 잡음 가정이 맞는지 확인 |
| 일정 간격 | 외력·배경 변화 | 빈도와 지속 시간 기록 |

## 설정표 작성
- 각 변수를 **공칭값과 허용 오차**로 표현

| 변수 | 공칭값 | 범위 예 |
|---|---|---|
| 물체 질량 | 0.20kg | 0.18~0.22kg |
| 마찰 계수 | 0.6 | 0.5~0.7 |
| 행동 지연 | 20ms | 0~40ms |
| 관측 잡음 표준편차 | 0rad | 0.005rad |

- 분포의 중심과 폭
  - 중심: 측정한 공칭값
  - 폭: 반복 측정의 흩어짐 + 모델 잔차(시뮬레이션과 실측의 차이)
  - 단위, 상한·하한, 그 근거를 같이 남김

## 범위를 바꿨을 때의 가설
| 설정 | 가능한 문제 | 확인 지표 |
|---|---|---|
| 너무 좁음 | 평가 조건을 충분히 경험하지 못함 | 조건별 성공률 |
| 적절한 범위 | 변동에 강한 전략을 학습 가능 | 반복 평가와 분산 |
| 너무 넓음 | 불가능한 과제가 섞이고 학습 난도 증가 | 실패 사유, 학습 안정성 |

## 태스크가 가능한 범위
- 랜덤화해도 과제가 풀 수 있는 조건이어야 함
  - 로봇의 도달 범위 안에 목표 배치
  - 물체가 관측 가능한지 확인
  - 랜덤화한 뒤 충돌 검사와 초기 침투(시작부터 물체끼리 겹침) 검사
- 초기 조건: 배치·초기각·목표 위치를 따로 랜덤화, 고정 시드로 같은 조건 재현, 평가 지형은 학습과 분리
- 내 계획: 물체 위치는 Isaac ROS의 CenterPose(물체 자세 추정)를 이용할 예정
  - 실물에서는 이 추정값이 관측이 되니, 시뮬레이션 관측에도 그 지연·잡음을 넣어야 함 (55의 "관측과 진단 정보 분리")

## 랜덤화 효과를 확인하는 실험
| 조건 | 변경점 | 고정할 항목 |
|---|---|---|
| 기준 | 랜덤화 없음 | 정책·학습 예산·평가 |
| 전체 DR | 선택한 축 모두 | 같은 평가 조건 |
| 한 축 제거 | 지연 등 한 축만 OFF | 다른 축과 학습 예산 |
| 범위 비교 | 좁게, 넓게 | 평가 프로토콜 |

- 절제 실험(ablation): 한 축을 뺀 뒤 성능 변화를 봄
  - 여러 시드에서의 흔들림도 같이 확인 (시드 하나의 차이는 우연일 수 있음)
  - 축 사이 상호작용(예: 질량과 마찰이 함께 바뀔 때)은 따로 검사

## 커리큘럼과 ADR
- 커리큘럼: 쉬운 범위에서 학습을 시작
- ADR(Automatic Domain Randomization): 경계 조건에서의 성능을 보고 범위를 자동으로 넓힘
  - 확대 속도와 되돌림(성능이 떨어지면 범위를 줄이는) 규칙을 기록
- 처음부터 넓은 범위면 "너무 넓음" 문제 → 점점 넓혀서 피함

## 훈련과 평가의 구분
| 데이터 | 사용 목적 | 변경 규칙 |
|---|---|---|
| 훈련 분포 | 정책 학습 | 설계 실험에서 수정 가능 |
| 검증 조건 | 범위·모델 선택 | 선택에 썼다고 기록 |
| 최종 시험 | 일반화 보고 | 튜닝 후 고정해서 실행 |
| 실물 시험 | 현장 검증 | 장비·안전 기준 적용 |

## 측정과 랜덤화의 연결
- 실측으로 분포의 중심과 불확실성을 파악
- 학습 후 약한 조건(weak point)을 찾음
- 보정·범위 수정·재평가를 반복
- 수업 산출물: 랜덤화 설정표와 범위 근거 / 조건별 관측 화면과 파라미터 로그 / 기준 정책과 DR 정책 비교표

## 핵심 용어
| 용어 | 뜻 |
|---|---|
| DR | 환경 조건을 분포로 바꿔 학습 |
| 공칭값 | 기준으로 삼는 파라미터 |
| OOD | 학습 분포 밖 조건 (out-of-distribution) |
| 절제 실험 | 한 구성 요소를 빼고 비교 |
| ADR | 성능에 따라 범위를 조절 |

## 미니 퀴즈 (내 답)
1. DR이 실물 성공을 보장하지 않는 이유는?
   - 실물이 학습 분포 안에 있다는 보장이 없음 (OOD). 랜덤화하지 않은 요인(모델링 안 한 효과)도 남음
2. 질량과 센서 잡음의 변경 시점은 어떻게 다른가?
   - 질량은 에피소드 리셋 때 한 번(한 시도 안에서는 일정), 센서 잡음은 매 스텝
3. 지연 2스텝을 ms로 바꾸려면 무엇이 필요한가?
   - 그 스텝의 주기 (물리 스텝인지 정책 스텝인지까지). 예: 정책 50Hz면 2스텝 = 40ms, 물리 200Hz면 10ms
4. 범위가 너무 넓을 때 확인할 것은?
   - 실패 사유(불가능한 조건이 섞였는지)와 학습 안정성
5. 한 축 제거 실험에서 고정해야 할 항목은?
   - 나머지 축의 범위, 학습 예산(스텝 수), 평가 조건과 시드
