#pragma once
#include "Sensor.h"

class IMU : public Sensor {
public:
    IMU() { 
        std::cout << "Imu 생성\n"; 
    }
    
    ~IMU() override { 
        std::cout << "~Imu() 자식 소멸자 호출 (메모리 해제)\n"; 
    }

    std::vector<double> read() override {
        return {0.1, -0.2, 9.8};
    }
};