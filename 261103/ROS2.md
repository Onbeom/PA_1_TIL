# 위치 추정 패키지와 장소 상자 인식

> 작업일 2026-11-03, 정리일 2026-11-18. 출처: `~/git/lv2_next_module` 작업 세션 기록(개인일지·트러블슈팅·보고서)
> 팀 과제 [Lv2_Cartlidar_Assignment](https://github.com/developlcy-oss/Lv2_Cartlidar_Assignment) (#번호 = PR·Issue). 맡은 영역: 위치 추정 · 인지
> [모의] = 시뮬레이션·재생·계산, [실물] = 실제 로봇·Jetson

## 한 일
- 팀 `localization` 패키지 작성: loc_monitor(위치 추정 상태 감시) · 지도 · AMCL 입력 (#91)
  - 모의 비교에서는 Cartographer가 더 정확했지만(RMSE 0.0072~0.0081m vs 최적화 AMCL 0.0154~0.0162m) **팀 요청으로 AMCL 기본**, Cartographer는 인자로 남김
- 팔 카메라로 장소 상자 윗면의 중심·방향·칸 9개 찾기 (place_box)
- YOLO 후보 D 설정
- 다른 담당에 Issue 요청: place_box 사용(#73), D435 노출 고정(#89), EKF 보정(#92), 위치 잠금(#93)

## 배운 점
- 고르는 규칙(예: RMSE 차 ≥ 0.005m면 작은 쪽)을 **실행 전에** 정해 두면 결과가 팀 결정과 달라도 근거가 남음
- 위치 추정 노드와 별개로 "지금 위치를 믿어도 되나"를 알려 주는 감시 노드가 필요 → 미션·주행이 이 상태를 보고 멈춤
- AMCL 기본 개념은 [261015](../261015/ROS2.md#3-amcl--저장-지도에서-위치-추정)
