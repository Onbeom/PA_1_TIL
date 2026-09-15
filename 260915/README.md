# ADUINO - IDE

## 모터 및 보드 인식
```c++
/*******************************************************************************
* Copyright 2016 ROBOTIS CO., LTD.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*******************************************************************************/

#include <Dynamixel2Arduino.h>

// Please modify it to suit your hardware.
#if defined(ARDUINO_AVR_UNO) || defined(ARDUINO_AVR_MEGA2560) // When using DynamixelShield
  #include <SoftwareSerial.h>
  SoftwareSerial soft_serial(7, 8); // DYNAMIXELShield UART RX/TX
  #define DXL_SERIAL   Serial
  #define DEBUG_SERIAL soft_serial
  const int DXL_DIR_PIN = 2; // DYNAMIXEL Shield DIR PIN
#elif defined(ARDUINO_SAM_DUE) // When using DynamixelShield
  #define DXL_SERIAL   Serial
  #define DEBUG_SERIAL SerialUSB
  const int DXL_DIR_PIN = 2; // DYNAMIXEL Shield DIR PIN
#elif defined(ARDUINO_SAM_ZERO) // When using DynamixelShield
  #define DXL_SERIAL   Serial1
  #define DEBUG_SERIAL SerialUSB
  const int DXL_DIR_PIN = 2; // DYNAMIXEL Shield DIR PIN
#elif defined(ARDUINO_OpenCM904) // When using official ROBOTIS board with DXL circuit.
  #define DXL_SERIAL   Serial3 //OpenCM9.04 EXP Board's DXL port Serial. (Serial1 for the DXL port on the OpenCM 9.04 board)
  #define DEBUG_SERIAL Serial
  const int DXL_DIR_PIN = 22; //OpenCM9.04 EXP Board's DIR PIN. (28 for the DXL port on the OpenCM 9.04 board)
#elif defined(ARDUINO_OpenCR) // When using official ROBOTIS board with DXL circuit.
  // For OpenCR, there is a DXL Power Enable pin, so you must initialize and control it.
  // Reference link : https://github.com/ROBOTIS-GIT/OpenCR/blob/master/arduino/opencr_arduino/opencr/libraries/DynamixelSDK/src/dynamixel_sdk/port_handler_arduino.cpp#L78
  #define DXL_SERIAL   Serial3
  #define DEBUG_SERIAL Serial
  const int DXL_DIR_PIN = 84; // OpenCR Board's DIR PIN.
#elif defined(ARDUINO_OpenRB)  // When using OpenRB-150
  //OpenRB does not require the DIR control pin.
  #define DXL_SERIAL Serial1
  #define DEBUG_SERIAL Serial
  const int DXL_DIR_PIN = -1;
#else // Other boards when using DynamixelShield
  #define DXL_SERIAL   Serial1
  #define DEBUG_SERIAL Serial
  const int DXL_DIR_PIN = 2; // DYNAMIXEL Shield DIR PIN
#endif


#define MAX_BAUD  5
const int32_t buad[MAX_BAUD] = {57600, 115200, 1000000, 2000000, 3000000};

Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);

//This namespace is required to use Control table item names
using namespace ControlTableItem;

void setup() {
  // put your setup code here, to run once:
  int8_t index = 0;
  int8_t found_dynamixel = 0;

  // Use UART port of DYNAMIXEL Shield to debug.
  DEBUG_SERIAL.begin(115200);   //set debugging port baudrate to 115200bps
  while(!DEBUG_SERIAL);         //Wait until the serial port is opened

  for(int8_t protocol = 1; protocol < 3; protocol++) {
    // Set Port Protocol Version. This has to match with DYNAMIXEL protocol version.
    dxl.setPortProtocolVersion((float)protocol);
    DEBUG_SERIAL.print("SCAN PROTOCOL ");
    DEBUG_SERIAL.println(protocol);

    for(index = 0; index < MAX_BAUD; index++) {
      // Set Port baudrate.
      DEBUG_SERIAL.print("SCAN BAUDRATE ");
      DEBUG_SERIAL.println(buad[index]);
      dxl.begin(buad[index]);
      for(int id = 0; id < DXL_BROADCAST_ID; id++) {
        //iterate until all ID in each buadrate is scanned.
        if(dxl.ping(id)) {
          DEBUG_SERIAL.print("ID : ");
          DEBUG_SERIAL.print(id);
          DEBUG_SERIAL.print(", Model Number: ");
          DEBUG_SERIAL.println(dxl.getModelNumber(id));
          found_dynamixel++;
        }
      }
    }
  }

  DEBUG_SERIAL.print("Total ");
  DEBUG_SERIAL.print(found_dynamixel);
  DEBUG_SERIAL.println(" DYNAMIXEL(s) found!");
}

void loop() {
  // put your main code here, to run repeatedly:
}
```
### 결과
```c++
12:56:13.070 -> SCAN BAUDRATE 57600
12:56:16.364 -> SCAN BAUDRATE 115200
12:56:17.135 -> SCAN BAUDRATE 1000000
12:56:19.931 -> ID : 2, Model Number: 1030
12:56:25.027 -> SCAN PROTOCOL 1
12:56:25.027 -> SCAN BAUDRATE 57600
12:56:28.305 -> SCAN BAUDRATE 115200
12:56:31.342 -> SCAN BAUDRATE 1000000
12:56:34.387 -> SCAN BAUDRATE 2000000
12:56:37.421 -> SCAN BAUDRATE 3000000
12:56:40.475 -> SCAN PROTOCOL 2
12:56:40.475 -> SCAN BAUDRATE 57600
12:56:43.761 -> SCAN BAUDRATE 115200
12:56:46.780 -> SCAN BAUDRATE 1000000
12:56:47.327 -> ID : 2, Model Number: 1030
12:56:49.845 -> SCAN BAUDRATE 2000000
12:56:52.876 -> SCAN BAUDRATE 3000000
12:56:55.901 -> Total 1 DYNAMIXEL(s) found!
```

## kp test code

