"""LiDAR 스캔 전처리 및 위험 판정 유틸리티.

가상의 360° LiDAR 스캔을 1차원 거리 배열로 받아
유효 측정 필터링, 최근접 장애물 탐지, 극좌표→직교좌표 변환,
전방 위험 구간 판정 기능을 제공한다.
"""
from __future__ import annotations

import numpy as np

RANGE_MIN: float = 0.1   # 유효 측정의 최소 거리 [m]
RANGE_MAX: float = 10.0  # 유효 측정의 최대 거리 [m]


def filter_valid(scan: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """센서 사양(RANGE_MIN~RANGE_MAX)을 벗어난 측정을 걸러낸다.

    - mask: 유효 측정이 True 인 불리언 배열
    - valid: 유효 측정의 거리만 남긴 1차원 배열
    - ratio: 전체 대비 유효 측정 비율 (0~1)

    >>> rng = np.random.default_rng(0)
    >>> scan = rng.random(360) * 12
    >>> mask, valid, ratio = filter_valid(scan)
    >>> valid.shape
    (247,)
    """
    mask = (scan > RANGE_MIN) & (scan < RANGE_MAX)
    valid = scan[mask]
    ratio = float(mask.mean())
    return mask, valid, ratio


def nearest_obstacle(
    scan: np.ndarray, angles: np.ndarray, mask: np.ndarray | None = None
) -> tuple[float, float]:
    """유효 측정 중 가장 가까운 장애물의 거리[m]와 각도[deg]를 반환한다.

    mask가 없을 경우 스캔 전체에서 최근장을 찾는다.
    """
    if mask is None:
        mask = (scan > RANGE_MIN) & (scan < RANGE_MAX)
    valid = scan[mask]
    ang_valid = angles[mask]
    idx = np.argmin(valid)
    return float(valid[idx]), float(np.degrees(ang_valid[idx]))


def polar_to_xy(scan: np.ndarray, angles: np.ndarray) -> np.ndarray:
    """유효 측정 전체를 로봇 중심 직교좌표 (N, 2)로 변환한다. 반복문 금지.

    각 행은 [x, y]이며, x = r·cos(θ), y = r·sin(θ)로 계산된다.
    """
    mask = (scan > RANGE_MIN) & (scan < RANGE_MAX)
    r = scan[mask]
    a = angles[mask]
    return np.column_stack([r * np.cos(a), r * np.sin(a)])


def detect_front_danger(
    valid: np.ndarray,
    ang_valid: np.ndarray,
    front_half_angle: float = np.pi / 6,
    danger_dist: float = 1.5,
) -> tuple[np.ndarray, np.ndarray, bool]:
    """로봇 전방 ±front_half_angle 안, danger_dist 이내 장애물을 판정한다.

    - front: 각도가 전방 구간인 곳이 True인 마스크
    - danger: 전방이면서 위험 거리 이내인 곳이 True인 마스크
    - stop: 위험이 하나라도 있으면 True(파이썬 bool)
    """
    front = (ang_valid < front_half_angle) | (
        ang_valid > 2 * np.pi - front_half_angle
    )
    danger = front & (valid < danger_dist)
    return front, danger, bool(danger.any())


def loop_filter(scan: np.ndarray) -> np.ndarray:
    """for 문 버전의 유효 측정 필터(속도 비교용). 벡터화 버전은 필요한 배열식이다."""
    out = []
    for i in range(len(scan)):
        if RANGE_MIN < scan[i] < RANGE_MAX:
            out.append(scan[i])
    return np.asarray(out)