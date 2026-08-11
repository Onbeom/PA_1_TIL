#include <iostream>
#include <memory>

class Motor {
    private:
    std::string name;

    public:
    Motor(std::string motorName) : name(motorName) {
        std::cout << "[생성]" << name << "객체가 생성되었습니다." << std::endl;
    }

    ~Motor() {
        std::cout << "[소멸]" << name << "객체가 소멸되었습니다." << std::endl;
    }
};

void runSimulation() {
    std::cout << "시작" << std::endl;

    Motor m("스택 모터(m)");
    auto p = std::make_unique<Motor>("힙 모터(p)");

    std::cout << "function 종료" << std::endl;
}

int main() {
    runSimulation();
    std::cout << "main 종료" << std::endl;
    return 0;
}