```c++
// Lv2 2강: OpenCR에서 위치 오차를 읽고 P 제어로 속도를 보정한다.
// 기준 하드웨어: XM430-W350-T/R, Protocol 2.0, firmware >= 38, 모터 1개.
#include <Dynamixel2Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

using namespace ControlTableItem;
Dynamixel2Arduino dxl(Serial3, 84);  // OpenCR DXL 포트 / 방향 제어 핀

const uint8_t DXL_ID = 2;          // 사용자 모터 검색 결과
const uint32_t DXL_BAUD = 1000000;
constexpr float PI_F = 3.14159265358979323846f;
constexpr float RAD_PER_DEG = PI_F / 180.0f;
constexpr float RAD_PER_TICK = 2.0f * PI_F / 4096.0f;
constexpr float RAD_S_PER_VELOCITY_RAW = 0.229f * 2.0f * PI_F / 60.0f;
constexpr float DEFAULT_SPEED_RAD_S = 20.0f * RAD_PER_DEG;
constexpr float MIN_SPEED_DEG_S = 2.0f;
constexpr float MAX_SPEED_DEG_S = 30.0f;
constexpr float MAX_ANGLE_DEG = 90.0f;
constexpr float MIN_POSITION_RAD = -120.0f * RAD_PER_DEG;
constexpr float MAX_POSITION_RAD = 120.0f * RAD_PER_DEG;
constexpr float DEADBAND_RAD = 0.2f * RAD_PER_DEG;
const uint32_t PERIOD_US = 10000;    // 100 Hz 요청 주기; 실제 dt는 로그로 확인
uint32_t run_ms = 60000;  // 시작할 때 입력 각도·속도로 결정한다. 최소 60초.
constexpr float MAX_GAIN = 2.0f;

bool running = false;
bool faulted = false;
float kp = 0.5f;                    // [1/s], 모터 내부 Position P Gain과 다름
float speed_limit_rad_s = DEFAULT_SPEED_RAD_S;
float goal_rad = 90.0f * RAD_PER_DEG;
int32_t origin_ticks = 0;
uint32_t started_ms = 0, last_us = 0, last_log_ms = 0;

constexpr float limitSpeed(float speed, float limit) {
  return speed > limit ? limit : speed < -limit ? -limit : speed;
}

constexpr float feedbackVelocity(float error_rad, float gain, float limit) {
  return (error_rad > -DEADBAND_RAD && error_rad < DEADBAND_RAD)
         ? 0.0f : limitSpeed(gain * error_rad, limit);
}

int32_t velocityToRaw(float speed, float limit) {
  const int32_t raw_limit = static_cast<int32_t>(limit / RAD_S_PER_VELOCITY_RAW);
  return constrain(static_cast<int32_t>(lroundf(speed / RAD_S_PER_VELOCITY_RAW)),
                   -raw_limit, raw_limit);  // 반올림 후에도 입력한 명령 상한을 넘지 않는다.
}

// 빌드할 때 실제 제어 함수의 부호, 영점, 데드밴드, 양방향 포화를 검증한다.
static_assert(feedbackVelocity(0.0f, 1.0f, DEFAULT_SPEED_RAD_S) == 0.0f, "zero error");
static_assert(feedbackVelocity(DEADBAND_RAD / 2.0f, 1.0f, DEFAULT_SPEED_RAD_S) == 0.0f, "deadband");
static_assert(feedbackVelocity(0.1f, 2.0f, DEFAULT_SPEED_RAD_S) == 0.2f, "positive command");
static_assert(feedbackVelocity(-0.1f, 2.0f, DEFAULT_SPEED_RAD_S) == -0.2f, "negative command");
static_assert(feedbackVelocity(1.0f, 2.0f, 0.1f) == 0.1f, "custom positive limit");
static_assert(feedbackVelocity(-1.0f, 2.0f, 0.1f) == -0.1f, "custom negative limit");
static_assert(MAX_ANGLE_DEG * RAD_PER_DEG < MAX_POSITION_RAD &&
              -MAX_ANGLE_DEG * RAD_PER_DEG > MIN_POSITION_RAD, "target range");

constexpr bool validSetting(char key, float value) {
  return key == 'k' ? value > 0 && value <= MAX_GAIN :
         key == 'v' ? value >= MIN_SPEED_DEG_S && value <= MAX_SPEED_DEG_S :
         key == 'a' ? value >= -MAX_ANGLE_DEG && value <= MAX_ANGLE_DEG : false;
}

bool parseSettingCommand(const char *line, float &value) {
  if (line[0] != 'k' && line[0] != 'v' && line[0] != 'a') return false;
  char *end;
  value = strtof(line + 1, &end);
  if (end == line + 1) return false;
  while (isspace(static_cast<unsigned char>(*end))) ++end;
  return *end == '\0' && isfinite(value) && validSetting(line[0], value);
}

bool parseRunCommand(const char *line, float &gain, float &speed_deg_s, float &angle_deg) {
  if (line[0] != 's' || !isspace(static_cast<unsigned char>(line[1]))) return false;
  const char *cursor = line + 1;
  float values[3];
  for (uint8_t i = 0; i < 3; ++i) {
    char *end;
    values[i] = strtof(cursor, &end);
    if (end == cursor || !isfinite(values[i])) return false;
    if (*end != '\0' && !isspace(static_cast<unsigned char>(*end))) return false;
    cursor = end;
  }
  while (isspace(static_cast<unsigned char>(*cursor))) ++cursor;
  if (*cursor != '\0' || !validSetting('k', values[0]) ||
      !validSetting('v', values[1]) || !validSetting('a', values[2])) return false;
  gain = values[0]; speed_deg_s = values[1]; angle_deg = values[2];
  return true;  // 세 값 모두 유효할 때에만 적용한다.
}

bool settingsSelfCheck() {
  float value, gain, speed, angle;
  return parseSettingCommand("k 0.1", value) && value == 0.1f &&
         parseSettingCommand("v 2", value) && value == 2 &&
         parseSettingCommand("a -90", value) && value == -90 &&
         !parseSettingCommand("k nan", value) && !parseSettingCommand("k inf", value) &&
         !parseSettingCommand("k 0", value) && !parseSettingCommand("k -1", value) &&
         !parseSettingCommand("k 99", value) && !parseSettingCommand("k 0.1 junk", value) &&
         !parseSettingCommand("v 0", value) && !parseSettingCommand("v 31", value) &&
         !parseSettingCommand("a 91", value) && !parseSettingCommand("k", value) &&
         parseRunCommand("s 0.1 20 -45", gain, speed, angle) &&
         gain == 0.1f && speed == 20 && angle == -45 &&
         !parseRunCommand("s 0.1 20", gain, speed, angle) &&
         !parseRunCommand("s 0.1 20 90 extra", gain, speed, angle) &&
         !parseRunCommand("s 0.1 inf 90", gain, speed, angle) &&
         !parseRunCommand("s 0.1 20 91", gain, speed, angle);
}

void printSettings() {
  Serial.print("SET Kp="); Serial.print(kp, 4);
  Serial.print(", speed_limit_deg_s="); Serial.print(speed_limit_rad_s / RAD_PER_DEG, 3);
  Serial.print(", angle_deg="); Serial.println(goal_rad / RAD_PER_DEG, 3);
}

void stopRun(const char *reason, bool fault) {
  running = false;
  // 읽기 실패를 위치 0으로 해석하지 않는다. 정지 패킷은 각각 한 번 보낸다.
  const bool zero_ok = dxl.setGoalVelocity(DXL_ID, 0, UNIT_RPM);
  const bool off_ok = dxl.torqueOff(DXL_ID);
  faulted = fault || !zero_ok || !off_ok;
  if (faulted) {
    // OpenCR에서 전원을 공급받는 DXL 포트를 차단한다. RESET 전까지 재시작 금지.
    digitalWrite(BDPIN_DXL_PWR_EN, LOW);
  }
  Serial.print(faulted ? "FAULT (RESET required): " : "STOP: ");
  Serial.println(reason);
}

bool requireOk(bool ok, const char *reason) {
  if (!ok) {
    const auto lib_error = dxl.getLastLibErrCode();
    const auto status_error = dxl.getLastStatusPacketError();
    stopRun(reason, true);  // 정지 통신이 원래 오류를 덮어쓰기 전에 위에서 보존한다.
    Serial.print("DXL lib_error="); Serial.print(lib_error);
    Serial.print(", status_error="); Serial.println(status_error);
  }
  return ok;
}

bool readItem(uint8_t item, int32_t &value) {
  value = dxl.readControlTableItem(item, DXL_ID, 10);  // timeout [ms]
  return requireOk(dxl.getLastLibErrCode() == DXL_LIB_OK &&
                   dxl.getLastStatusPacketError() == 0, "DXL read failed");
}

void startRun() {
  if (running || faulted) return;
  // watchdog 오류를 지우고, 남아 있는 속도 명령을 0으로 만든 뒤 토크를 켠다.
  if (!requireOk(dxl.writeControlTableItem(BUS_WATCHDOG, DXL_ID, 0), "watchdog clear") ||
      !requireOk(dxl.setGoalVelocity(DXL_ID, 0, UNIT_RPM), "zero velocity") ||
      !requireOk(dxl.torqueOn(DXL_ID), "torque on") ||
      !requireOk(dxl.writeControlTableItem(BUS_WATCHDOG, DXL_ID, 5), "watchdog set")) return;
  if (!readItem(PRESENT_POSITION, origin_ticks)) return;
  const uint32_t estimated_ms = 12000UL +
      static_cast<uint32_t>(ceilf(3000.0f * fabsf(goal_rad) / speed_limit_rad_s));
  run_ms = estimated_ms > 60000UL ? estimated_ms : 60000UL;
  started_ms = millis();
  last_log_ms = started_ms;
  last_us = micros();
  running = true;
  Serial.println("START: current position = 0 deg.");
  printSettings();
  Serial.print("Run timeout [s]: "); Serial.println(run_ms / 1000.0f, 1);
}

void readCommands() {
  static char line[64];
  static uint8_t used = 0;
  static bool overflow = false;
  for (uint8_t n = 0; n < 32 && Serial.available(); ++n) {
    const char c = Serial.read();
    if (c == 'x') {  // 정지는 줄바꿈을 기다리지 않는다.
      used = 0; overflow = false;
      if (running) stopRun("user", false);
      continue;
    }
    if (c == '\r' || c == '\n') {
      line[used] = '\0';
      float value, gain, speed, angle;
      if (overflow) Serial.println("Command too long; discarded.");
      else if (used && faulted) Serial.println("FAULT: RESET required.");
      else if (used && running) Serial.println("Running: send x before changing settings.");
      else if (used && strcmp(line, "s") == 0) startRun();
      else if (used && parseRunCommand(line, gain, speed, angle)) {
        kp = gain; speed_limit_rad_s = speed * RAD_PER_DEG; goal_rad = angle * RAD_PER_DEG;
        startRun();
      } else if (used && parseSettingCommand(line, value)) {
        if (line[0] == 'k') kp = value;
        if (line[0] == 'v') speed_limit_rad_s = value * RAD_PER_DEG;
        if (line[0] == 'a') goal_rad = value * RAD_PER_DEG;
        printSettings();
      } else if (used) {
        Serial.print("Invalid setting. Kp (0, "); Serial.print(MAX_GAIN, 4);
        Serial.println("], speed 2..30 deg/s, angle -90..90 deg. Use k/v/a or s <gain> <speed> <angle>.");
      }
      used = 0; overflow = false;
    } else if (!overflow) {
      if (used < sizeof(line) - 1) line[used++] = c;
      else overflow = true;
    }
  }
}

void setup() {
  Serial.begin(115200);
  dxl.begin(DXL_BAUD);  // 라이브러리가 OpenCR의 DXL 전원도 켠다.
  dxl.setPortProtocolVersion(2.0);
  if (!requireOk(dxl.ping(DXL_ID), "ping: check ID/baud/power") ||
      !requireOk(dxl.getModelNumber(DXL_ID) == XM430_W210, "requires XM430-W350") ||
      !requireOk(dxl.torqueOff(DXL_ID), "torque off")) return;
  if (!requireOk(settingsSelfCheck(), "settings parser self-check")) return;
  int32_t value;
  if (!readItem(FIRMWARE_VERSION, value) ||
      !requireOk(value >= 38, "requires firmware >= 38")) return;
  if (!readItem(DRIVE_MODE, value) ||
      !requireOk((value & 4) == 0, "use velocity-based profile: Drive Mode bit 2 = 0")) return;
  if (!readItem(OPERATING_MODE, value)) return;
  if (value != OP_VELOCITY &&
      !requireOk(dxl.setOperatingMode(DXL_ID, OP_VELOCITY), "velocity mode")) return;
  // 매 실험에서 가속 프로파일을 동일하게 유지한다. XM430 raw 단위, 튜닝 가능.
  if (!requireOk(dxl.writeControlTableItem(PROFILE_ACCELERATION, DXL_ID, 5), "acceleration")) return;
  Serial.println("READY: s <gain> <speed_deg_s> <angle_deg>; k/v/a set; s start; x stop. Newline.");
  Serial.print("Max Kp: "); Serial.println(MAX_GAIN, 4);
  printSettings();
}

void loop() {
  readCommands();
  if (!running) return;
  const uint32_t now_us = micros();
  const uint32_t dt_us = now_us - last_us;  // unsigned 차분: micros() wrap 대응
  if (dt_us < PERIOD_US) return;
  if (dt_us > 5 * PERIOD_US) { stopRun("control loop late", true); return; }
  last_us = now_us;
  const uint32_t elapsed_ms = millis() - started_ms;
  if (elapsed_ms >= run_ms) { stopRun("time limit reached; torque off", false); return; }

  int32_t ticks;
  if (!readItem(PRESENT_POSITION, ticks)) return;
  // 32비트 signed 연속 위치를 차분한다. 0/360도 경계에서 각도를 접지 않는다.
  const float position_rad = static_cast<float>(static_cast<int64_t>(ticks) - origin_ticks)
                             * RAD_PER_TICK;
  if (position_rad < MIN_POSITION_RAD || position_rad > MAX_POSITION_RAD) {
    stopRun("travel limit", true); return;
  }

  const float target_rad = elapsed_ms < 2000 ? 0.0f : goal_rad;
  const float error_rad = target_rad - position_rad;
  const float speed_rad_s = feedbackVelocity(error_rad, kp, speed_limit_rad_s);
  const int32_t velocity_raw = velocityToRaw(speed_rad_s, speed_limit_rad_s);
  if (!requireOk(dxl.setGoalVelocity(DXL_ID, velocity_raw, UNIT_RAW),
                 "velocity write failed")) return;

  // ponytail: 동기식 단일 모터 폴링. 다축/더 빠른 주기가 필요하면 Sync Read/Write로 변경.
  if (millis() - last_log_ms >= 100 && Serial) {  // 10 Hz 로그, Arduino Serial Plotter
    last_log_ms = millis();
    Serial.print("target_deg:"); Serial.print(target_rad / RAD_PER_DEG, 3);
    Serial.print("\tposition_deg:"); Serial.print(position_rad / RAD_PER_DEG, 3);
    Serial.print("\terror_deg:"); Serial.print(error_rad / RAD_PER_DEG, 3);
    Serial.print("\tp_deg_s:"); Serial.print(kp * error_rad / RAD_PER_DEG, 3);
    Serial.print("\tu_deg_s:"); Serial.print(velocity_raw * RAD_S_PER_VELOCITY_RAW / RAD_PER_DEG, 3);
    Serial.print("\tv_limit_deg_s:"); Serial.print(speed_limit_rad_s / RAD_PER_DEG, 3);
    Serial.print("\tdt_ms:"); Serial.print(dt_us / 1000.0f, 3);
    Serial.print("\tkp:"); Serial.print(kp, 4);
    Serial.print("\tt_s:"); Serial.println(elapsed_ms / 1000.0f, 3);
  }
}
```
### 결과
```bash
14:39:46.200 -> target_deg:90.000	position_deg:17.139	error_deg:72.861	p_deg_s:36.431	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:3.000
14:39:46.296 -> target_deg:90.000	position_deg:19.072	error_deg:70.928	p_deg_s:35.464	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.001	kp:0.5000	t_s:3.100
14:39:46.392 -> target_deg:90.000	position_deg:20.918	error_deg:69.082	p_deg_s:34.541	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:3.200
14:39:46.489 -> target_deg:90.000	position_deg:22.939	error_deg:67.061	p_deg_s:33.530	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:3.300
14:39:46.618 -> target_deg:90.000	position_deg:24.785	error_deg:65.215	p_deg_s:32.607	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:3.400
14:39:46.715 -> target_deg:90.000	position_deg:26.719	error_deg:63.281	p_deg_s:31.641	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:3.500
14:39:46.811 -> target_deg:90.000	position_deg:28.652	error_deg:61.348	p_deg_s:30.674	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.001	kp:0.5000	t_s:3.600
14:39:46.907 -> target_deg:90.000	position_deg:30.498	error_deg:59.502	p_deg_s:29.751	u_deg_s:19.236	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:3.700
...
114:40:41.494 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:58.303
14:40:41.591 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:58.403
14:40:41.720 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:58.503
14:40:41.817 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.001	kp:0.5000	t_s:58.603
14:40:41.915 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:58.703
14:40:42.013 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:58.803
14:40:42.112 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:58.903
14:40:42.210 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.001	kp:0.5000	t_s:59.003
14:40:42.306 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:59.103
14:40:42.402 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:59.203
14:40:42.500 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:59.303
14:40:42.598 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.001	kp:0.5000	t_s:59.403
14:40:42.695 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:59.503
14:40:42.792 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:59.603
14:40:42.922 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.001	kp:0.5000	t_s:59.703
14:40:43.019 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:0.659	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.000	kp:0.5000	t_s:59.803
14:40:43.118 -> target_deg:90.000	position_deg:88.770	error_deg:1.230	p_deg_s:0.615	u_deg_s:0.000	v_limit_deg_s:20.000	dt_ms:10.001	kp:0.5000	t_s:59.903
14:40:43.216 -> STOP: time limit reached; torque off
```
## modified kp test code

