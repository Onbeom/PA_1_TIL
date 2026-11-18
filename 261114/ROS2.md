# TFmini 중복 실행과 실물 미로 지도

> 작업일 2026-11-14, 정리일 2026-11-18. 출처: `~/git/lv2_next_module` 작업 세션 기록(개인일지·트러블슈팅·보고서)
> 팀 과제 [Lv2_Cartlidar_Assignment](https://github.com/developlcy-oss/Lv2_Cartlidar_Assignment) (#번호 = PR·Issue). 맡은 영역: 인지 · 위치 추정 (실물)
> [모의] = 시뮬레이션·재생·계산, [실물] = 실제 로봇·Jetson

## 한 일
- TFmini 노드가 두 번 뜨는 문제 고침 (#280)
- 실물 미로 bag을 Cartographer(c6 설정)로 처리해 발제 SDF 지도와 비교
  - 기준(계산 전에 정함): 실물 벽 → SDF 5cm 안 ≥ 70%, SDF 벽 → 실물 5cm 안 ≥ 70%
  - 결과 29% · 17%로 기준 미달 (겹벽)
- Issue 공유: Jetson 컨트롤러 spawner가 첫 bringup 9번 중 6번 실패 (#275), 팔 카메라 렌즈가 설계보다 약 20mm 낮음 (#278) 등 (#275~#279)

## 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| tfmini_node가 두 번 뜸 | bringup의 `use_tfmini` 인자가 포함된 인지 launch로 그대로 넘어감 | 단독 실행 인자를 `standalone_tfmini`로 분리 |

## 배운 점
- launch를 include하면 같은 이름의 인자가 안쪽까지 전달됨 → 역할이 다른 인자는 이름을 나눔
- 지도 품질은 눈으로 보지 말고 정답 지도와의 거리 기준을 미리 정해 판정 ([261014](../261014/ROS2.md) Cartographer 비교와 같은 방식)
