260811 정리
=========================
## 8장
```c++
#include <algorithm>  
//정렬 및 최대값, 최소값 도출, 벡터의 주소 삽입 등이 있는 헤더파일
sort(begin(),end());

#include <memory>  
//스마트 포인터를 포함한 헤더파일
std::unique_ptr
std::shared_ptr
std::weak_ptr

#include <vector>  
//템플릿 형태로 배열을 커스터마이징 할 수 있는 헤더파일

std::vector
using namespace std;

#include <random>

randomValues(count, low, high)
```
>std::unique_ptr (독점 소유)  
>>개념: 객체를 딱 하나의 포인터만 가질 수 있습니다.  
>>특징: 복사(Copy)가 불가능하며, 오직 소유권 이전(Move)만 가능합니다.  
>>생성법: std::make_unique<T>()를 사용합니다.  
>>용도: 포인터의 수명이 명확하고, 다른 곳과 공유할 필요가 없는 대부분의 일반적인 상황에 씁니다. (기본 선택) [1, 2, 3, 4, 5]

>std::shared_ptr (공유 소유)  
>>개념: 하나의 객체를 여러 개의 포인터가 공동으로 가질 수 있습니다.  
>>특징: 내부적으로 참조 횟수(Reference Count)를 세어, 포인터가 모두 사라져 카운트가 0이 될 때 자동으로 메모리를 해제합니다.  
>>생성법: std::make_shared<T>()를 사용합니다.  
>>용도: 여러 클래스나 함수에서 하나의 데이터 객체를 동시 관리하고 수명을 예측하기 어려울 때 씁니다. [1, 2, 3, 4]

>std::weak_ptr (참조만 수행)  
>>개념: std::shared_ptr가 가리키는 객체를 관찰하지만, 소유권은 갖지 않는 포인터입니다.  
>>특징: 객체를 가리켜도 참조 횟수가 늘어나지 않으므로, 메모리 해제에 영향을 주지 않습니다.  
>>용도: 두 객체가 서로를 shared_ptr로 가리켜 메모리가 영원히 해제되지 않는 순환 참조(Circular Reference) 문제를 해결할 때 씁니다. [1, 2, 3, 4]

![스마트 포인터](image-1.png)

## 9장

>발행 : 송신  
>구독 : 수신

[nods & topic](image.png)

>노드 : 하나의 일을 하는 프로그램  
>토픽 : 이름 붙은 메시지 흐름으로 노드를 연결
>>Ex) camera_node가 /image 토픽에 영상을 발행(publish) 하면, perception_node가 그것을 구독(subscribe) 해 받습니다. 인지 결과는 다시 /obstacles 토픽으로 제어에 전달

>같은 토픽을 구독하는 노드가 여럿이여도 발행자는 모름.  
>노드는 독립 프로세스.  
>언어, 위치가 무관함.
>>Ex) C++,Python, 다른 컴퓨터의 노드와도 통신

|용어|의미|비유|
|---|-------|---|
|노드|하나의 일을 하는 실행 단위(프로세스)|부서|
|토픽|이름 붙은 단방향 메시지 흐름|사내 공지 채널|
|메시지|토픽으로 오가는 데이터의 형식|정해진 양식의 문서|
|발행/구독|토픽에 쓰기 / 토픽에서 읽기|게시 / 구독|

```shell
ros2 node list           # 실행 중인 노드 목록
ros2 topic list          # 토픽 목록
ros2 topic echo /scan    # 토픽에 흐르는 메시지 실시간 출력
ros2 topic hz /scan      # 발행 주파수 측정 (2강의 주기!)
rqt_graph                # 그래프를 시각적으로 표시
```
> 콜백 :  이벤트 구동 방식
>>구독 콜백: 구독 중인 토픽에 메시지가 도착하면 실행  
(예: `/scan`이 오면 장애물 계산)  
>>타이머 콜백: 정해진 주기마다 실행  
(예: 20ms마다 제어 명령 발행)  
>>서비스 콜백: 다른 노드가 요청을 보내면 실행

```c++
class PerceptionNode(Node):      # 5강의 상속!
    def __init__(self):
        super().__init__('perception_node')
        # "/scan이 오면 self.on_scan을 불러라"
        self.sub = self.create_subscription(LaserScan, '/scan', self.on_scan, 10)
        # "/obstacles로 발행할 통로를 연다"
        self.pub = self.create_publisher(Obstacles, '/obstacles', 10)
        # "50ms마다 self.on_timer를 불러라"
        self.timer = self.create_timer(0.05, self.on_timer)

    def on_scan(self, msg):      # 구독 콜백
        self.latest_scan = msg   # 받아서 저장만 (빠르게!)

    def on_timer(self):          # 타이머 콜백
        result = detect_obstacles(self.latest_scan)
        self.pub.publish(result) # 결과 발행
```