```c++
// Lv2 2강: OpenCR에서 위치 오차를 읽고 P 제어로 속도를 보정한다.
// 기준 하드웨어: XM430-W350-T/R, Protocol 2.0, firmware >= 38, 모터 1개.
#include <Dynamixel2Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

using namespace ControlTableItem;
Dynamixel2Arduino dxl(Serial3, 84);  // OpenCR DXL 포트 / 방향 제어 핀

const uint8_t DXL_ID = 2;          // 사용자 모터 검색 결과
const uint32_t DXL_BAUD = 1000000;
constexpr float PI_F = 3.14159265358979323846f;
constexpr float RAD_PER_DEG = PI_F / 180.0f;
constexpr float RAD_PER_TICK = 2.0f * PI_F / 4096.0f;
constexpr float RAD_S_PER_VELOCITY_RAW = 0.229f * 2.0f * PI_F / 60.0f;
constexpr float DEFAULT_SPEED_RAD_S = 20.0f * RAD_PER_DEG;
constexpr float MAX_ANGLE_DEG = 90.0f;
constexpr float MIN_POSITION_RAD = -120.0f * RAD_PER_DEG;
constexpr float MAX_POSITION_RAD = 120.0f * RAD_PER_DEG;
constexpr float DEADBAND_RAD = 0.2f * RAD_PER_DEG;
const uint32_t PERIOD_US = 10000;    // 100 Hz 요청 주기; 실제 dt는 로그로 확인
uint32_t run_ms = 60000;  // 시작할 때 입력 각도·속도로 결정한다. 최소 60초.

bool running = false;
bool faulted = false;
float kp = 0.5f;                    // [1/s], 모터 내부 Position P Gain과 다름
float speed_limit_rad_s = DEFAULT_SPEED_RAD_S;
float goal_rad = 90.0f * RAD_PER_DEG;
int32_t origin_ticks = 0;
int32_t velocity_limit_raw = 0;  // 모터의 EEPROM 한계를 읽어 사용한다.
uint32_t started_ms = 0, last_us = 0, last_log_ms = 0;

constexpr float limitSpeed(float speed, float limit) {
  return speed > limit ? limit : speed < -limit ? -limit : speed;
}

constexpr float feedbackVelocity(float error_rad, float gain, float limit) {
  return (error_rad > -DEADBAND_RAD && error_rad < DEADBAND_RAD)
         ? 0.0f : limitSpeed(gain * error_rad, limit);
}

int32_t velocityToRaw(float speed, float limit, int32_t motor_limit_raw) {
  // 큰 입력도 정수로 바꾸기 전에 모터가 허용하는 범위로 제한한다.
  const int32_t raw_limit = static_cast<int32_t>(fminf(limit / RAD_S_PER_VELOCITY_RAW, motor_limit_raw));
  const float raw_speed = limitSpeed(speed / RAD_S_PER_VELOCITY_RAW, raw_limit);
  return constrain(static_cast<int32_t>(lroundf(raw_speed)),
                   -raw_limit, raw_limit);  // 반올림 후에도 입력한 명령 상한을 넘지 않는다.
}

// 빌드할 때 실제 제어 함수의 부호, 영점, 데드밴드, 양방향 포화를 검증한다.
static_assert(feedbackVelocity(0.0f, 1.0f, DEFAULT_SPEED_RAD_S) == 0.0f, "zero error");
static_assert(feedbackVelocity(DEADBAND_RAD / 2.0f, 1.0f, DEFAULT_SPEED_RAD_S) == 0.0f, "deadband");
static_assert(feedbackVelocity(0.1f, 2.0f, DEFAULT_SPEED_RAD_S) == 0.2f, "positive command");
static_assert(feedbackVelocity(-0.1f, 2.0f, DEFAULT_SPEED_RAD_S) == -0.2f, "negative command");
static_assert(feedbackVelocity(1.0f, 2.0f, 0.1f) == 0.1f, "custom positive limit");
static_assert(feedbackVelocity(-1.0f, 2.0f, 0.1f) == -0.1f, "custom negative limit");
static_assert(MAX_ANGLE_DEG * RAD_PER_DEG < MAX_POSITION_RAD &&
              -MAX_ANGLE_DEG * RAD_PER_DEG > MIN_POSITION_RAD, "target range");

uint32_t trialDurationMs(float angle_rad, float speed_rad_s) {
  const double estimate = 12000.0 + ceil(3000.0 * fabs(angle_rad) / speed_rad_s);
  // 아주 작은 속도에서도 타이머 정수 변환이 넘치지 않게 한다(최대 약 24.9일).
  return static_cast<uint32_t>(fmin(2147483647.0, fmax(60000.0, estimate)));
}
constexpr bool validSetting(char key, float value) {
  return key == 'k' ? true :
         key == 'v' ? value > 0 && value * RAD_PER_DEG > 0 :
         key == 'a' ? value >= -MAX_ANGLE_DEG && value <= MAX_ANGLE_DEG : false;
}

bool parseSettingCommand(const char *line, float &value) {
  if (line[0] != 'k' && line[0] != 'v' && line[0] != 'a') return false;
  char *end;
  value = strtof(line + 1, &end);
  if (end == line + 1) return false;
  while (isspace(static_cast<unsigned char>(*end))) ++end;
  return *end == '\0' && isfinite(value) && validSetting(line[0], value);
}

bool parseRunCommand(const char *line, float &gain, float &speed_deg_s, float &angle_deg) {
  if (line[0] != 's' || !isspace(static_cast<unsigned char>(line[1]))) return false;
  const char *cursor = line + 1;
  float values[3];
  for (uint8_t i = 0; i < 3; ++i) {
    char *end;
    values[i] = strtof(cursor, &end);
    if (end == cursor || !isfinite(values[i])) return false;
    if (*end != '\0' && !isspace(static_cast<unsigned char>(*end))) return false;
    cursor = end;
  }
  while (isspace(static_cast<unsigned char>(*cursor))) ++cursor;
  if (*cursor != '\0' || !validSetting('k', values[0]) ||
      !validSetting('v', values[1]) || !validSetting('a', values[2])) return false;
  gain = values[0]; speed_deg_s = values[1]; angle_deg = values[2];
  return true;  // 세 값 모두 유효할 때에만 적용한다.
}

bool settingsSelfCheck() {
  float value, gain, speed, angle;
  return parseSettingCommand("k 0.1", value) && value == 0.1f &&
         parseSettingCommand("v 2", value) && value == 2 &&
         parseSettingCommand("a -90", value) && value == -90 &&
         !parseSettingCommand("k nan", value) && !parseSettingCommand("k inf", value) &&
         parseSettingCommand("k 0", value) && value == 0 &&
         parseSettingCommand("k -1", value) && value == -1 &&
         parseSettingCommand("k 99", value) && value == 99 &&
         !parseSettingCommand("k 0.1 junk", value) && !parseSettingCommand("k 1e100", value) &&
         parseSettingCommand("v 0.01", value) && value == 0.01f &&
         parseSettingCommand("v 1000", value) && value == 1000 &&
         !parseSettingCommand("v 0", value) && !parseSettingCommand("v -1", value) &&
         !parseSettingCommand("v 1e-45", value) &&
         !parseSettingCommand("a 91", value) && !parseSettingCommand("k", value) &&
         parseRunCommand("s 0.1 20 -45", gain, speed, angle) &&
         gain == 0.1f && speed == 20 && angle == -45 &&
         parseRunCommand("s -99 1000 45", gain, speed, angle) &&
         gain == -99 && speed == 1000 && angle == 45 &&
         !parseRunCommand("s 0.1 20", gain, speed, angle) &&
         !parseRunCommand("s 0.1 20 90 extra", gain, speed, angle) &&
         !parseRunCommand("s 0.1 inf 90", gain, speed, angle) &&
         !parseRunCommand("s 0.1 20 91", gain, speed, angle);
}

void printSettings() {
  Serial.print("SET Kp="); Serial.print(kp, 4);
  Serial.print(", speed_limit_deg_s="); Serial.print(speed_limit_rad_s / RAD_PER_DEG, 3);
  Serial.print(", angle_deg="); Serial.println(goal_rad / RAD_PER_DEG, 3);
}

void stopRun(const char *reason, bool fault) {
  running = false;
  // 읽기 실패를 위치 0으로 해석하지 않는다. 정지 패킷은 각각 한 번 보낸다.
  const bool zero_ok = dxl.setGoalVelocity(DXL_ID, 0, UNIT_RPM);
  const bool off_ok = dxl.torqueOff(DXL_ID);
  faulted = fault || !zero_ok || !off_ok;
  if (faulted) {
    // OpenCR에서 전원을 공급받는 DXL 포트를 차단한다. RESET 전까지 재시작 금지.
    digitalWrite(BDPIN_DXL_PWR_EN, LOW);
  }
  Serial.print(faulted ? "FAULT (RESET required): " : "STOP: ");
  Serial.println(reason);
}

bool requireOk(bool ok, const char *reason) {
  if (!ok) {
    const auto lib_error = dxl.getLastLibErrCode();
    const auto status_error = dxl.getLastStatusPacketError();
    stopRun(reason, true);  // 정지 통신이 원래 오류를 덮어쓰기 전에 위에서 보존한다.
    Serial.print("DXL lib_error="); Serial.print(lib_error);
    Serial.print(", status_error="); Serial.println(status_error);
  }
  return ok;
}

bool readItem(uint8_t item, int32_t &value) {
  value = dxl.readControlTableItem(item, DXL_ID, 10);  // timeout [ms]
  return requireOk(dxl.getLastLibErrCode() == DXL_LIB_OK &&
                   dxl.getLastStatusPacketError() == 0, "DXL read failed");
}

void startRun() {
  if (running || faulted) return;
  // watchdog 오류를 지우고, 남아 있는 속도 명령을 0으로 만든 뒤 토크를 켠다.
  if (!requireOk(dxl.writeControlTableItem(BUS_WATCHDOG, DXL_ID, 0), "watchdog clear") ||
      !requireOk(dxl.setGoalVelocity(DXL_ID, 0, UNIT_RPM), "zero velocity") ||
      !requireOk(dxl.torqueOn(DXL_ID), "torque on") ||
      !requireOk(dxl.writeControlTableItem(BUS_WATCHDOG, DXL_ID, 5), "watchdog set")) return;
  if (!readItem(PRESENT_POSITION, origin_ticks)) return;
  run_ms = trialDurationMs(goal_rad, speed_limit_rad_s);
  started_ms = millis();
  last_log_ms = started_ms;
  last_us = micros();
  running = true;
  Serial.println("START: current position = 0 deg.");
  printSettings();
  Serial.print("Run timeout [s]: "); Serial.println(run_ms / 1000.0f, 1);
}

void readCommands() {
  static char line[64];
  static uint8_t used = 0;
  static bool overflow = false;
  for (uint8_t n = 0; n < 32 && Serial.available(); ++n) {
    const char c = Serial.read();
    if (c == 'x') {  // 정지는 줄바꿈을 기다리지 않는다.
      used = 0; overflow = false;
      if (running) stopRun("user", false);
      continue;
    }
    if (c == '\r' || c == '\n') {
      line[used] = '\0';
      float value, gain, speed, angle;
      if (overflow) Serial.println("Command too long; discarded.");
      else if (used && faulted) Serial.println("FAULT: RESET required.");
      else if (used && running) Serial.println("Running: send x before changing settings.");
      else if (used && strcmp(line, "s") == 0) startRun();
      else if (used && parseRunCommand(line, gain, speed, angle)) {
        kp = gain; speed_limit_rad_s = speed * RAD_PER_DEG; goal_rad = angle * RAD_PER_DEG;
        startRun();
      } else if (used && parseSettingCommand(line, value)) {
        if (line[0] == 'k') kp = value;
        if (line[0] == 'v') speed_limit_rad_s = value * RAD_PER_DEG;
        if (line[0] == 'a') goal_rad = value * RAD_PER_DEG;
        printSettings();
      } else if (used) {
        Serial.println("Invalid setting. Finite Kp, positive speed (deg/s), angle -90..90 deg. Use k/v/a or s <gain> <speed> <angle>.");
      }
      used = 0; overflow = false;
    } else if (!overflow) {
      if (used < sizeof(line) - 1) line[used++] = c;
      else overflow = true;
    }
  }
}

void setup() {
  Serial.begin(115200);
  dxl.begin(DXL_BAUD);  // 라이브러리가 OpenCR의 DXL 전원도 켠다.
  dxl.setPortProtocolVersion(2.0);
  if (!requireOk(dxl.ping(DXL_ID), "ping: check ID/baud/power") ||
      !requireOk(dxl.getModelNumber(DXL_ID) == XM430_W210, "requires XM430-W350") ||
      !requireOk(dxl.torqueOff(DXL_ID), "torque off")) return;
  if (!requireOk(settingsSelfCheck(), "settings parser self-check")) return;
  int32_t value;
  if (!readItem(FIRMWARE_VERSION, value) ||
      !requireOk(value >= 38, "requires firmware >= 38")) return;
  if (!readItem(DRIVE_MODE, value) ||
      !requireOk((value & 4) == 0, "use velocity-based profile: Drive Mode bit 2 = 0")) return;
  if (!readItem(OPERATING_MODE, value)) return;
  if (value != OP_VELOCITY &&
      !requireOk(dxl.setOperatingMode(DXL_ID, OP_VELOCITY), "velocity mode")) return;
  // 매 실험에서 가속 프로파일을 동일하게 유지한다. XM430 raw 단위, 튜닝 가능.
  if (!readItem(VELOCITY_LIMIT, velocity_limit_raw) ||
      !requireOk(velocity_limit_raw >= 0 && velocity_limit_raw <= 1023, "Velocity Limit")) return;
  if (!requireOk(dxl.writeControlTableItem(PROFILE_ACCELERATION, DXL_ID, 5), "acceleration")) return;
  Serial.println("READY: s <gain> <speed_deg_s> <angle_deg>; k/v/a set; s start; x stop. Newline.");
  Serial.println("Kp: any finite value; speed: positive, no input upper limit.");
  Serial.print("Motor velocity raw cap: "); Serial.println(velocity_limit_raw);
  printSettings();
}

void loop() {
  readCommands();
  if (!running) return;
  const uint32_t now_us = micros();
  const uint32_t dt_us = now_us - last_us;  // unsigned 차분: micros() wrap 대응
  if (dt_us < PERIOD_US) return;
  if (dt_us > 5 * PERIOD_US) { stopRun("control loop late", true); return; }
  last_us = now_us;
  const uint32_t elapsed_ms = millis() - started_ms;
  if (elapsed_ms >= run_ms) { stopRun("time limit reached; torque off", false); return; }

  int32_t ticks;
  if (!readItem(PRESENT_POSITION, ticks)) return;
  // 32비트 signed 연속 위치를 차분한다. 0/360도 경계에서 각도를 접지 않는다.
  const float position_rad = static_cast<float>(static_cast<int64_t>(ticks) - origin_ticks)
                             * RAD_PER_TICK;
  if (position_rad < MIN_POSITION_RAD || position_rad > MAX_POSITION_RAD) {
    stopRun("travel limit", true); return;
  }

  const float target_rad = elapsed_ms < 2000 ? 0.0f : goal_rad;
  const float error_rad = target_rad - position_rad;
  const float speed_rad_s = feedbackVelocity(error_rad, kp, speed_limit_rad_s);
  const int32_t velocity_raw = velocityToRaw(speed_rad_s, speed_limit_rad_s, velocity_limit_raw);
  if (!requireOk(dxl.setGoalVelocity(DXL_ID, velocity_raw, UNIT_RAW),
                 "velocity write failed")) return;

  // ponytail: 동기식 단일 모터 폴링. 다축/더 빠른 주기가 필요하면 Sync Read/Write로 변경.
  if (millis() - last_log_ms >= 100 && Serial) {  // 10 Hz 로그, Arduino Serial Plotter
    last_log_ms = millis();
    Serial.print("target_deg:"); Serial.print(target_rad / RAD_PER_DEG, 3);
    Serial.print("\tposition_deg:"); Serial.print(position_rad / RAD_PER_DEG, 3);
    Serial.print("\terror_deg:"); Serial.print(error_rad / RAD_PER_DEG, 3);
    Serial.print("\tp_deg_s:"); Serial.print(kp * error_rad / RAD_PER_DEG, 3);
    Serial.print("\tu_deg_s:"); Serial.print(velocity_raw * RAD_S_PER_VELOCITY_RAW / RAD_PER_DEG, 3);
    Serial.print("\tv_limit_deg_s:"); Serial.print(speed_limit_rad_s / RAD_PER_DEG, 3);
    Serial.print("\tdt_ms:"); Serial.print(dt_us / 1000.0f, 3);
    Serial.print("\tkp:"); Serial.print(kp, 4);
    Serial.print("\tt_s:"); Serial.println(elapsed_ms / 1000.0f, 3);
  }
}
```
### 결과
- s 4.0 45 90(게인값 = 4.0,  최대 속도 제한 = 45, 목표 각도 = 90도 기준)  
    -  error_degree = +- 0.088로, 최대 속도가 45일때 임계 게인값은 4.0임을 알 수 있음.  
        - 감속 구간 각 = 최대 속도 / 게인 값 = 45 / 4.0 = 11.25도 이므로 속도가 X일 때, 임계 게인 값 Kp = X / 11.25

