# CH 2 - 1강

## 개루프 제어 vs 폐루프 제어

![개루프 제어 vs 폐루프 제어](<개루프 제어 vs 폐루프 제어.png>)

|구분|개루프|폐루프|
|---|-----|----|
|센서|불필요 → 저렴·단순|필요 → 비용·복잡도 증가|
|외란|대응	불가 — 오차가 그대로 남음|자동 보정|
|모델|오차 대응	불가 — 모델이 틀리면 결과도 틀림|자동 보정|
|안정성 문제|없음 (시스템 자체가 안정하면)|잘못 설계하면 발진·불안정 (2강)|

## 1차 시스템(전달함수)

- $J\frac{d\omega}{dt} + b\,\omega = K\,v(t)$
  - $J$는 회전 관성, $b$는 마찰 계수, $K$는 토크 상수
- $(Js + b)\,\Omega(s) = K\,V(s) \quad\Rightarrow\quad G(s) = \frac{\Omega(s)}{V(s)} = \frac{K}{Js + b}$
  - 라플라스 변환
- $G(s)$ — 입력의 라플라스 변환 대비 출력의 라플라스 변환의 비 = 전달함수

## 시정수 $τ$

- G(s) = \frac{K}{\tau s + 1}
  - $K$: 정상상태 이득 : 입력 1을 오래 유지했을 때 출력이 최종적으로 도달하는 값
  - $\tau$: 시정수(time constant) : 반응의 "빠르기"를 나타내는 시간 단위 값
- 입력을 0에서 1로 갑자기 올리는 계단 입력 : $y(t) = K\left(1 - e^{-t/\tau}\right)$

![계단 입력](<계단 입력.png>)

## 2차 시스템(오버슈트와 정착시간)

- $G(s) = \frac{\omega_n^2}{s^2 + 2\zeta\omega_n s + \omega_n^2}$
  - $\omega_n$: 고유 진동수 : 진동의 빠르기
  - $\zeta$(제타): 감쇠비 : 진동이 얼마나 빨리 잦아드는가

![감쇠비에 따른 계단 응답](<감쇠비에 따른 계단 응답.png>)

## 계단 응답 성능

![계단 응답 성능](<계단 응답 성능.png>)

### 제어의 트레이드오프

- 빠르게 만들수록 많이 출렁, 얌전하게 만들수록 느림
- 상승시간과 오버슈트는 반비례 관계

### Python code

```python
import numpy as np
import matplotlib.pyplot as plt

t = np.linspace(0, 10, 500)
tau = 1.0
y1 = 1 - np.exp(-t / tau)                       # 1차 계단 응답

wn, zeta = 2.0, 0.3                              # 2차: 감쇠 진동
wd = wn * np.sqrt(1 - zeta**2)
y2 = 1 - np.exp(-zeta*wn*t) * (np.cos(wd*t) + zeta*wn/wd*np.sin(wd*t))

plt.plot(t, y1, label='1st order (tau=1)')
plt.plot(t, y2, label='2nd order (zeta=0.3)')
plt.axhline(1, color='gray', ls='--'); plt.legend(); plt.xlabel('t [s]')
```

