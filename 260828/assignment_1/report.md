# 1. 배달 로봇의 연산 분담과 실시간성 설계

## 전제 조건 : 배달 로봇에 다음이 실려 있다고 가정합니다 — 2D 라이다(10Hz), RGB 카메라(30fps·1080p), IMU(200Hz), 바퀴 엔코더(1kHz), 모터 드라이버, LTE 모듈.

### 1. 이 로봇이 하는 작업 여섯 가지(모터 속도 제어, 장애물 감지, 보행자 인식, 지도 기반 경로 계획, 배달 완료 사진 업로드, 운행 로그 집계)를 임베디드 / Edge AI / 클라우드 중 어디서 처리할지 표로 배치하고, 지연 예산과 데이터 전송량을 근거로 각각 이유를 쓰세요(1강).

|작업|위치|지연 예산|데이터량|근거|
|---|---|-------|------|---|
|모터 속도 제어|임베디드|≤ 1 ms|엔코더 8 KB/s + 명령 수 B/ms|LTE통신과 엣지의 주기가 지연 예산보다 크기에 불가능하고 데이터는 작지만 짧은 주기가 필요하므로 MCU의 타이머 인터럽트에서 PID 제어|
|장애물 감지|임베디드+Edge AI|≤ 100 ms|라이다 28.8 KB/s|360점 스캔의 계산은 임베디드와 엣지 모두 가능하므로 둘다 사용하여 비상 정지와 같은 급작스러운 상황이나 최종 판정은 mcu가 바로 전달하여 엣지가 죽어도 작동하도록 하며, 지도의 경로 계획과의 결합을 위해 기본적인 연산은 엣지가 진행|
|보행자 인식|Edge AI|≤ 100 ms|186.6 MB/s|초당 요구 데이터량이 LTE의 속도보다 많기에 클라우드에서는 불가능하기에 엣지 AI로 계산 후 결과만 판단으로 넘김|
|지도 기반 경로 계획|Edge AI+클라우드|1 ~ 5 s|요청 수백 B, 응답 waypoint 수 KB|지도는 수 GB이고 도로 통제·다른 로봇 위치와 함께 갱신되므로 클라우드 서버 이용, 응답이 몇 초 늦어도 로봇은 이전 경로로 계속 주행할 수 있어 지연에 둔감. 국소 회피는 엣지에서 진행|
|배달 완료 사진 업로드|클라우드|초 ~ 분|JPEG 1 장 ≈ 0.5~2 MB, 배달 1 건당 1 회|실시간성이 전혀 없기에 클라우드 서버 이용|
|운행 로그 집계|클라우드|분 ~ 시간|로그 수십 KB/s 를 로컬 축적, 압축 후 업로드| 마감이 없기에 로컬 저장 후 Wi-Fi/유휴 시간 배치 업로드|

### 2. 카메라 원시 영상을 클라우드로 계속 보내면 초당 몇 MB 인지 계산하고, LTE 대역폭과 비교해 그 설계가 왜 성립하지 않는지 수치로 보이세요.

- 카메라 원시 영상을 클라우드로 계속 보내면 1920 × 1080 × 3 B = 6,220,800 B ≈ 6.22 MB, 30 fps (33 ms)이므로 186.6 MB/s ≈ 1,493 Mbps = 1.49 Gbps
  - RGB 카메라는 보통 30 fps인데 이론상 LTE 링크의 최대치인 50Mbps일때 1 fps 이므로 프레임은 버퍼에 쌓이고 지연도 쌓이게 됨. 1시간 당 3600 s이므로 186.6 MB/s X 3600 s = 671760 MB/시간 = 671.76 GB/시간으로 과도한 요금이 부여됨

- 모터 제어 : (8 B×1,000 Hz (회/초)=8,000 B/s)  
- 라이다 : 2,880 B X 10 Hz (초당 스캔 횟수) = 28,800 B/s = 28.8 KB/s

### 3. 같은 작업들을 인지 → 판단 → 제어 계층에 매핑하고, 계층별 갱신 주기를 적어 멀티레이트 데이터 흐름을 그림이나 표로 정리하세요(2강).