## kp, ki, kd test code

```c++
// Lv2 2강: OpenCR에서 위치 오차를 읽고 PID 제어로 속도를 보정한다.
// 기준 하드웨어: XM430-W350-T/R, Protocol 2.0, firmware >= 38, 모터 1개.
#include <Dynamixel2Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

using namespace ControlTableItem;
Dynamixel2Arduino dxl(Serial3, 84);  // OpenCR DXL 포트 / 방향 제어 핀

const uint8_t DXL_ID = 2;          // 사용자 모터 검색 결과
const uint32_t DXL_BAUD = 1000000;
constexpr float PI_F = 3.14159265358979323846f;
constexpr float RAD_PER_DEG = PI_F / 180.0f;
constexpr float RAD_PER_TICK = 2.0f * PI_F / 4096.0f;
constexpr float RAD_S_PER_VELOCITY_RAW = 0.229f * 2.0f * PI_F / 60.0f;
constexpr float DEFAULT_SPEED_RAD_S = 20.0f * RAD_PER_DEG;
constexpr float MAX_ANGLE_DEG = 90.0f;
constexpr float DEADBAND_RAD = 0.2f * RAD_PER_DEG;
const uint32_t PERIOD_US = 10000;    // 100 Hz 요청 주기; 실제 dt는 로그로 확인
uint32_t run_ms = 60000;  // 시작할 때 입력 각도·속도로 결정한다. 최소 60초.

bool running = false;
bool faulted = false;
float kp = 0.5f;                    // [1/s], 모터 내부 Position P Gain과 다름
float ki = 0.0f, kd = 0.0f;
double p_term = 0, i_term = 0, d_term = 0;
float speed_limit_rad_s = DEFAULT_SPEED_RAD_S;
float goal_rad = 90.0f * RAD_PER_DEG;
int32_t origin_ticks = 0;
int32_t velocity_limit_raw = 0;  // 모터의 EEPROM 한계를 읽어 사용한다.
uint32_t started_ms = 0, last_us = 0, last_log_ms = 0;

constexpr float limitSpeed(float speed, float limit) {
  return speed > limit ? limit : speed < -limit ? -limit : speed;
}

int32_t velocityToRaw(float speed, float limit, int32_t motor_limit_raw) {
  // 큰 입력도 정수로 바꾸기 전에 모터가 허용하는 범위로 제한한다.
  const int32_t raw_limit = static_cast<int32_t>(fminf(limit / RAD_S_PER_VELOCITY_RAW, motor_limit_raw));
  const float raw_speed = limitSpeed(speed / RAD_S_PER_VELOCITY_RAW, raw_limit);
  return constrain(static_cast<int32_t>(lroundf(raw_speed)),
                   -raw_limit, raw_limit);  // 반올림 후에도 입력한 명령 상한을 넘지 않는다.
}

// PID/입력 검사는 ../check_feedback.py 참조.

// P/I는 위치 오차, D는 측정 속도를 사용해 목표 변경 순간의 미분 급증을 피한다.
void resetPid() { p_term = i_term = d_term = 0; }
double feedbackPid(float error_rad, float measured_speed_rad_s, float dt_s,
                   double output_min, double output_max) {
  const float error = fabsf(error_rad) < DEADBAND_RAD ? 0.0f : error_rad;
  p_term = static_cast<double>(kp) * error;
  d_term = -static_cast<double>(kd) * measured_speed_rad_s;
  if (ki == 0) i_term = 0;
  const double integral_limit = fmax(fabs(output_min), fabs(output_max));
  const double candidate = fmax(-integral_limit, fmin(integral_limit,
      i_term + static_cast<double>(ki) * error * dt_s));
  const double candidate_output = p_term + candidate + d_term;
  // 출력 포화를 더 키우는 방향의 적분만 보류한다. PWM 속도 제한도 포함한다.
  if (!((candidate_output > output_max && candidate > i_term) ||
        (candidate_output < output_min && candidate < i_term))) i_term = candidate;
  return fmax(output_min, fmin(output_max, p_term + i_term + d_term));
}

uint32_t trialDurationMs(float angle_rad, float speed_rad_s) {
  const double estimate = 12000.0 + ceil(3000.0 * fabs(angle_rad) / speed_rad_s);
  // 아주 작은 속도에서도 타이머 정수 변환이 넘치지 않게 한다(최대 약 24.9일).
  return static_cast<uint32_t>(fmin(2147483647.0, fmax(60000.0, estimate)));
}
constexpr bool validSetting(char key, float value) {
  return key == 'k' || key == 'i' || key == 'd' ? true :
         key == 'v' ? value > 0 && value * RAD_PER_DEG > 0 :
         key == 'a' ? value >= -MAX_ANGLE_DEG && value <= MAX_ANGLE_DEG : false;
}
bool parseMaxSpeed(const char *text, const char *&end) {
  while (isspace(static_cast<unsigned char>(*text))) ++text;
  if (strncmp(text, "max", 3) != 0 ||
      (text[3] != '\0' && !isspace(static_cast<unsigned char>(text[3])))) return false;
  end = text + 3;
  return true;
}
bool parseSettingCommand(const char *line, float &value) {
  if (line[0] != 'k' && line[0] != 'i' && line[0] != 'd' &&
      line[0] != 'v' && line[0] != 'a') return false;
  const char *max_end;
  if (line[0] == 'v' && parseMaxSpeed(line + 1, max_end)) {
    while (isspace(static_cast<unsigned char>(*max_end))) ++max_end;
    if (*max_end != '\0') return false;
    value = INFINITY; return true;
  }
  char *end;
  value = strtof(line + 1, &end);
  if (end == line + 1) return false;
  while (isspace(static_cast<unsigned char>(*end))) ++end;
  return *end == '\0' && isfinite(value) && validSetting(line[0], value);
}
bool parseRunCommand(const char *line, float &pg, float &ig, float &dg,
                     float &speed_deg_s, float &angle_deg) {
  if (line[0] != 's' || !isspace(static_cast<unsigned char>(line[1]))) return false;
  const char *cursor = line + 1;
  const char keys[] = "kidva";
  float values[5];
  for (uint8_t i = 0; i < 5; ++i) {
    const char *max_end;
    if (i == 3 && parseMaxSpeed(cursor, max_end)) {
      values[i] = INFINITY; cursor = max_end; continue;
    }
    char *end;
    values[i] = strtof(cursor, &end);
    if (end == cursor || !isfinite(values[i]) || !validSetting(keys[i], values[i])) return false;
    if (*end != '\0' && !isspace(static_cast<unsigned char>(*end))) return false;
    cursor = end;
  }
  while (isspace(static_cast<unsigned char>(*cursor))) ++cursor;
  if (*cursor != '\0') return false;
  pg = values[0]; ig = values[1]; dg = values[2];
  speed_deg_s = values[3]; angle_deg = values[4];
  return true;  // 다섯 값 모두 유효할 때에만 적용한다.
}
bool settingsSelfCheck() {
  float value, pg = 1, ig = 2, dg = 3, speed = 20, angle = 90;
  return parseSettingCommand("k 100", value) && value == 100 &&
         parseSettingCommand("i -0.5", value) && value == -0.5f &&
         parseSettingCommand("d 0", value) && value == 0 &&
         parseSettingCommand("v 0.01", value) && value == 0.01f &&
         parseSettingCommand("v 1000", value) && value == 1000 &&
         !parseSettingCommand("k nan", value) && !parseSettingCommand("i inf", value) &&
         !parseSettingCommand("d 1e100", value) && !parseSettingCommand("d 0.1 junk", value) &&
         !parseSettingCommand("v 0", value) && !parseSettingCommand("v -1", value) &&
         !parseSettingCommand("v 1e-45", value) && !parseSettingCommand("a 91", value) &&
         !parseSettingCommand("k", value) &&
         !parseRunCommand("s 3 4 5 20 91", pg, ig, dg, speed, angle) &&
         pg == 1 && ig == 2 && dg == 3 && speed == 20 && angle == 90 &&
         !parseRunCommand("s 3 20 90", pg, ig, dg, speed, angle) &&
         !parseRunCommand("s 3 4 5 20 90 extra", pg, ig, dg, speed, angle) &&
         !parseRunCommand("s 3 nan 5 20 90", pg, ig, dg, speed, angle) &&
         parseRunCommand("s -99 -1 0 1000 -45", pg, ig, dg, speed, angle) &&
         pg == -99 && ig == -1 && dg == 0 && speed == 1000 && angle == -45 &&
         parseRunCommand("s 1 0 0 max 90", pg, ig, dg, speed, angle) && isinf(speed) &&
         parseSettingCommand("v max", value) && isinf(value) &&
         !parseSettingCommand("v inf", value) && !parseSettingCommand("v max junk", value) &&
         !parseRunCommand("s 1 0 0 max90 90", pg, ig, dg, speed, angle);
}

void printSettings() {
  Serial.print("SET Kp="); Serial.print(kp, 4);
  Serial.print(", Ki="); Serial.print(ki, 4);
  Serial.print(", Kd="); Serial.print(kd, 4);
  Serial.print(", speed_limit_deg_s=");
  if (isinf(speed_limit_rad_s)) Serial.print("max");
  else Serial.print(speed_limit_rad_s / RAD_PER_DEG, 3);
  Serial.print(", angle_deg="); Serial.println(goal_rad / RAD_PER_DEG, 3);
}

void stopRun(const char *reason, bool fault) {
  running = false;
  resetPid();
  // 읽기 실패를 위치 0으로 해석하지 않는다. 정지 패킷은 각각 한 번 보낸다.
  const bool zero_ok = dxl.setGoalVelocity(DXL_ID, 0, UNIT_RPM);
  const bool off_ok = dxl.torqueOff(DXL_ID);
  faulted = fault || !zero_ok || !off_ok;
  if (faulted) {
    // OpenCR에서 전원을 공급받는 DXL 포트를 차단한다. RESET 전까지 재시작 금지.
    digitalWrite(BDPIN_DXL_PWR_EN, LOW);
  }
  Serial.print(faulted ? "FAULT (RESET required): " : "STOP: ");
  Serial.println(reason);
}

bool requireOk(bool ok, const char *reason) {
  if (!ok) {
    const auto lib_error = dxl.getLastLibErrCode();
    const auto status_error = dxl.getLastStatusPacketError();
    stopRun(reason, true);  // 정지 통신이 원래 오류를 덮어쓰기 전에 위에서 보존한다.
    Serial.print("DXL lib_error="); Serial.print(lib_error);
    Serial.print(", status_error="); Serial.println(status_error);
  }
  return ok;
}

bool readItem(uint8_t item, int32_t &value) {
  value = dxl.readControlTableItem(item, DXL_ID, 10);  // timeout [ms]
  return requireOk(dxl.getLastLibErrCode() == DXL_LIB_OK &&
                   dxl.getLastStatusPacketError() == 0, "DXL read failed");
}

void startRun() {
  if (running || faulted) return;
  // max에서는 예제의 완만한 가속 프로파일을 해제한다. 숫자 속도는 기존 raw 5.
  if (!requireOk(dxl.writeControlTableItem(PROFILE_ACCELERATION, DXL_ID,
                                         isinf(speed_limit_rad_s) ? 0 : 5), "acceleration")) return;
  // watchdog 오류를 지우고, 남아 있는 속도 명령을 0으로 만든 뒤 토크를 켠다.
  if (!requireOk(dxl.writeControlTableItem(BUS_WATCHDOG, DXL_ID, 0), "watchdog clear") ||
      !requireOk(dxl.setGoalVelocity(DXL_ID, 0, UNIT_RPM), "zero velocity") ||
      !requireOk(dxl.torqueOn(DXL_ID), "torque on") ||
      !requireOk(dxl.writeControlTableItem(BUS_WATCHDOG, DXL_ID, 5), "watchdog set")) return;
  if (!readItem(PRESENT_POSITION, origin_ticks)) return;
  resetPid();
  run_ms = trialDurationMs(goal_rad, speed_limit_rad_s);
  started_ms = millis();
  last_log_ms = started_ms;
  last_us = micros();
  running = true;
  Serial.println("START: current position = 0 deg.");
  printSettings();
  Serial.print("Run timeout [s]: "); Serial.println(run_ms / 1000.0f, 1);
}

void readCommands() {
  static char line[96];
  static uint8_t used = 0;
  static bool overflow = false;
  for (uint8_t n = 0; n < 32 && Serial.available(); ++n) {
    const char c = Serial.read();
    // max 토큰의 마지막 x와 즉시 정지 명령 x를 구분한다.
    const bool max_token_end = !overflow && used >= 2 && line[used - 2] == 'm' &&
        line[used - 1] == 'a' && (used == 2 || isspace(static_cast<unsigned char>(line[used - 3])));
    if (c == 'x' && !max_token_end) {  // 정지는 줄바꿈을 기다리지 않는다.
      used = 0; overflow = false;
      if (running) stopRun("user", false);
      continue;
    }
    if (c == '\r' || c == '\n') {
      line[used] = '\0';
      float value, pg, ig, dg, speed, angle;
      if (overflow) Serial.println("Command too long; discarded.");
      else if (used && faulted) Serial.println("FAULT: RESET required.");
      else if (used && running) Serial.println("Running: send x before changing settings.");
      else if (used && strcmp(line, "s") == 0) startRun();
      else if (used && parseRunCommand(line, pg, ig, dg, speed, angle)) {
        kp = pg; ki = ig; kd = dg;
        speed_limit_rad_s = speed * RAD_PER_DEG; goal_rad = angle * RAD_PER_DEG;
        startRun();
      } else if (used && parseSettingCommand(line, value)) {
        if (line[0] == 'k') kp = value;
        if (line[0] == 'i') ki = value;
        if (line[0] == 'd') kd = value;
        if (line[0] == 'v') speed_limit_rad_s = value * RAD_PER_DEG;
        if (line[0] == 'a') goal_rad = value * RAD_PER_DEG;
        printSettings();
      } else if (used) {
        Serial.println("Invalid setting. Finite Kp/Ki/Kd, positive speed or max, angle -90..90. Use k/i/d/v/a or s <Kp> <Ki> <Kd> <speed> <angle>.");
      }
      used = 0; overflow = false;
    } else if (!overflow) {
      if (used < sizeof(line) - 1) line[used++] = c;
      else overflow = true;
    }
  }
}

void setup() {
  Serial.begin(115200);
  dxl.begin(DXL_BAUD);  // 라이브러리가 OpenCR의 DXL 전원도 켠다.
  dxl.setPortProtocolVersion(2.0);
  if (!requireOk(dxl.ping(DXL_ID), "ping: check ID/baud/power") ||
      !requireOk(dxl.getModelNumber(DXL_ID) == XM430_W210, "requires XM430-W350") ||
      !requireOk(dxl.torqueOff(DXL_ID), "torque off")) return;
  if (!requireOk(settingsSelfCheck(), "settings parser self-check")) return;
  int32_t value;
  if (!readItem(FIRMWARE_VERSION, value) ||
      !requireOk(value >= 38, "requires firmware >= 38")) return;
  if (!readItem(DRIVE_MODE, value) ||
      !requireOk((value & 4) == 0, "use velocity-based profile: Drive Mode bit 2 = 0")) return;
  if (!readItem(OPERATING_MODE, value)) return;
  if (value != OP_VELOCITY &&
      !requireOk(dxl.setOperatingMode(DXL_ID, OP_VELOCITY), "velocity mode")) return;
  // EEPROM 속도 한계는 읽기만 한다. 가속 프로파일은 시작할 때 max 여부로 정한다.
  if (!readItem(VELOCITY_LIMIT, velocity_limit_raw) ||
      !requireOk(velocity_limit_raw >= 0 && velocity_limit_raw <= 1023, "Velocity Limit")) return;
  Serial.println("READY: s <Kp> <Ki> <Kd> <speed_deg_s|max> <angle_deg>; k/i/d/v/a set; s start; x stop. Newline.");
  Serial.println("Kp/Ki/Kd: any finite value; speed: positive or max (motor limits).");
  Serial.print("Motor velocity raw cap: "); Serial.println(velocity_limit_raw);
  printSettings();
}

void loop() {
  readCommands();
  if (!running) return;
  const uint32_t now_us = micros();
  const uint32_t dt_us = now_us - last_us;  // unsigned 차분: micros() wrap 대응
  if (dt_us < PERIOD_US) return;
  if (dt_us > 5 * PERIOD_US) { stopRun("control loop late", true); return; }
  last_us = now_us;
  const uint32_t elapsed_ms = millis() - started_ms;
  if (elapsed_ms >= run_ms) { stopRun("time limit reached; torque off", false); return; }

  int32_t ticks, measured_velocity_raw;
  if (!readItem(PRESENT_POSITION, ticks) || !readItem(PRESENT_VELOCITY, measured_velocity_raw)) return;
  const float measured_speed_rad_s = measured_velocity_raw * RAD_S_PER_VELOCITY_RAW;
  // 32비트 signed 연속 위치를 차분한다. 0/360도 경계에서 각도를 접지 않는다.
  const float position_rad = static_cast<float>(static_cast<int64_t>(ticks) - origin_ticks)
                             * RAD_PER_TICK;

  const float target_rad = elapsed_ms < 2000 ? 0.0f : goal_rad;
  const float error_rad = target_rad - position_rad;
  const int32_t max_velocity_raw = velocityToRaw(speed_limit_rad_s, speed_limit_rad_s, velocity_limit_raw);
  const float output_limit = max_velocity_raw * RAD_S_PER_VELOCITY_RAW;
  const float speed_rad_s = feedbackPid(error_rad, measured_speed_rad_s, dt_us * 1e-6f,
                                        -output_limit, output_limit);
  const int32_t velocity_raw = velocityToRaw(speed_rad_s, speed_limit_rad_s, velocity_limit_raw);
  if (!requireOk(dxl.setGoalVelocity(DXL_ID, velocity_raw, UNIT_RAW),
                 "velocity write failed")) return;

  // ponytail: 동기식 단일 모터 폴링. 다축/더 빠른 주기가 필요하면 Sync Read/Write로 변경.
  if (millis() - last_log_ms >= 100 && Serial) {  // 10 Hz 로그, Arduino Serial Plotter
    last_log_ms = millis();
    Serial.print("target_deg:"); Serial.print(target_rad / RAD_PER_DEG, 3);
    Serial.print("\tposition_deg:"); Serial.print(position_rad / RAD_PER_DEG, 3);
    Serial.print("\terror_deg:"); Serial.print(error_rad / RAD_PER_DEG, 3);
    Serial.print("\tp_deg_s:"); Serial.print(p_term / RAD_PER_DEG, 3);
    Serial.print("\ti_deg_s:"); Serial.print(i_term / RAD_PER_DEG, 3);
    Serial.print("\td_deg_s:"); Serial.print(d_term / RAD_PER_DEG, 3);
    Serial.print("\tpid_deg_s:"); Serial.print((p_term + i_term + d_term) / RAD_PER_DEG, 3);
    Serial.print("\tspeed_deg_s:"); Serial.print(measured_speed_rad_s / RAD_PER_DEG, 3);
    Serial.print("\tu_deg_s:"); Serial.print(velocity_raw * RAD_S_PER_VELOCITY_RAW / RAD_PER_DEG, 3);
    Serial.print("\tv_limit_deg_s:"); Serial.print(isinf(speed_limit_rad_s) ? -1.0f : speed_limit_rad_s / RAD_PER_DEG, 3);
    Serial.print("\tdt_ms:"); Serial.print(dt_us / 1000.0f, 3);
    Serial.print("\tkp:"); Serial.print(kp, 4);
    Serial.print("\tki:"); Serial.print(ki, 4);
    Serial.print("\tkd:"); Serial.print(kd, 4);
    Serial.print("\tt_s:"); Serial.println(elapsed_ms / 1000.0f, 3);
  }
}
```
### 결과
```shell
16:14:36.130 -> START: current position = 0 deg.
16:14:36.130 -> SET Kp=3.8000, Ki=0.1500, Kd=0.1500, speed_limit_deg_s=45.000, angle_deg=90.000
16:14:36.130 -> Run timeout [s]: 60.0
16:14:36.227 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.100
16:14:36.324 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.200
16:14:36.421 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.300
16:14:36.518 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.400
16:14:36.614 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.500
16:14:36.709 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.600
16:14:36.839 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.700
16:14:36.936 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.800
16:14:37.033 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:0.900
16:14:37.129 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.000
16:14:37.226 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.100
16:14:37.322 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.200
16:14:37.417 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.300
16:14:37.514 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.400
16:14:37.611 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.500
16:14:37.709 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.600
16:14:37.838 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.700
16:14:37.934 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.800
16:14:38.029 -> target_deg:0.000	position_deg:0.000	error_deg:0.000	p_deg_s:0.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:0.000	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:1.900
16:14:38.126 -> target_deg:90.000	position_deg:0.000	error_deg:90.000	p_deg_s:342.000	i_deg_s:0.000	d_deg_s:0.000	pid_deg_s:342.000	speed_deg_s:0.000	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.000
16:14:38.222 -> target_deg:90.000	position_deg:0.439	error_deg:89.561	p_deg_s:340.330	i_deg_s:0.000	d_deg_s:-1.031	pid_deg_s:339.300	speed_deg_s:6.870	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.100
16:14:38.318 -> target_deg:90.000	position_deg:1.582	error_deg:88.418	p_deg_s:335.988	i_deg_s:0.000	d_deg_s:-2.061	pid_deg_s:333.927	speed_deg_s:13.740	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.200
16:14:38.414 -> target_deg:90.000	position_deg:3.955	error_deg:86.045	p_deg_s:326.971	i_deg_s:0.000	d_deg_s:-3.710	pid_deg_s:323.261	speed_deg_s:24.732	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.300
16:14:38.511 -> target_deg:90.000	position_deg:7.383	error_deg:82.617	p_deg_s:313.945	i_deg_s:0.000	d_deg_s:-5.153	pid_deg_s:308.793	speed_deg_s:34.350	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.400
16:14:38.639 -> target_deg:90.000	position_deg:11.602	error_deg:78.398	p_deg_s:297.914	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:291.525	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.500
16:14:38.736 -> target_deg:90.000	position_deg:15.908	error_deg:74.092	p_deg_s:281.549	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:275.160	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.600
16:14:38.833 -> target_deg:90.000	position_deg:20.303	error_deg:69.697	p_deg_s:264.850	i_deg_s:0.000	d_deg_s:-6.595	pid_deg_s:258.254	speed_deg_s:43.968	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.700
16:14:38.930 -> target_deg:90.000	position_deg:24.785	error_deg:65.215	p_deg_s:247.816	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:241.427	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.800
16:14:39.028 -> target_deg:90.000	position_deg:29.092	error_deg:60.908	p_deg_s:231.451	i_deg_s:0.000	d_deg_s:-6.595	pid_deg_s:224.856	speed_deg_s:43.968	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:2.900
16:14:39.124 -> target_deg:90.000	position_deg:33.574	error_deg:56.426	p_deg_s:214.418	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:208.029	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.000
16:14:39.221 -> target_deg:90.000	position_deg:38.057	error_deg:51.943	p_deg_s:197.385	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:190.996	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.100
16:14:39.317 -> target_deg:90.000	position_deg:42.451	error_deg:47.549	p_deg_s:180.686	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:174.296	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.004	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.200
16:14:39.413 -> target_deg:90.000	position_deg:46.934	error_deg:43.066	p_deg_s:163.652	i_deg_s:0.000	d_deg_s:-6.595	pid_deg_s:157.057	speed_deg_s:43.968	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.300
16:14:39.509 -> target_deg:90.000	position_deg:51.240	error_deg:38.760	p_deg_s:147.287	i_deg_s:0.000	d_deg_s:-6.595	pid_deg_s:140.692	speed_deg_s:43.968	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.400
16:14:39.637 -> target_deg:90.000	position_deg:55.723	error_deg:34.277	p_deg_s:130.254	i_deg_s:0.000	d_deg_s:-6.595	pid_deg_s:123.659	speed_deg_s:43.968	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.500
16:14:39.736 -> target_deg:90.000	position_deg:60.205	error_deg:29.795	p_deg_s:113.221	i_deg_s:0.000	d_deg_s:-6.595	pid_deg_s:106.626	speed_deg_s:43.968	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.600
16:14:39.833 -> target_deg:90.000	position_deg:64.600	error_deg:25.400	p_deg_s:96.521	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:90.132	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.700
16:14:39.930 -> target_deg:90.000	position_deg:68.994	error_deg:21.006	p_deg_s:79.822	i_deg_s:0.000	d_deg_s:-6.595	pid_deg_s:73.227	speed_deg_s:43.968	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.800
16:14:40.026 -> target_deg:90.000	position_deg:73.652	error_deg:16.348	p_deg_s:62.121	i_deg_s:0.000	d_deg_s:-6.389	pid_deg_s:55.732	speed_deg_s:42.594	u_deg_s:43.968	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:3.900
16:14:40.124 -> target_deg:90.000	position_deg:78.047	error_deg:11.953	p_deg_s:45.422	i_deg_s:0.075	d_deg_s:-6.389	pid_deg_s:39.108	speed_deg_s:42.594	u_deg_s:38.472	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.000
16:14:40.220 -> target_deg:90.000	position_deg:82.090	error_deg:7.910	p_deg_s:30.059	i_deg_s:0.220	d_deg_s:-5.771	pid_deg_s:24.508	speed_deg_s:38.472	u_deg_s:24.732	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.100
16:14:40.317 -> target_deg:90.000	position_deg:85.166	error_deg:4.834	p_deg_s:18.369	i_deg_s:0.311	d_deg_s:-4.122	pid_deg_s:14.558	speed_deg_s:27.480	u_deg_s:15.114	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.200
16:14:40.414 -> target_deg:90.000	position_deg:87.275	error_deg:2.725	p_deg_s:10.354	i_deg_s:0.365	d_deg_s:-2.679	pid_deg_s:8.039	speed_deg_s:17.862	u_deg_s:8.244	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.300
16:14:40.513 -> target_deg:90.000	position_deg:88.242	error_deg:1.758	p_deg_s:6.680	i_deg_s:0.397	d_deg_s:-1.443	pid_deg_s:5.634	speed_deg_s:9.618	u_deg_s:5.496	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.400
16:14:40.609 -> target_deg:90.000	position_deg:88.682	error_deg:1.318	p_deg_s:5.010	i_deg_s:0.420	d_deg_s:-0.412	pid_deg_s:5.017	speed_deg_s:2.748	u_deg_s:5.496	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.500
16:14:40.738 -> target_deg:90.000	position_deg:89.209	error_deg:0.791	p_deg_s:3.006	i_deg_s:0.435	d_deg_s:-0.824	pid_deg_s:2.616	speed_deg_s:5.496	u_deg_s:2.748	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.600
16:14:40.835 -> target_deg:90.000	position_deg:89.473	error_deg:0.527	p_deg_s:2.004	i_deg_s:0.445	d_deg_s:-0.412	pid_deg_s:2.037	speed_deg_s:2.748	u_deg_s:1.374	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.700
16:14:40.930 -> target_deg:90.000	position_deg:89.648	error_deg:0.352	p_deg_s:1.336	i_deg_s:0.452	d_deg_s:-0.412	pid_deg_s:1.375	speed_deg_s:2.748	u_deg_s:1.374	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.800
16:14:41.029 -> target_deg:90.000	position_deg:89.736	error_deg:0.264	p_deg_s:1.002	i_deg_s:0.456	d_deg_s:0.000	pid_deg_s:1.458	speed_deg_s:0.000	u_deg_s:1.374	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:4.900
16:14:41.127 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.456	d_deg_s:0.000	pid_deg_s:0.456	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.000
16:14:41.224 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.456	d_deg_s:0.000	pid_deg_s:0.456	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.100
16:14:41.320 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.456	d_deg_s:0.000	pid_deg_s:0.456	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.200
16:14:41.417 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.456	d_deg_s:0.000	pid_deg_s:0.456	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.300
16:14:41.513 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.400
16:14:41.610 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.500
16:14:41.742 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.600
16:14:41.839 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.700
16:14:41.937 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.800
16:14:42.034 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:5.900
16:14:42.130 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.000
16:14:42.227 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.100
16:14:42.322 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.200
16:14:42.418 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.300
16:14:42.514 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.400
16:14:42.611 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.500
16:14:42.740 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.600
16:14:42.836 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.700
16:14:42.933 -> target_deg:90.000	position_deg:89.912	error_deg:0.088	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.800
16:14:43.030 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:6.900
16:14:43.127 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.000
16:14:43.224 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.100
16:14:43.321 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.200
16:14:43.417 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.300
16:14:43.514 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.400
16:14:43.611 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.500
16:14:43.739 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.600
16:14:43.835 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.700
16:14:43.931 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.800
16:14:44.027 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:7.900
16:14:44.125 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:8.000
16:14:44.220 -> target_deg:90.000	position_deg:89.912	error_deg:0.088	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.000	kp:3.8000	ki:0.1500	kd:0.1500	t_s:8.100
16:14:44.318 -> target_deg:90.000	position_deg:89.824	error_deg:0.176	p_deg_s:0.000	i_deg_s:0.457	d_deg_s:0.000	pid_deg_s:0.457	speed_deg_s:0.000	u_deg_s:0.000	v_limit_deg_s:45.000	dt_ms:10.001	kp:3.8000	ki:0.1500	kd:0.1500	t_s:8.200
16:14:44.382 -> STOP: user
```  
- 오차값의 제한(0.2)가 있어 비정상적인 게인값이 아닌 이상 완벽한 PID제어 불가. 최소 0.088, 0.176의 2틱 이하의 오차가 생김.

