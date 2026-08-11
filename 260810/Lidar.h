#pragma once
#include "Sensor.h"

class Lidar : public Sensor {
public:
    Lidar() { 
        std::cout << "Lidar 생성\n"; 
    }
    
    ~Lidar() override { 
        std::cout << "~Lidar() 자식 소멸자 호출 (메모리 해제)\n"; 
    }

    std::vector<double> read() override {
        return {0.8, 0.82, 0.85};
    }
};