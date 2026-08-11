#pragma once
#include <vector>
#include <iostream>

class Sensor {
    public:
    virtual ~Sensor() {
        std::cout << "부모 소멸자 호출" << std::endl;
    }

    virtual std::vector<double> read() = 0;
};