## 지그라-니콜스 튜닝법

### 개루프 반응 곡선법(제1방법)

- PID 제어 끄기: 비례, 적분, 미분 게인을 모두 0으로 두고 제어 출력을 열린 상태로.
- 스텝 입력 가하기: 모터에 일정한 크기의 속도나 전압 명령을 주고 로그 기록
- S자 곡선 분석: 출력된 시간별 위치 그래프에서 지연 시간 (L, 모터가 실제로 움직이기 시작할 때까지 걸린 시간), 시정수 / 반응 기울기 (T 또는 R, S자 곡선에서 가장 가파른 기울기 지점의 접선을 그렸을 때, 이 접선이 최종 목표값에 도달하는 데 걸리는 시간(T) 또는 단위 시간당 변화율(R = 최대 기울기))

- P 제어: $K_p = \frac{1}{R \cdot L}$
- PI 제어: $K_p = \frac{0.9}{R \cdot L}$, 적분 시간 $T_i = 3L$
- PID 제어: $K_p = \frac{1.2}{R \cdot L}$, 적분 시간 $T_i = 2L$, 미분 시간 $T_d = 0.5L$
- 다이나믹셀 같은 서보모터 환경에서는 모터가 끝까지 가속해버리거나 보호 모드에 걸릴 수 있어 실험 중 제어가 까다로움