|작업|계층|갱신 주기|실행위치|입력|→|출력|
|---|---|-------|------|---|-|----|
|엔코더 읽기|인지|1 kHz|임베디드|펄스 카운트|→|바퀴 각속도|
|IMU 읽기|인지|200 Hz|임베디드|가속도·각속도|→|자세·오도메트리|
|모터 속도 제어|제어|1 kHz|임베디드|엔코더|→|PWM 듀티|
|장애물 감지|인지|10 Hz|임베디드+Edge|라이다 스캔|→|장애물 점군·최근접 거리|
|보행자 인식|인지|30 Hz|Edge|카메라 프레임|→|보행자 박스·거리|
|지도 기반 경로 계획|판단|0.1 ~ 1 Hz|클라우드|출발·목적지·지도|→|waypoint 열|
|지도 기반 경로 계획|판단|10 Hz|Edge|waypoint + 장애물 + 보행자|→|목표 선속도·각속도|
|배달 완료 사진 업로드|비실시간|배달 1 건당 1 회, 이벤트성|클라우드|JPEG|→|저장·알림|
|운행 로그 집계|비실시간|배치 1/분~1/시간|클라우드|로그 파일|→|통계·대시보드|

### 4. 여섯 작업을 Hard / Firm / Soft 실시간으로 분류하고, Hard 로 분류한 작업이 마감을 놓치면 어떤 물리적 결과가 생기는지 한 줄씩 쓰세요.

|작업|등급|마감|마감을 놓치면|근거|
|---|---|---|----------|----|
|엔코더 읽기|Hard|1 ms|바퀴가 과도하게 회전(Over-spin)하거나 갑자기 역회전하여 차량이 급발진·탈선|딜레이 시 치명적, 엔코더의 값을 늦게 읽으면 모터 속도 제어에 영향을 미치기 때문|
|IMU 읽기|Hard|1 ms|무게 중심의 변화를 제때 감지하지 못해 원심력을 이기지 못하고 전복|기울어짐이나 미끄러짐에 대한 감지 마감 시간을 놓치면, 물리력이 차량의 한계를 넘어서기 전에 제어 명령을 내릴 수 없음|
|모터 속도 제어|Hard|1 ms|바퀴 속도가 폭주하거나 좌우 바퀴 속도가 어긋나 노선을 이탈|딜레이 시 치명적, 늦은 결과는 가치가 0 이 아니라 음수|
|장애물 감지|Hard|100 ms|스캔 하나 당 로봇이 0.15 m 를 더 진행, 두 번 놓치면 제동 거리 여유가 사라져 충돌|충돌 확률 직접 증가|
|보행자 인식|Firm|100 ms|이미 이동한 뒤라 폐기하고 다음 프레임 사용, 라이다 비상정지가 안전을 보장|마감 초과 시 가치가 0이지만, 놓쳐도 시스템 실패는 아님|
|지도 기반 경로 계획|soft|5 s|응답이 늦으면 로봇은 이전 경로로 계속 주행하거나 잠시 대기, 비상정지가 안전을 보장|가치가 점진적으로 감소할 뿐 0 이 아님|
|배달 완료 사진 업로드|soft|N 분|실시간성 없음, 고객 알림이 늦어질 뿐, 재전송 가능|마감 자체가 느슨하고 재시도 가능|
|운행 로그 집계|soft|N 시간|실시간성 없음, 대시보드가 늦게 갱신|배치 작업. 마감 없음에 가까움|

### 5. 주기·지연·지터를 이 로봇의 예로 각각 한 문장씩 구분해 설명하세요.

- 주기 : 작업이 얼마나 자주 반복되는가, 모터 제어 시 엔코더를 1 kHz의 주기로 읽고 라이다를 10 Hz 마다 읽으며 pwm 제어
- 지연 : 입력이 들어와서 출력이 나올 때까지 걸리는 시간, 현재 차체의 상황이 imu를 통해, 모터 값이 엔코더를 통해 들어오고 그 값들을 이용해 목적지로의 방향과 모터 속도를 결정하는데 걸리는 시간이 지연된 시간
- 지터 : 주기와 지연의 불균일성, 매번 주기와 지연이 동일하면 지터는 0, 지터가 PID 계산을 오염시키므로 낮은 지터가 중요


