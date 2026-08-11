#include <iostream>
#include <memory>
#include <string>

class Motor {
private:
    std::string name;

public:
    Motor(std::string motorName) : name(motorName) {
        // 루프 실행 시 출력이 너무 많아지므로 주석 처리하거나 지워도 좋습니다.
        // std::cout << "[생성]" << name << "객체가 생성되었습니다." << std::endl;
    }

    ~Motor() {
        std::cout << "[소멸]" << name << "객체가 소멸되었습니다." << std::endl;
    }
};

int main() {
    std::cout << "--- 메모리 누수 실험 시작 (new 사용) ---\n";

    // delete 없이 new를 반복 호출하여 누수 발생
    for (int i = 0; i < 5; ++i) {
        Motor* leak_motor = new Motor("누수 모터 " + std::to_string(i));
        // 의도적으로 delete leak_motor; 를 수행하지 않음
    }

    std::cout << "main 종료 (소멸자가 전혀 호출되지 않음)\n";

    std::cout << "--- 메모리 안전성 실험 시작 (make_unique 사용) ---\n";

    // 루프가 반복될 때마다 중괄호 {}를 벗어나며 수명이 다한 unique_ptr가 자동으로 delete 수행
    for (int i = 0; i < 5; ++i) {
        auto safe_motor = std::make_unique<Motor>("안전 모터 " + std::to_string(i));
    } // <- 여기서 safe_motor가 스택에서 사라지면서 힙의 Motor 객체 소멸자 강제 호출

    std::cout << "main 종료 (모든 스마트 포인터 해제 완료)\n";

    return 0;
}