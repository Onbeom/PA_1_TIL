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


def axis_angle_from_matrix(R):
    """3x3 회전행렬 R로부터 유일하게 정의되는 회전축(단위벡터)과 회전각(라디안, [0, pi])을 복원합니다."""
    R = np.asarray(R, dtype=float)
    
    # 1. 대각합을 이용한 cos(theta) 계산 및 클리핑 (부동소수점 오차 방지)
    cos_theta = (np.trace(R) - 1.0) / 2.0
    cos_theta = max(-1.0, min(1.0, cos_theta))
    theta = np.arccos(cos_theta)
    
    # 예외 처리 1: theta = 0 (회전이 없는 경우)
    if np.isclose(theta, 0.0, atol=1e-8):
        return np.array([1.0, 0.0, 0.0]), 0.0
        
    # 예외 처리 2: theta = pi (180도 회전인 경우, sin(theta)가 0이 되어 나눗셈 불가)
    if np.isclose(theta, np.pi, atol=1e-8):
        # R = 2 * k * k^T - I 성질 이용
        diag = np.diagonal(R)
        k_sq = (diag + 1.0) / 2.0
        k_sq = np.maximum(k_sq, 0.0) # 음수 방지
        k = np.sqrt(k_sq)
        
        # 부호 결정 (R의 비대각 성분 활용)
        if R[0, 1] < 0: k[1] = -k[1]
        if R[0, 2] < 0: k[2] = -k[2]
        if k[1] * k[2] * R[1, 2] < 0: k[2] = -k[2]
        
        return k / np.linalg.norm(k), np.pi

    # 일반적인 경우 (0 < theta < pi): R - R^T의 비대각 성분으로 방향 부호 정밀 동기화
    axis = np.array([
        R[2, 1] - R[1, 2],
        R[0, 2] - R[2, 0],
        R[1, 0] - R[0, 1]
    ], dtype=float)
    
    return axis / np.linalg.norm(axis), theta

def quaternion_from_axis_angle(axis, angle):
    """회전축 axis(단위벡터)와 회전각 angle(라디안)로단위 쿼터니언 [x, y, z, w] 형식을 생성합니다."""
    axis = np.asarray(axis, dtype=float)
    norm = np.linalg.norm(axis)
    if np.isclose(norm, 0.0):
        return np.array([0.0, 0.0, 0.0, 1.0])
        
    u = axis / norm
    sin_half = np.sin(angle / 2.0)
    cos_half = np.cos(angle / 2.0)
    
    return np.array([u[0] * sin_half, u[1] * sin_half, u[2] * sin_half, cos_half], dtype=float)