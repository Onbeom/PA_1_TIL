# ROS2 Lyrical
## 권장 설치 순서
- 장비의 OS·GPU·디스크 여유 공간을 확인한다.
- Windows에 지원 드라이버와 Isaac Sim을 설치하고 로컬 headless 시작을 확인한다.
- Ubuntu에 ROS 2 Lyrical과 개발 도구를 설치하고 로컬 메시지 송수신을 확인한다.
- 아래의 Python 관측·영상 처리 환경을 설치한다.
- SSH 공개키 인증과 서버 키 확인을 구성한다.
- 원격 실행과 ROS 메시지 연결을 분리하여 검증한다.
- 기본 경로가 동작한 후 GPU 확장 도구를 설치한다.

## Python video tool
```shell
sudo apt update
sudo apt install -y git curl build-essential python3-venv python3-pip \
  ffmpeg openssh-client

mkdir -p "$HOME/pa-course"
cd "$HOME/pa-course"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy opencv-python-headless imageio imageio-ffmpeg
python -m pip freeze > requirements.lock.txt

source "$HOME/pa-course/.venv/bin/activate"
python - <<'PY'
import cv2
import numpy as np
import imageio.v2 as imageio
import imageio_ffmpeg
import hashlib, json
from pathlib import Path

out = Path.home() / 'pa-course' / 'install-check'
out.mkdir(parents=True, exist_ok=True)
frame = np.zeros((240, 320, 3), dtype=np.uint8)
frame[80:160, 100:220] = (0, 0, 255)  # RGB의 파랑
video = out / 'video_check.mp4'
with imageio.get_writer(str(video), fps=10, codec='libx264') as writer:
    for _ in range(10):
        writer.append_data(frame)
assert video.stat().st_size > 0
print('OpenCV:', cv2.__version__)
print('NumPy:', np.__version__)
print('FFmpeg:', imageio_ffmpeg.get_ffmpeg_exe())
print('MP4:', video)
print('SHA-256:', hashlib.sha256(video.read_bytes()).hexdigest())
print('PYTHON_VIDEO_INSTALL_OK')
PY
ffmpeg -version
```
## GPU Extension tool - PyTorch
```shell
python3 -m venv "$HOME/pa-course/.venv-gpu"
source "$HOME/pa-course/.venv-gpu/bin/activate"
python -m pip install --upgrade pip
# 이 위치에서 공식 선택기가 제시한 PyTorch 설치 명령을 실행한다.
# 설치 후 확인:
python -c "import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available(), 'CUDA unavailable'; print(torch.cuda.get_device_name(0))"
python -m pip freeze > "$HOME/pa-course/requirements-gpu.lock.txt"
```

## Lyrical

### OS, local, basic tool check
```shell
. /etc/os-release
printf 'OS=%s codename=%s arch=%s\n' "$PRETTY_NAME" "$VERSION_CODENAME" "$(dpkg --print-architecture)"
if [ "$VERSION_CODENAME" != noble ]; then
  echo '이 절차는 Ubuntu 24.04 Noble용이다.'
  exit 1
fi
sudo apt update
sudo apt install -y locales curl gnupg ca-certificates \
  software-properties-common git build-essential python3-venv
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository -y universe
locale
```

### Environment
```shell
vi ~/.bashrc
source ~/.bashrc
```
- 자동 source 설정을 확인

### Isaac ROS (NVIDIA)
```shell
nvidia-smi

mkdir -p  ~/workspaces/isaac_ros-dev/src
echo 'export ISAAC_ROS_WS="${ISAAC_ROS_WS:-${HOME}/workspaces/isaac_ros-dev/}"' >> ~/.bashrc
source ~/.bashrc

locale  # check for UTF-8

sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

locale  # verify settings

sudo apt update && sudo apt install curl gnupg
sudo apt install software-properties-common
sudo add-apt-repository universe

k="/usr/share/keyrings/nvidia-isaac-ros.gpg"
curl -fsSL https://isaac.download.nvidia.com/isaac-ros/repos.key | sudo gpg --dearmor \
    | sudo tee -a $k > /dev/null
f="/etc/apt/sources.list.d/nvidia-isaac-ros.list"
sudo touch $f
s="deb [signed-by=$k] https://isaac.download.nvidia.com/isaac-ros/release-5.0 noble main"
grep -qxF "$s" $f || echo "$s" | sudo tee -a $f

sudo apt-get update
```

