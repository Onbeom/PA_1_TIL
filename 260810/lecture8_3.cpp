#include <iostream>
#include <vector>
#include <unordered_map>
#include <algorithm>

int main() {
    std::vector<double> scan = {0.3, 8.2, 0.5, 12.0};
    scan.push_back(1.1);                    // 끝에 추가
    
    std::unordered_map < std::string, double > sensors;   // dict 대응, 조회 O(1)
    
    sensors["battery"]=11.9;
    sensors["lidar+front"]=0.5;
    sensors["liadr_rear"]=1.2;
    
    if(sensors.count("battery")) { /* 존재 확인 */ 
        std::cout <<  "[센서 확인] 배터리 전압: " << sensors["battery"] << "V" << std::endl;
    }
    double closest = *std::min_element(scan.begin(), scan.end());  // 최솟값
    std::cout << "[분석] 가장 가까운 물체 거리: " << closest << "m\n";
    
    // 범위 기반 for + 람다 (Python 컴프리헨션 느낌)
    int near_count = std::count_if(scan.begin(), scan.end(), [](double d){
        return d < 1.0;
    });
    
    std::cout << "[결과] 1m 이내에 탐지된 물체 개수: " << near_count << "개\n";

    return 0;
}