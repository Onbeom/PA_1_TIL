import numpy as np
from src.vectors import skew, dot, normalize, det

def rot_x(theta):
    """X축 기준 회전 행렬 생성(각도 단위: 라디안)"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([
        [1.0, 0.0, 0.0],
        [0.0, c,  -s],
        [0.0, s,   c]
    ], dtype=float)

def rot_y(theta):
    """Y축 기준 회전 행렬 생성(각도 단위: 라디안)"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([
        [ c, 0.0,  s],
        [0.0, 1.0, 0.0],
        [-s, 0.0,  c]
    ], dtype=float)

def rot_z(theta):
    """Z축 기준 회전 행렬 생성(각도 단위: 라디안)"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([
        [c, -s, 0.0],
        [s,  c, 0.0],
        [0.0, 0.0, 1.0]
    ], dtype=float)

def rodrigues(axis, theta):
    """로드리게스 회전 공식을 이용하여 임의의 축 기준 회전 행렬을 생성"""
    axis = np.array(axis, dtype=float)
    norm = np.sqrt(np.sum(axis**2))
    
    if np.isclose(norm, 0.0):
        return np.eye(3)
        
    u = axis / norm
    K = skew(u)
    I = np.eye(3)
    
    # R = I + sin(theta)*K + (1 - cos(theta))*K^2s
    return I + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)

def gram_schmidt(R):
    """Gram-Schmidt 과정을 이용하여 3x3 행렬의 직교성을 복구"""

    v1=R[:,0]
    v2=R[:,1]
    v3=R[:,2]

    q1 = normalize(v1)
    if np.allclose(q1, 0.0):
        raise ValueError("선형 종속인 열이 존재합니다.")

    v2_orthogonal = v2 - dot(v2,q1) * q1
    q2 = normalize(v2_orthogonal)
    if np.allclose(q2, 0.0):
        raise ValueError("선형 종속인 열이 존재합니다.")

    v3_orthogonal = v3 - dot(v3,q1) * q1 - dot(v3, q2) * q2
    q3 = normalize(v3_orthogonal)
    if np.allclose(q3, 0.0):
        raise ValueError("선형 종속인 열이 존재합니다.")

    return np.column_stack((q1,q2,q3))

def orthogonality_error(R) -> float:
    """|R^T @ R - I|의 최대 절댓값"""
    I = np.eye(R.shape[0])
    diff = R.T @ R-I
    return float(np.sqrt(np.sum(diff ** 2)))

def is_rotation(R, atol: float = 1e-9) -> bool:
    """행렬 R이 올바른 회전 행렬인지 검증합니다"""
    if R.shape != (3,3):
        return False
    if orthogonality_error(R) > atol:
        return False
    if not np.isclose(det(R), 1.0, atol=atol):
        return False
    R_reortho = gram_schmidt(R)
    if not np.allclose(R, R_reortho, atol=atol):
        return False
    return True