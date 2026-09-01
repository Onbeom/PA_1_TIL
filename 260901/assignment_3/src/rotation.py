import numpy as np
from src.vectors import skew, dot_product, normalize

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

    q1=normalize(v1)

    proj_v2_q1 = dot_product(v2,q1) * q1
    q2 = normalize(v2-proj_v2_q1)

    proj_v3_q1 = dot_product(v3,q1) * q1
    proj_v3_q2 = dot_product(v3,q2) * q2
    q3=normalize(v3 - proj_v3_q1 - proj_v3_q2)

    return np.column_stack((q1,q2,q3))