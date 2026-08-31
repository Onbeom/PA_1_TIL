import numpy as np

def custom_norm(v):
    """벡터의 크기를 계산"""
    return float(np.sqrt(np.sum(v ** 2)))

def dot_product(a, b):
    """두 벡터의 내적을 계산"""
    return float(np.sum(a * b))

def angle_between(a, b):
    """두 벡터 사이의 사이각(도)을 계산"""
    norm_a = custom_norm(a)
    norm_b = custom_norm(b)
    if norm_a == 0 or norm_b == 0:
        raise ValueError("영벡터는 사이각을 정의할 수 없습니다.")
    cos_theta = dot_product(a, b) / (norm_a * norm_b)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return float(np.degrees(np.arccos(cos_theta)))

def normalize(v):
    """벡터를 정규화, 영벡터 입력 시 영벡터를 반환"""
    norm = custom_norm(v)
    if norm == 0:
        return np.zeros_like(v, dtype=float)
    return v / norm

def project(a, b):
    """벡터 a를 벡터 b 방향으로 투영"""
    norm_b = custom_norm(b)
    if norm_b == 0:
        raise ValueError("영벡터 방향으로는 투영할 수 없습니다.")
    return (dot_product(a, b) / (norm_b ** 2)) * b

def reject(a, b):
    """벡터 a에서 벡터 b 방향 성분을 제거한 수직 성분을 반환"""
    return a - project(a, b)

def skew(a):
    """3차원 벡터 a에 대한 반대칭행렬"""
    if len(a) != 3:
        raise ValueError("skew 행렬은 3차원 벡터에 대해서만 정의됩니다.")
    return np.array([
        [0.0, -a[2], a[1]],
        [a[2], 0.0, -a[0]],
        [-a[1], a[0], 0.0]
    ], dtype=float)

def custom_cross(a, b):
    """3차원 벡터의 외적을 직접 계산"""
    if len(a) != 3 or len(b) != 3:
        raise ValueError("외적은 3차원 벡터에 대해서만 정의됩니다.")
    return np.array([
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    ], dtype=float)

def plane_normal(p1, p2, p3):
    """세 점으로 이루어진 평면의 단위 법선 벡터"""
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p3) - np.array(p1)
    cross_prod = custom_cross(v1, v2)
    return normalize(cross_prod)