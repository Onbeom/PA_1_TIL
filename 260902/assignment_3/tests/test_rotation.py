import pytest
import numpy as np
from src.rotation import rot_x, rot_y, rot_z, gram_schmidt, orthogonality_error, is_rotation
from src.vectors import det

rng = np.random.default_rng(42)
random_angles = rng.uniform(0, 2 * np.pi, size=3).tolist()
angles_case = [0.0, np.pi/4, np.pi/2,] + random_angles

@pytest.mark.parametrize("angle", angles_case)
@pytest.mark.parametrize("rot_func", [rot_x, rot_y, rot_z])
def test_columns_are_orthonormal(angle, rot_func):
    """① 회전행렬의 열이 서로 직교하는 단위벡터인지 검증"""
    R = rot_func(angle)
    assert np.isclose(orthogonality_error(R), 0.0, atol=1e-12)

@pytest.mark.parametrize("angle", angles_case)
@pytest.mark.parametrize("rot_func", [rot_x, rot_y, rot_z])
def test_determinant_is_one(angle, rot_func):
    """② 행렬식이 +1 인지 검증"""
    R = rot_func(angle)
    assert np.isclose(det(R), 1.0, atol=1e-12)

@pytest.mark.parametrize("angle", angles_case)
@pytest.mark.parametrize("rot_func", [rot_x, rot_y, rot_z])
def test_inverse_equals_transpose(angle, rot_func):
    """③ 역행렬이 전치와 같은지 검증"""
    R = rot_func(angle)
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-12)

def test_gram_schmidt_restores_orthogonality():
    """④ 무너진 행렬을 재직교화한 결과가 완전한 직교행렬이 되는지 검증"""
    rng_gs = np.random.default_rng(42)
    bad_R = rot_z(0.5) + rng_gs.uniform(-0.01, 0.01, size=(3, 3))
    fixed_R = gram_schmidt(bad_R)
    assert is_rotation(fixed_R)