### 지속 진동법(제2방법)
- 하드웨어 실험을 통해 얻은 데이터만으로 PID 게인을 계산
- I, D 게인은 0으로 고정
- 임계 게인 찾기($K_{u}$)
- 임계 주기 측정($T_{u}$)
 
|제어 방식|$K_{p}$ (비례)|$K_{i}$ (적분)|$K_{d}$ (미분)|
|-------|---------------|---------------|----------------|
|P 제어|$0.50 \times K_u$|-|-|
|PI 제어|$0.45 \times K_u$|$1.2 \times (K_p / T_u)$|-|
|PID 제어|$0.60 \times K_u$|$2.0 \times (K_p / T_u)$ |$0.125 \times K_u \times T_u$|
    -  25% 정도의 오버슈트를 허용하면서 가장 빠르게 목표치에 도달하도록 설계, 이후 D를 조금 더 키우거나 P를 낮추는 미세 조정을 거침

## 극점 배치법
- 전달함수를 사용하는 제어이론 기반의 기법
- 극점을 내가 원하는 위치에 강제로 배치
- 특성 방정식의 근이 극점, 근이 어디에 있느냐에 따라 모터의 성격이 결정

- 원하는 모터의 성격 정의
- 수식 매칭: 제어공학의 표준 2차 방정식 공식과 내 PID 시스템의 수식을 일대일 비교
  - 표준 식: $s^2 + 2\zeta\omega_n s + \omega_n^2 = 0$
  - 내 모터+PID 식: $s^2 + (\frac{b + K_d}{J})s + (\frac{K_p}{J}) = 0$ (J: 모터 관성, b: 기계 마찰)

- $K_p = J \cdot \omega_n^2$
- $K_d = 2\zeta\omega_n J - b$

- 수학적으로 가장 완벽하고 오버슈트 없는 깔끔한 응답

## 내부 모델 제어
- 제어기 내부에 실제 모터와 똑같이 생긴 가상 수학 모델을 하나 더 심어두고 제어
![내부 모델 제어](<내부 모델 제어.png>)
- $K_p = \frac{2\tau + \theta}{2(\lambda + \theta)}$
- $K_i = \frac{1}{\lambda + \theta}$