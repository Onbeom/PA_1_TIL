260810 정리
===================================

```c++
#include <iostream> // <studio.h> 와 같은 표준 입출력 헤더 파일
#include <string> // iostream에 내장된 std라이브러리
#include <cmath> // 표준 수학 계산 라이브러리

    std::cout << // 문자 입력, printf와 동일
    std::cin >> // 변수 입력, 서식 문자열 %d, %c, 주소연산자 & 불필요
    std::endl // 줄바꿈, \n과 동일
    std::boolalpha // bool값 출력
    std::sqrt(a); // root(a)와 동일
    fmod // cmath의 부동소수점 나머지 연산함수
    int // 정수형
    float // 4바이트 실수형
    double // 8바이트 실수형
    bool // 1바이트 논리형
    char // 2바이트 문자형
    short // 2바이트 정수형
    long // 4바이트 정수형
    long long // 8바이트 정수형
    unsigned // 양수or0

    float number = 3.14f; // 3.14f의 f는 접미사로, 자료형 고정

    std::cout << "Robot State: " << (robotstate ? "Activate" : "Inactivate") << std::endl;
    // robot state의 bool값에 따라 출력값 변화

    --i // 전위 연산자, i--와는 다르게 Result_i값도 -1된 값


    int add() {
    return a+b;
}

    int sub() {
    return a-b;
}

    int mult() {
    return a*b;
}

    int div() {
    if (b == 0) {
        std::cout << "0으로 나눌 수 없습니다. ";
        return 0;
    }
    return a/b;
}

    int pow_ex() {
        int result = 1;
        for (int i = 0; i < b; ++i) {
            result *= a;
        }
    return result;
}

    int fmod_ex() {
        if (b == 0) {
            std::cout << "0으로 나눌 수 없습니다. ";
            return 0;
        }
    return a%b;
}
```