### Isaac ROS BUildfarm(in Ubuntu 24.04)
```shell
k="/usr/share/keyrings/nvidia-isaac-ros.gpg"
f="/etc/apt/sources.list.d/nvidia-isaac-ros-buildfarm.list"
sudo touch $f
s="deb [arch=$(dpkg --print-architecture) signed-by=$k] https://isaac.download.nvidia.com/isaac-ros/ubuntu/main noble main"
grep -qxF "$s" $f || echo "$s" | sudo tee -a $f

sudo apt-get update
sudo apt-get install -y curl

ROS_APT_SOURCE_VERSION="1.2.0"
curl -fsSL -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

sudo apt-get update
apt-cache policy ros-lyrical-ros-base

sudo apt-get install -y ros-lyrical-ros-base

sudo apt-get install -y python3-colcon-common-extensions python3-rosdep

sudo apt-get install -y ros-lyrical-ros-base ros-lyrical-rviz2 ros-lyrical-rqt ros-lyrical-demo-nodes-cpp
```

### Isaac ROS CLI
```shell
sudo apt-get install isaac-ros-cli

sudo usermod -aG docker $USER
newgrp docker

sudo systemctl daemon-reload && sudo systemctl restart docker

docker info | grep -E "Runtimes|Default Runtime"
docker run --rm hello-world
docker run --rm --gpus all ubuntu:24.04 bash -lc 'echo "NVIDIA runtime OK"'

sudo isaac-ros init docker
```

### launch
```shell
source /opt/ros/lyrical/setup.bash
```

# OpenCV

## BGR, HSV

- 3원색 : CMYK
  - OpenCR에서 : CMYK는 RGB로 나타내고 관례상 BGR순서로 표시.
- HSV : 색상, 채도, 명도
  - 범위 :
    - H : 0 ° ~ 360 °
    - S : 0 % ~ 100 %
    - V : 0 % ~ 100 %
    - OpenCR에서 360의 색상환을 8bit로 변환하며 0 ~ 359의 범위가 0 ~ 179가 됨
      - EX. OpenCV의 H는 0~179로 감기는 원형 척도라, 빨강(0° 근처)은 H∈[0,10] 과 H∈[170,179] 두 범위의 OR로 잡아야 합니다
- Contour : 객체 추출 후 윤곽선 찾기

- 파이프라인 : 이미지 읽기 -> HSV 변환 -> 색 추출 후 마스크 생성 -> 노이즈 제거 -> 윤곽선 검출

## OpenCV HSV Contour 검출 코드

```python
import cv2
import numpy as np

# 1. 이미지 로드
img = cv2.imread('object.jpg')

# 2. BGR에서 HSV 색상 공간으로 변환
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 3. 검출하고 싶은 색상의 HSV 범위 설정 (예: 노란색 대역)
# ※ OpenCV의 Hue(색상) 범위는 0 ~ 179입니다.
lower_color = np.array([20, 100, 100])
upper_color = np.array([30, 255, 255])

# 4. 설정한 범위에 해당하는 픽셀만 흰색(255), 나머지는 검은색(0)인 이진 마스크 생성
mask = cv2.inRange(hsv, lower_color, upper_color)

# [선택] 모폴로지 연산으로 마스크 내부 노이즈 및 구멍 제거
kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

# 5. 이진 마스크 이미지에서 윤곽선(Contour) 찾기
# cv2.RETR_EXTERNAL: 가장 외각의 윤곽선만 검출
# cv2.CHAIN_APPROX_SIMPLE: 윤곽선 좌표를 압축하여 메모리 절약
contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 6. 원본 이미지 위에 검출된 윤곽선 그리기 (-1은 모든 윤곽선, 초록색(0,255,0), 두께 2)
cv2.drawContours(img, contours, -1, (0, 255, 0), 2)

# 7. 결과 확인
cv2.imshow('Mask', mask)
cv2.imshow('Result', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

- Numpy array : [v, u]  <--- Origin(RGB)
- OpenCR array : [u, v] <--- Converted(BGR)
- "함수 인자는 상식적인 (가로, 세로), 행렬 배열은 컴퓨터 기준의 [세로, 가로(행, 열)]"

## Gaussian-Median Filter

- crop : 사용하는 부분만 남기고 나머지는 버림 
- mask : 쓸 부분을 박스처리한 후 사용하지 않을 부분을 0처리하고, 박스 내에서 다시 색상을 가진 객체 검출

- Gaussian Filter : 선형 필터, 마스크 중심에서 가까운 픽셀에는 큰 가중치, 먼 픽셀에는 작은 가중치를 주어 가중 평균을 계산
  - 경계선(Edge)이나 세부 디테일이 흐려지거나 뭉개질 수 있음
- Median Filter : 비선형 필터, 마스크 내의 픽셀 값들을 크기순으로 정렬한 뒤 중앙값을 선택해 해당 픽셀을 대체
  - 텍스처가 적은 균일한 영역에서는 디테일이 손상되거나 세부 요소의 손실 가능
- Convolution(합성곱) Filter
  - Blur : 주변 픽셀들의 값을 평균 내어 노이즈를 제거
  - Sharpening : 이미지를 더 또렷하고 날카롭게, 중심 픽셀과 주변 픽셀의 차이를 극대화하여 흐릿한 이미지를 선명하게
  - Edge Detection : 물체의 경계선을 찾는 필터, 값이 급격하게 변하는 부분을 감지하여 흰색 선으로 남기고 나머지는 검은색으로

# Intel Real Sense
## test.py
```python
import argparse
import pyrealsense2 as rs
import numpy as np

