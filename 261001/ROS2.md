# 17강
## K, 렌즈 왜곡

### 정규화 좌표
- 카메라 특성이 반영되기 전 순수 3D 방향 비율
  - $u = f_x \times X \div Z + C_x$
  - $v = f_y \times Y \div Z + C_y$
- 카메라 내장 파라미터(고유값 k)
  - 렌즈 초점거리
  - 이미지 중심점

> $$ k = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix} (단위 : pixel)$$
> 2차원 동차변환행렬

## 투영, 역투영

- $Z_{Depth} \not= ||카메라 원점, 물체||$
- $Z = 1.2 m, u = 380, C_x = 320, f_x = 600 -> X = (u − C_x) \times Z \div f_x = 0.12 m$