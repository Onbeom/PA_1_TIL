#include <iostream>

int a, b;
char symbol;

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

int main() {
    std::cout << "계산에 사용할 첫 번째 숫자를 제시해주세요." << std::endl;
    std::cin >> a;
    std::cout << "계산에 사용할 연산 기호를 제시해주세요. 예) *, /, ^, +, -, ..." << std::endl;
    std::cin >> symbol;
    std::cout << "계산에 사용할 두 번째 숫자를 제시해주세요." << std::endl;
    std::cin >> b;
    std::cout << "Answer : ";
    if (symbol=='+') {
        std::cout << add();
    }
    else if (symbol=='-') {
        std::cout << sub();
    }
    else if (symbol=='*') {
        std::cout << mult();
    }
    else if (symbol=='/') {
        std::cout << div();
    }
    else if (symbol=='^') {
        std::cout << pow_ex();
    }
    else if (symbol=='%') {
        std::cout << fmod_ex();
    }
    else{
        std::cout << "적용불가능한 기호입니다. 다시 입력해주세요.";
    }
    std::cout << std::endl;
}