# 2. 원격 접속(SSH)과 센서 장치 경로 고정

## 1. 고른 접속 대상: localhost / 가상머신 중 ___ — 무비밀번호 접속 로그와 who·echo $SSH_CONNECTION 출력

- 가상머신
```shell
pa4@pa4-Legion-Pro-5-16IAX10:~$ who
pa4      tty2         2026-08-28 17:47 (tty2)
pa4      pts/5        2026-08-28 15:57 (10.2.12.138)
pa4@pa4-Legion-Pro-5-16IAX10:~$ echo $SSH_CONNECTION
10.2.12.138 37868 10.2.12.138 22
```

## 2. 개인키·공개키 중 서버에 등록하는 것: ___ — 안전한 이유

- 공개키 : 암호화에서 개인키와 공개키를 함꼐 사용하는데 개인키가 private한 키이므로

## 3. 원격 단일 명령 실행과 scp 전송 출력

```shell
pa4@pa4-Legion-Pro-5-16IAX10:~$ sudo scp test260828 pa4@10.2.12.138:/home/pa4/temp
pa4@10.2.12.138's password: 
test260828                                                                                                                                                                100%    7    10.0KB/s   00:00   
```

## 4. 두 장치를 구분한 속성: 라이다 ___ / IMU ___

```shell
pa4@pa4-Legion-Pro-5-16IAX10:~/fake_sensors$ udevadm info --attribute-walk /dev/loop21

Udevadm info starts with the device specified by the devpath and then
walks up the chain of parent devices. It prints for every device
found, all possible attributes in the udev rules key format.
A rule to match, can be composed by the attributes of the device
and the attributes from one single parent device.

  looking at device '/devices/virtual/block/loop21':
    KERNEL=="loop21"

```
- loop의 backing_file이 생성되지 않아서 kernel값을 고유값으로 지정했음.

## 5. 작성한 udev 규칙 2개 + 규칙 키 설명표

[99-robot-sensor.rules](99-robot-sensor.rules)
```text
SUBSYSTEM=="block", KERNEL=="loop*", ATTR{loop/backing_file}=="*lidar.img*", SYMLINK+="robot_lidar", MODE="0660", GROUP="dialout"
SUBSYSTEM=="block", KERNEL=="loop*", ATTR{loop/backing_file}=="*imu.img*", SYMLINK+="robot_imu", MODE="0660", GROUP="dialout"
```

## 6. 순서를 바꿔 재연결한 뒤 ls -l /dev/robot_* 결과

```shell
pa4@pa4-Legion-Pro-5-16IAX10:/dev$ ls -al | grep robot
lrwxrwxrwx   1 root root             6 Aug 28 16:40 robot_imu -> loop21
lrwxrwxrwx   1 root root             5 Aug 28 16:40 robot_lidar -> loop6
```

## 7. 실제 USB 센서용 규칙 초안과 구분 근거

- 실제 센서는 다음의 값들을 사용한다.  

```text
ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60"
```

# 3. 팀 저장소 협업 — 브랜치·충돌 해결·PR 리뷰

## 1. 저장소 URL: ___ / PR URL: ___

- 저장소 URL : https://github.com/SpartaPA/OnChangbum_physicalai_lv1_assignments

- PR URL : https://github.com/SpartaPA/OnChangbum_physicalai_lv1_assignments/pulls?q=is%3Apr+is%3Aclosed

## 2. PR 리뷰 코멘트와 반영 커밋 (캡처 또는 링크)

![PR_Review](PR_Review.png)

- PR URL : https://github.com/SpartaPA/OnChangbum_physicalai_lv1_assignments/pulls?q=is%3Apr+is%3Aclosed

## 3. 충돌이 난 파일과 줄: ___ — 충돌 표식의 뜻과 해결 방법

