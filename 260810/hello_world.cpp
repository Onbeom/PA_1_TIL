#include <iostream>
#include <string>

int main() {
    std::cout << "Hello, World!" << std::endl;
    
    short count = 10;
    int speed = 100;
    long distance = -1000000;
    unsigned int age = 25;

    std::cout << "Count: " << count << std::endl;
    std::cout << "Speed: " << speed << std::endl;
    std::cout << "Distance: " << distance << std::endl;
    std::cout << "Age: " << age << std::endl << std::endl;

    float number = 3.14f;
    double largeNumber = 2.718281828459045;

    std::cout << "number: " << number << std::endl;
    std::cout << "largeNumber " << largeNumber << std::endl<< std::endl;

    bool robotstate = true;
    char sensor = 'T';
    std::string message = "Hello, World!";

    std::cout << "Robot State: " << (robotstate ? "Activate" : "Inactivate") << std::endl;
    std::cout << "Sensor Type: " << sensor << std::endl;
    std::cout << "Message: " << message << std::endl << std::endl;

    int reading[5] = {10, 20, 30, 40, 50};
    std::cout << "Sensor readings: " << reading[0] << ", " 
    << reading[1] << ", " 
    << reading[2] << ", " 
    << reading[3] << ", "
    << reading[4] << std::endl;

    double readings[5] = {10, 20, 30, 40, 5.00000001};
    std::cout << "readings[4] size is: " << sizeof(readings[4]) << std::endl << std::endl;

    double batteryVoltage = 12.0;
    bool lidar_isOK = true, imu_isOK = true;
    std::cout << "battery < 50 = " << std::boolalpha << (batteryVoltage >= 50) << std::endl;
    std::cout << "robot State : " << (lidar_isOK || imu_isOK ? "OK": "Not OK") <<std::endl << std::endl;

    int batteryLevel = 100;
    std::cout << "batteryLevel: if / elseif else (battery = 100)";
    if (batteryLevel==100) {
        std::cout << "Battery is fully charged." << std::endl;
    }
    else if (batteryLevel >= 50) {
        std::cout << "Battery is more than half charged." << std::endl;
    }
    else if (batteryLevel > 0) {
        std::cout << "Battery is low." << std::endl;
    }
    else{
        std::cout << "Battery is empty." << std::endl;
    }
    
    


    return 0;
}