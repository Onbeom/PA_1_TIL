#include <iostream>
#include <vector>
#include <memory>

#include "Lidar.h"
#include "IMU.h"

int main() {
    std::vector<std::unique_ptr<Sensor>> sensors;
    
    sensors.push_back(std::make_unique<Lidar>());
    sensors.push_back(std::make_unique<IMU>());

    for (const auto& sensor : sensors) {
        std::vector<double> data = sensor->read();
        for (double val : data) {
            std::cout << val << " ";
        }
        std::cout << "\n";
    }
    return 0;
}