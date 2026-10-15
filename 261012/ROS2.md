## 카메라 연결
```shell
tmux attach -t pi 
export DISPLAY=$(tmux show-environment DISPLAY | sed -n 's/^DISPLAY=//p'); echo $DISPLAY
cd ~/git/Lv2_Monglian_Assignment/lv2_module5 && source ros2_ws/install/setup.bash && python3 assignment/main.py
```

# 19·21강 과제

## HSV Mask와 검출 후보 필터

### 처리 흐름
- Raw Image(rgb8) → HSV 변환 → `inRange` → open·close → `findContours` → `min_area` 필터 → 후보 선택 → `/target` 발행
- Mask: HSV 범위 안 255(전경), 밖 0(배경)
- `inRange`는 H·S·V **세 조건 모두** 만족해야 255

### 실험 1: H 하한 102 → 96
- 빨대: S·V는 범위 안, H(98~100)만 하한 밖 → H 하한을 내리니 Mask에 들어옴
- 원기둥 H 104~107 → 두 값 모두 그대로
- 후보 1 → 3 (빨대가 컵 테두리에서 두 조각), `/target`은 원기둥 유지
- 색 범위를 넓히면 **오검출** 쪽으로 실패

### 실험 2: min_area 100 → 3000
- Mask는 픽셀 단위로 동일
- 원기둥 컨투어(2806.5 px²) < 3000 → 후보 탈락 → `/target` (0, 0, 0)
- 면적 기준이 너무 크면 **미검출** 쪽으로 실패
- Mask 생성과 후보 필터는 서로 다른 단계 → 고치는 위치도 다름
  - 비슷한 색 물체: HSV 범위
  - 작은 잡음: `min_area`

### 픽셀 면적의 한계
- 같은 물체도 멀어지면 px² 감소
- 깊이로 실제 면적 근사 가능
  - $A_{cm^2} = A_{px^2} \times (Z \div f_x) \times (Z \div f_y) \times 10^4$
- `min_area`는 점 잡음 제거용, 물체 판단은 실제 면적으로

## 같은 입력으로 비교하기

- 실시간 카메라: A·B가 서로 다른 프레임 → 잡음·노출 차이가 섞임
- rosbag 녹화 후 한 프레임만 재생
  - `ros2 bag play --start-paused`
  - `/rosbag2_player/seek` → `/rosbag2_player/play_next`
- Raw·Mask·검출 결과의 header stamp가 같으면 같은 프레임
- 노드가 설정을 시작 시 한 번만 읽음 → 값 바꿀 때마다 재시작

## 토픽 수신 증거

- 토픽 목록에 이름만 있는 것은 수신 증거 X
- 이미지: `rqt_image_view`, 수치: `ros2 topic echo`
- 한 장만 보낼 때는 뷰어가 **먼저** 구독 중이어야 함 (VOLATILE이라 늦게 붙으면 못 받음)
- OpenCV 로컬 창은 토픽 수신 증거 X

## BEST_EFFORT로 영상이 안 들어온 이유

- 640×480 rgb8 한 장 = 921,600 B → UDP 조각으로 나뉘어 전송
- PC `net.core.rmem_max` 212,992 B → 수신 버퍼가 넘쳐 조각 손실
  - RELIABLE: 빠진 조각 재전송 → 수신됨 (약 14 Hz)
  - BEST_EFFORT: 재전송 없음 → 그 장 전체 버림 (0 Hz)
- Pi는 4,194,304 → 같은 값으로 올리니 30 Hz
  - `/etc/sysctl.d/`에 설정 파일로 남겨 재부팅 후에도 유지