```text
 <<<<<<< HEAD
 배달 로봇 사양(센서 목록·주기): 2D 라이다(10Hz), RGB 카메라(30fps·1080p), IMU(200Hz), 바퀴 엔코더(1kHz), 모터 드라이버, 5G 모듈.
=======
 배달 로봇 사양(센서 목록·주기): 2D 라이다(10Hz), RGB 카메라(30fps·1080p), IMU(200Hz), 바퀴 엔코더(1kHz), 모터 드라이버, 4G 모듈.
>>>>>>> main
```
```text
<<<<< : 내 입장의 충돌 내용

===== : 구분선

>>>>> : 상대 입장의 충돌 내용
```

## 4. merge 방식 이력 그래프 / rebase 방식 이력 그래프 (두 출력 비교)

- merge graph
```text
pa4@pa4-Legion-Pro-5-16IAX10:~/git/OnChangbum_physicalai_lv1_assignments$ git log --oneline --decorate --graph
*   c162f23 (HEAD -> main, origin/main, origin/HEAD) Merge pull request #4 from SpartaPA/branch-b
|\  
| *   7bc58c8 (origin/branch-b, branch-b) merge_ex
| |\  
| |/  
|/|   
* |   1b56600 Merge pull request #3 from SpartaPA/branch-a
|\ \
| * | 95f0975 (origin/branch-a, branch-a) README4G
* | |   7ef9245 Merge pull request #2 from SpartaPA/feature/udev-rules
|\ \ \  
| |/ /  
|/| |   
| * | 523e429 (origin/feature/udev-rules, feature/udev-rules) assignment_2
|/ /  
| * 11ebdb0 README5G
|/  
*   fcbd9f4 Merge pull request #1 from SpartaPA/feature/compute-layout
|\  
```
- rebase graph(commit 이후 rebase 이전)
```text
pa4@pa4-Legion-Pro-5-16IAX10:~/git/OnChangbum_physicalai_lv1_assignments$ git log --oneline --decorate --graph --all
* e4ffa0b (HEAD -> main) test.txt
| * a253f89 (rebase_test) rebase_test
|/  
*   c162f23 (origin/main, origin/HEAD) Merge pull request #4 from SpartaPA/branch-b
|\  
| *   7bc58c8 (origin/branch-b, branch-b) merge_ex
| |\  
| |/  
|/|   
* |   1b56600 Merge pull request #3 from SpartaPA/branch-a
|\ \  
| * | 95f0975 (origin/branch-a, branch-a) README4G
* | |   7ef9245 Merge pull request #2 from SpartaPA/feature/udev-rules
|\ \ \  
| |/ /  
|/| |   
| * | 523e429 (origin/feature/udev-rules, feature/udev-rules) assignment_2
|/ /  
| * 11ebdb0 README5G
```

- rebase graph(rebase 이후)
```text
pa4@pa4-Legion-Pro-5-16IAX10:~/git/OnChangbum_physicalai_lv1_assignments$ git log --oneline --decorate --graph --all
* e91264f (HEAD -> rebase_test) rebase_test
* e4ffa0b (main) test.txt
*   c162f23 (origin/main, origin/HEAD) Merge pull request #4 from SpartaPA/branch-b
|\  
| *   7bc58c8 (origin/branch-b, branch-b) merge_ex
| |\  
| |/  
|/|   
* |   1b56600 Merge pull request #3 from SpartaPA/branch-a
|\ \  
| * | 95f0975 (origin/branch-a, branch-a) README4G
* | |   7ef9245 Merge pull request #2 from SpartaPA/feature/udev-rules
|\ \ \  
| |/ /  
|/| |   
| * | 523e429 (origin/feature/udev-rules, feature/udev-rules) assignment_2
|/ /  
| * 11ebdb0 README5G
|/  
```

## 5. 언제 merge 를, 언제 rebase 를 쓸지 — 3줄 이내

- git merge: 여러 명이 공유하는 메인 브랜치를 안전하게 합치고, 개발 기록을 있는 그대로 남길 때 사용
- git rebase: 개인 작업 중인 로컬 브랜치의 커밋 기록을 깔끔하고 일렬로 정렬해 가독성을 높일 때 사용
  - merge는 이력이 남으므로 이력을 깨뜨리지 않게 만들기 위해서는 merge를 쓰고, 이력에 상관안해도 될때엔 rebase를 사용