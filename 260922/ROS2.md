# Raspberry Pi
```shell
ping pa23.local -4
ssh pa23@10.2.16.237
```
```shell
hostname
cat /etc/os-release
uname -m
df -h "$HOME"
```
```shell
export BASE="$HOME/pa-opencr-build"
set -o pipefail
mkdir -p "$BASE"/{bin,downloads,data,user,sketches,output}
sudo apt update
sudo apt install -y build-essential curl git python3-serial \
  gcc-arm-none-eabi libnewlib-arm-none-eabi \
  libstdc++-arm-none-eabi-newlib usbutils file
arm-none-eabi-g++ --version
sudo usermod -aG dialout "$USER"
```
```shell
cd "$BASE/downloads"
VER=1.5.1
ASSET="arduino-cli_${VER}_Linux_ARM64.tar.gz"
RELEASE="https://github.com/arduino/arduino-cli/releases/download"
curl -fL -o "$ASSET" "$RELEASE/v$VER/$ASSET"
curl -fL -o checksums.txt \
  "$RELEASE/v$VER/${VER}-checksums.txt"
grep "  $ASSET\$" checksums.txt | sha256sum -c -
```
- 체크섬 검증이 OK일 때만 압축을 풀어 실행합니다.
```shell
tar -xzf "$ASSET" -C "$BASE/bin" arduino-cli
file "$BASE/bin/arduino-cli"
"$BASE/bin/arduino-cli" version
```
```shell
cat > "$BASE/arduino-cli.yaml" <<EOF
directories:
  data: $BASE/data
  downloads: $BASE/downloads
  user: $BASE/user
EOF
"$BASE/bin/arduino-cli" --config-file "$BASE/arduino-cli.yaml" \
  core update-index
"$BASE/bin/arduino-cli" --config-file "$BASE/arduino-cli.yaml" \
  board listall
```
- 보드 목록에 OpenCR Board와 **ROBOTIS:OpenCR:OpenCR**이 있어야 합니다.
```shell
mkdir -p "$BASE/user/libraries"
git clone https://github.com/ROBOTIS-GIT/Dynamixel2Arduino.git \
  "$BASE/user/libraries/Dynamixel2Arduino"
git -C "$BASE/user/libraries/Dynamixel2Arduino" checkout \
  cfbbaf79581ecfcdec952a87916572885453f4ab
```
```shell
cat > "$BASE/user/hardware/ROBOTIS/OpenCR/platform.local.txt" <<'EOF'
compiler.path=/usr/bin/
EOF
arm-none-eabi-g++ --version
```
- 제공 소스의 기본 대상은 XM430-W350(모델 1020), ID 12, 1 Mbps, Protocol 2.0입니다. 본인 장비가 다르면 검증된 호환 소스·설정이 필요합니다. 모델 검사를 제거하지 마세요.
```shell
git clone https://github.com/SpartaPA/physicalai-lv2-assignments.git \
  "$BASE/repo"
SOURCE=$(find "$BASE/repo" -type d -name opencr_position_p -print -quit)
test -n "$SOURCE" && test -f "$SOURCE/opencr_position_p.ino"
```
- 소스를 찾았을 때만 작업 폴더에 복사하고 빌드
```shell
cp -r "$SOURCE" "$BASE/sketches/"
set -o pipefail
"$BASE/bin/arduino-cli" --config-file "$BASE/arduino-cli.yaml" \
  compile --fqbn ROBOTIS:OpenCR:OpenCR --jobs 1 \
  --output-dir "$BASE/output" \
  "$BASE/sketches/opencr_position_p" 2>&1 | tee "$BASE/build.log"
```
- 빌드가 성공했을 때만 아래 결과를 확인
```shell
test -s "$BASE/output/opencr_position_p.ino.bin"
file "$BASE/output/opencr_position_p.ino.elf"
arm-none-eabi-size "$BASE/output/opencr_position_p.ino.elf"
sha256sum "$BASE/output/opencr_position_p.ino.bin"
```
```shell
mkdir "$BASE/uploader-src"
cd "$BASE/uploader-src"
git init
git remote add origin https://github.com/ROBOTIS-GIT/OpenCR.git
git sparse-checkout init --cone
git sparse-checkout set arduino/opencr_develop/opencr_ld
git fetch --depth 1 --filter=blob:none origin \
  68ec75d8a400949580ecf263e0105ea9743b878e
git checkout --detach FETCH_HEAD
make -C arduino/opencr_develop/opencr_ld
file arduino/opencr_develop/opencr_ld/opencr_ld
```

# Open CR
```shell
lsusb
ls -l /dev/ttyACM*
```
- 결과_ex = dev/ttyACM0
```shell
PORT=/dev/ttyACM0
udevadm info --query=property --name="$PORT"
test -r "$PORT" && test -w "$PORT" && echo 'Port access OK'
```
```shell
UPLOADER="$BASE/uploader-src/arduino/opencr_develop/opencr_ld/opencr_ld"
set -o pipefail
"$UPLOADER" "$PORT" 115200 \
  "$BASE/output/opencr_position_p.ino.bin" 1 \
  2>&1 | tee "$BASE/upload.log"
```
```shell
ls -l /dev/ttyACM*
PORT=/dev/ttyACM0
python3 -m serial.tools.miniterm "$PORT" 115200 --eol LF
```

# Restart
```shell
export BASE="$HOME/pa-opencr-build"
set -o pipefail
cd "$BASE/uploader-src"
ls -l /dev/ttyACM*
PORT=/dev/ttyACM0
python3 -m serial.tools.miniterm "$PORT" 115200 --eol LF
```