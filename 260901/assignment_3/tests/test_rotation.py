import numpy as np
import pytest
from src.rotation import rot_x, rot_y, rot_z, rodrigues, gram_schmidt
from src.vectors import dot_product, custom_cross

# 가상환경 채점 고정을 위한 고정 난수 시드 사용
rng = np.random.default_rng(42)

# ① 회전행렬의 열이 서로 직교하는 단위벡터인지 검증
def test_columns_orthonormal():
    rand_angle = rng.uniform(0, 2 * np.pi)
    R = rot_y(rand_angle)  # Y축 회전 행렬 샘플 테스트
    
    q1, q2, q3 = R[:, 0], R[:, 1], R[:, 2]
    
    # 열 벡터 간 상호 직교성 검증 (내적 = 0)
    assert np.isclose(dot_product(q1, q2), 0.0, atol=1e-15)
    assert np.isclose(dot_product(q2, q3), 0.0, atol=1e-15)
    assert np.isclose(dot_product(q3, q1), 0.0, atol=1e-15)
    
    # 열 벡터 각각의 크기가 1인지 단위벡터 검증 (자기 자신과의 내적 = 1)
    assert np.isclose(dot_product(q1, q1), 1.0, atol=1e-15)
    assert np.isclose(dot_product(q2, q2), 1.0, atol=1e-15)
    assert np.isclose(dot_product(q3, q3), 1.0, atol=1e-15)

# ② 행렬식이 정확히 1인지 검증
def test_determinant_is_one():
    rand_angle = rng.uniform(0, 2 * np.pi)
    R = rot_z(rand_angle)
    
    # 직접 구현한 스칼라 삼중적으로 행렬식 연산
    det_custom = dot_product(R[:, 0], custom_cross(R[:, 1], R[:, 2]))
    
    # [검산용 명시] np.linalg.det로 수치 일치 상태 교차 검증
    det_verification = np.linalg.det(R)
    
    assert np.isclose(det_custom, 1.0, atol=1e-15)
    assert np.isclose(det_custom, det_verification, atol=1e-15)

# ③ 역행렬이 전치행렬과 동일한지 검증 (R^T @ R = I)
def test_inverse_equals_transpose():
    rand_angle = rng.uniform(0, 2 * np.pi)
    axis = rng.uniform(-1.0, 1.0, 3)
    R = rodrigues(axis, rand_angle)  # 로드리게스 임의 축 행렬 샘플 테스트
    
    I_3 = np.eye(3)
    # R^T @ R 연산 결과가 단위 행렬인지 검증
    assert np.allclose(R.T @ R, I_3, atol=1e-15)

# ④ 재직교화(Gram-Schmidt) 결과가 완벽한 직교행렬이 되는지 검증
def test_gram_schmidt_restoration():
    rand_angle = rng.uniform(0, 2 * np.pi)
    R_clean = rot_x(rand_angle)
    
    # 일부러 수치적 오염(노이즈)을 가해 직교성을 무너뜨림
    R_broken = R_clean + 0.02
    
    # 복구 함수 작동
    R_fixed = gram_schmidt(R_broken)
    
    I_3 = np.eye(3)
    # 무너진 행렬이 재직교화 과정을 거쳐 다시 직교 행렬 조건을 완벽히 충족하는지 검증
    assert np.allclose(R_fixed.T @ R_fixed, I_3, atol=1e-15)