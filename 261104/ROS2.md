# Jetson에서 돌게 맞추기 — loc_monitor 막힘과 YOLO 엔진

> 작업일 2026-11-04, 정리일 2026-11-18. 출처: `~/git/lv2_next_module` 작업 세션 기록(개인일지·트러블슈팅·보고서)
> 팀 과제 [Lv2_Cartlidar_Assignment](https://github.com/developlcy-oss/Lv2_Cartlidar_Assignment) (#번호 = PR·Issue). 맡은 영역: 위치 추정 · 인지 (Jetson)
> [모의] = 시뮬레이션·재생·계산, [실물] = 실제 로봇·Jetson

## 한 일
- loc_monitor가 Jetson에서 검사를 모두 멈춘 문제 고침 (#102)
- YOLO TensorRT 엔진을 카메라별로 분리: 앞·뒤 D435는 입력 480, 팔은 384, FP16
- 배포 엔진 D → E2, 팔 YOLO 박스로 목표 잠금 (이날 PR #95 · #96 · #97 · #100 · #102 · #103)
- [실물, 녹화 재생] 카메라 3대 + YOLO + AMCL·loc_monitor 30분 × 5판: CPU 평균 44.0%, GPU 50.2%, YOLO 15Hz

## 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| Jetson에서 loc_monitor 검사가 모두 멈춤 | 콜백 안에서 TF를 기다림 → 코어가 적은 Jetson에서 실행기가 막힘 | 콜백에서 TF를 기다리지 않게 바꿈 (CPU 47 → 33%) |

## 배운 점
- ROS 2 콜백 안에서 블로킹 대기(TF `lookup` timeout 등)를 하면 같은 실행기의 다른 콜백까지 멈춤 → PC에선 안 보이고 Jetson에서 드러남
- TensorRT 엔진은 입력 크기·정밀도별로 따로 빌드 → 카메라마다 엔진을 나눔 ([261102](../261102/ROS2.md))
