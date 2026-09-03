import numpy as np
from src.vectors import dot
from src.rotation import is_rotation

def make_T(R, t):
    """3x3 회전행렬 R과 3차원 평행이동 벡터 t를 결합하여 4x4 동차변환 행렬 T를 생성합니다."""
    if not is_rotation(R):
        raise ValueError("입력된 3x3 행렬이 올바른 회전 행렬(SO(3))이 아닙니다.")
        
    T = np.eye(4, dtype=float)
    T[:3, :3] = R
    T[:3, 3] = np.array(t).flatten()
    return T

def inv_T(T):
    """일반 역행렬 함수를 사용하지 않고, 
    동차변환 행렬의 기하학적 성질(R^T, -R^T @ t)을 이용하여 고속으로 역변환 행렬을 구합니다.
    """
    R = T[:3, :3]
    t = T[:3, 3]
    
    R_inv = R.T  # 직교행렬인 회전행렬의 성질(R^-1 = R^T) 이용
    t_inv = -R_inv @ t  # 역평행이동 성분 계산
    
    # 내부적으로 이미 검증된 R_inv이므로 정석 결합
    T_inv = np.eye(4, dtype=float)
    T_inv[:3, :3] = R_inv
    T_inv[:3, 3] = t_inv
    return T_inv

def to_homogeneous(v, w=1.0):
    """3차원 벡터 v를 동차좌표계(w) 벡터로 변환합니다.
    w=1이면 점(Point), w=0이면 방향/변위 벡터(Direction)를 의미합니다.
    """
    return np.append(v, w)

def transform_point(T, p):
    """동차변환 행렬 T를 이용하여 3차원 공간 상의 '점 p (w=1)'를 변환합니다."""
    p_hom = to_homogeneous(p, w=1.0)
    return (T @ p_hom)[:3]

def transform_direction(T, d):
    """동차변환 행렬 T를 이용하여 3차원 공간 상의 '방향 벡터 d (w=0)'를 변환합니다."""
    d_hom = to_homogeneous(d, w=0.0)
    return (T @ d_hom)[:3]

def transform_points(T, points):
    """여러 개의 3차원 점들이 담긴 배열(N x 3)을 동차변환 행렬 T로 일괄 변환합니다."""
    points_hom = np.hstack([points, np.ones((len(points), 1))])
    return (T @ points_hom.T).T[:, :3]

def inv_T_batch(T_batch):
    """여러 개의 동차변환 행렬이 쌓인 3차원 배열(N x 4 x 4)을 일괄 역변환합니다."""
    N = T_batch.shape[0]
    T_inv_batch = np.zeros_like(T_batch)
    T_inv_batch[:, 3, 3] = 1.0
    
    R_batch = T_batch[:, :3, :3]
    R_inv_batch = np.transpose(R_batch, axes=(0, 2, 1))  # 축 교환 전치 수행
    T_inv_batch[:, :3, :3] = R_inv_batch
    
    t_batch = T_batch[:, :3, 3:4]
    t_inv_batch = -R_inv_batch @ t_batch
    T_inv_batch[:, :3, 3] = t_inv_batch.squeeze(-1)
    
    return T_inv_batch

def least_squares_normal_equation(A, b):
    """과결정 시스템 Ax = b를 정규방정식 (A^T A) x = A^T b 로 최적해 x를 반환합니다."""
    ATA = A.T @ A
    ATb = A.T @ b
    return np.linalg.solve(ATA, ATb)

def rmse(y_true, y_pred):
    """실제 값과 예측 값 사이의 평균 제곱근 오차(RMSE)를 계산합니다."""
    return np.sqrt(np.mean((y_true - y_pred) ** 2))