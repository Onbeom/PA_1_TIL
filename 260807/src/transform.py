"""2차원 회전 변환 유틸리티.

점군(각 행이 [x, y])을 2×2 회전행렬로 돌린다.
행 벡터 관례에 따라 `xy @ R.T`로 곱한다.
"""
from __future__ import annotations

import numpy as np


def rotation_matrix(theta: float) -> np.ndarray:
    """2D 회전행렬을 만든다.

    - theta: 회전 각도 [rad]
    - 반환: shape (2, 2) 행렬 [[cos, -sin], [sin, cos]]

    >>> R = rotation_matrix(np.radians(45))
    >>> np.round(R, 4)
    array([[ 0.7071, -0.7071],
           [ 0.7071,  0.7071]])
    """
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def rotate_points(xy: np.ndarray, theta: float) -> np.ndarray:
    """점군 xy(각 행이 [x, y])를 theta[rad]만큼 z축 회전시킨다."""
    return xy @ rotation_matrix(theta).T


def distances_unchanged(xy: np.ndarray, theta: float, tol: float = 1e-9) -> bool:
    """회전이 원점까지 거리를 보존하는지 확인한다."""
    d0 = np.linalg.norm(xy, axis=1)
    d1 = np.linalg.norm(rotate_points(xy, theta), axis=1)
    return bool(np.allclose(d0, d1, atol=tol))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
