# YOLO 배포 엔진 E3로 교체

> 작업일 2026-11-05, 정리일 2026-11-18. 출처: `~/git/lv2_next_module` 작업 세션 기록(개인일지·트러블슈팅·보고서)
> 팀 과제 [Lv2_Cartlidar_Assignment](https://github.com/developlcy-oss/Lv2_Cartlidar_Assignment) (#번호 = PR·Issue). 맡은 영역: 인지 (YOLO)
> [모의] = 시뮬레이션·재생·계산, [실물] = 실제 로봇·Jetson

## 한 일
- 배포 엔진 E2 → E3 (앞·뒤 480, 팔 384, FP16): 엔진 경로·설정을 바꾸고 재확인 (#120)
- 팔 Arducam을 1280×720으로 받도록 요청 (#118, #119)

## 배운 점
- 모델 교체는 가중치 파일만 바꾸는 일이 아님 → 엔진 경로·입력 크기·설정을 함께 바꾸고 같은 판정으로 다시 확인