def main():
    p = argparse.ArgumentParser(description="RealSense Depth Camera Example")
    p.add_argument('serial', help='Serial number of the RealSense camera')
    args = p.parse_args()
    devices = list(rs.context().query_devices())

    if not devices:
        print("No RealSense devices found.")
        return
    for d in devices:
        for key in (rs.camera_info.name, rs.camera_info.serial_number, rs.camera_info.usb_type_descriptor):
            print(f"{key}:{d.get_info(key)}")

    if len(devices) > 1 and not args.serial:
        raise SystemExit("Multiple devices found. Please specify the serial number of the device to use.")

    config = rs.config()

    if args.serial:
        config.enable_device(args.serial)

    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline = rs.pipeline()
    started = False

    try:
        pipeline.start(config)
        started = True

        color = pipeline.wait_for_frames().get_color_frame()
        if not color:
            raise RuntimeError("Could not acquire color frame.")

        array = np.asanyarray(color.get_data())
        print("Color frame shape:", array.shape)

    except Exception as e:
        print("Error:", e)

    finally:
        if started:
            pipeline.stop()

if __name__ == "__main__":
    main()
```
## shell
```shell
lsusb -v -d 8086: | grep -i "iSerial"
python3 "file_name" "Serial_number"
```
## 결과 : 
```shell
camera_info.name:RealSense D435
camera_info.serial_number:261822072247
camera_info.usb_type_descriptor:3.2
Color frame shape: (480, 640, 3)
```

## test_rs.py
```python
import argparse
import cv2
import numpy as np
import pyrealsense2 as rs


def main():
    parser = argparse.ArgumentParser(description="RealSense Camera Example")
    parser.add_argument("--width", type=int, default=640, help="Width of the image")
    parser.add_argument(
        "-s", "--serial", type=str, help="Serial number of the RealSense device"
    )
    args = parser.parse_args()

    context = rs.context()
    devices = list(context.query_devices())

    if not devices:
        print("No RealSense devices found.")
        return

    if len(devices) > 1 and not args.serial:
        print("Multiple RealSense devices found. Please connect only one device.")
        for device in devices:
            print(f"Device: {device.get_info(rs.camera_info.name)}, Serial: {device.get_info(rs.camera_info.serial_number)}")
        return

    config = rs.config()
    if args.serial:
        config.enable_device(args.serial)
    config.enable_stream(rs.stream.color, args.width, 480, rs.format.bgr8, 30)

    pipeline = rs.pipeline()
    started = False

    try:
        pipeline.start(config)
        started = True
        print("Pipeline started successfully.")

        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()

            if not color_frame:
                continue

            frame = np.asanyarray(color_frame.get_data())
            cv2.imshow("RealSense Color Frame", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if started:
            pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```
## shell
```shell
python3 test_opencr.py -s 261822072247
```
## 결과 : 
```shell
Pipeline started successfully.
QFontDatabase: Cannot find font directory /home/pa4/git/opencv/opencv/lib/python3.12/site-packages/cv2/qt/fonts.
Note that Qt no longer ships fonts. Deploy some (from https://dejavu-fonts.github.io/ for example) or switch to fontconfig.
QFontDatabase: Cannot find font directory /home/pa4/git/opencv/opencv/lib/python3.12/site-packages/cv2/qt/fonts.
Note that Qt no longer ships fonts. Deploy some (from https://dejavu-fonts.github.io/ for example) or switch to fontconfig.
QFontDatabase: Cannot find font directory /home/pa4/git/opencv/opencv/lib/python3.12/site-packages/cv2/qt/fonts.
Note that Qt no longer ships fonts. Deploy some (from https://dejavu-fonts.github.io/ for example) or switch to fontconfig.
QFontDatabase: Cannot find font directory /home/pa4/git/opencv/opencv/lib/python3.12/site-packages/cv2/qt/fonts.
Note that Qt no longer ships fonts. Deploy some (from https://dejavu-fonts.github.io/ for example) or switch to fontconfig.
QFontDatabase: Cannot find font directory /home/pa4/git/opencv/opencv/lib/python3.12/site-packages/cv2/qt/fonts.
Note that Qt no longer ships fonts. Deploy some (from https://dejavu-fonts.github.io/ for example) or switch to fontconfig.
^C^CTraceback (most recent call last):
  File "/home/pa4/git/opencv/test_opencr.py", line 42, in main
    frames = pipeline.wait_for_frames()
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
KeyboardInterrupt

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/pa4/git/opencv/test_opencr.py", line 62, in <module>
    main()
  File "/home/pa4/git/opencv/test_opencr.py", line 58, in main
    pipeline.stop()
KeyboardInterrupt
```
- 카메라 켜짐