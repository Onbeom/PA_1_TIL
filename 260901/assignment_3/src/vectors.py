import numpy as np

def norm(v):
    """벡터의 크기를 계산"""
    return float(np.sqrt(np.sum(v ** 2)))

def det(a):
    n = len(a)
    
    if n == 1:
        return a[0][0]
    
    if n == 2:
        return a[0][0] * a[1][1] - a[0][1] * a[1][0]
    
    determinant = 0

    for col in range(n):
        sub_matrix = [row[:col] + row[col+1:] for row in A[1:]]
        sign = (-1) ** col
        determinant += sign * a[0][col] * det(sub_matrix)
    return determinant

def dot(a, b):
    """두 벡터의 내적을 계산"""
    return float(np.sum(a * b))

def _swap_rows(M, i, j):
    """M 행렬의 i행과 j행을 바꿉니다."""
    M[i], M[j] = M[j], M[i]

def _eliminate_row(M, target_row, pivot_row, col):
    """pivot_row를 이용하여 target_row의 col번째 원소를 0으로 소거합니다."""
    if abs(M[pivot_row][col]) < 1e-9:
        return
    factor = M[target_row][col] / M[pivot_row][col]
    for k in range(col, len(M[0])):
        M[target_row][k] -= factor * M[pivot_row][k]

def angle_between(a, b):
    """두 벡터 사이의 사이각(도)을 계산"""
    norm_a = norm(a)
    norm_b = norm(b)
    if norm_a == 0 or norm_b == 0:
        raise ValueError("영벡터는 사이각을 정의할 수 없습니다.")
    cos_theta = dot(a, b) / (norm_a * norm_b)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return float(np.degrees(np.arccos(cos_theta)))

def normalize(v):
    """벡터를 정규화, 영벡터 입력 시 영벡터를 반환"""
    if norm(v) == 0:
        return np.zeros_like(v, dtype=float)
    return v / norm(v)

def project(a, b):
    """벡터 a를 벡터 b 방향으로 투영"""
    norm_b = norm(b)
    if norm_b == 0:
        raise ValueError("영벡터 방향으로는 투영할 수 없습니다.")
    return (dot(a, b) / (norm_b ** 2)) * b

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

def cross(a, b):
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
    cross_prod = cross(v1, v2)
    return normalize(cross_prod)

def row_echelon(A):
    M = [list(map(float, row)) for row in A]
    rows = len(M)
    cols = len(M[0]) if rows > 0 else 0
    
    current_col = 0
    for r in range(rows):
        while current_col < cols:
            pivot_row = r
            for i in range(r + 1, rows):
                if abs(M[i][current_col]) > abs(M[pivot_row][current_col]):
                    pivot_row = i
            
            if abs(M[pivot_row][current_col]) >= 1e-9:
                _swap_rows(M, r, pivot_row)
                break
            current_col += 1
            
        if current_col == cols:
            break
            
        for i in range(r + 1, rows):
            _eliminate_row(M, i, r, current_col)
            
        current_col += 1
        
    return M

def rank(a):
    ref_M = row_echelon(A)
    
    rank_count = 0
    for row in ref_M:
        # 행의 모든 원소가 0이 아니라면 (살아남은 독립적인 행이라면) 카운트
        if not all(abs(val) < 1e-9 for val in row):
            rank_count += 1
            
    return rank_count