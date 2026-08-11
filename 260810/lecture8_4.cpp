#include <iostream>
#include <algorithm>

namespace ex{
    template <typename T>
    T clamp(T value, T lo, T hi) {        // 어떤 타입 T든 동작
        return std::max(lo, std::min(value, hi));
    }
}

int main() {
    std::cout << "--- 1. double 타입 적용 (로봇/드론 속도 상한 제어) ---" << std::endl;
    double speed = 1.8;
    double min_speed = 0;
    double max_speed = 1.0;

    double limited_speed = ex::clamp<double>(speed, min_speed, max_speed);
    std::cout << "원래 속도: " << speed << " m/s" << std::endl;
    std::cout << "제한된 속도: " << limited_speed << " m/s (속도 상한선 1.0에 걸림)" << std::endl;

    std::cout << "--- 2. int 타입 적용 (이미지 픽셀값 제어) ---" << std::endl;
    int raw_pixel_1 = 150;
    int raw_pixel_2 = 300; // 255를 초과하는 잘못된 값 가정
    int min_pixel = 0;
    int max_pixel = 255;

     // 컴파일러의 자동 타입 추론을 활용한 호출 ( <int> 생략 )
    int valid_pixel_1 = ex::clamp(raw_pixel_1, min_pixel, max_pixel);
    int valid_pixel_2 = ex::clamp(raw_pixel_2, min_pixel, max_pixel);

    std::cout << "픽셀값 1 (원래 150) -> 결과: " << valid_pixel_1 << " (범위 내 안전)" << std::endl;
    std::cout << "픽셀값 2 (원래 300) -> 결과: " << valid_pixel_2 << " (최대치 255로 제한)" << std::endl;

    return 0;
}