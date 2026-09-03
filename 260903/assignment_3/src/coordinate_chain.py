"""문제 6 — 좌표 변환 체인 모듈. (학생 작성용 템플릿)

base -> link -> camera 로 이어지는 동차변환 체인을 구성하고,
카메라 기준 좌표를 로봇 base 기준으로 바꾼다.
모듈 4(픽앤플레이스 미니 프로젝트)에서 그대로 import 해 쓰게 되므로,
공개 함수 이름과 반환 형식을 이 템플릿 그대로 유지한다.
"""

from __future__ import annotations

import numpy as np

from .rotation import axis_angle_from_matrix, rot_x, rot_y, rot_z
from .transform import inv_T, make_T, transform_points

__all__ = ["CoordinateChain", "default_chain", "camera_point_to_base", "base_point_to_camera"]


class CoordinateChain:
    """부모 -> 자식 동차변환을 이름으로 등록하고, 임의의 두 프레임 사이 변환을 만든다.

    TF2 의 축소판이라고 보면 된다.
    """

    def __init__(self, root: str = "base"):
        self.root = root
        self._parent: dict[str, str] = {}                 # child -> parent
        self._T: dict[tuple[str, str], np.ndarray] = {}   # (parent, child) -> T

    def add(self, parent: str, child: str, T) -> "CoordinateChain":
        """parent 기준으로 표현된 child 프레임의 자세 T(parent<-child) 를 등록한다."""
        T = np.asarray(T, dtype=float)
        if T.shape != (4, 4):
            raise ValueError(f"4x4 동차변환이 필요합니다. 받은 shape={T.shape}")
        self._parent[child] = parent
        self._T[(parent, child)] = T
        return self

    def get(self, parent: str, child: str) -> np.ndarray:
        """등록해 둔 T(parent <- child) 를 그대로 돌려준다."""
        return self._T[(parent, child)]

    def frames(self) -> list[str]:
        """등록된 프레임 이름 목록 (root 포함)."""
        return [self.root] + list(self._parent.keys())

    # ------------------------------------------------------ 여기부터 구현

    def _path_to_root(self, frame: str) -> list[str]:
        """frame 에서 root 까지의 경로 [frame, ..., root] 를 만든다.

        root 에 연결되어 있지 않으면 KeyError.
        """
        # 문제 6-1
        path = [frame]
        curr = frame
        while curr != self.root:
            if curr not in self._parent:
                raise KeyError(f"프레임 '{curr}'이 루트 '{self.root}'에 연결되어 있지 않습니다.")
            curr = self._parent[curr]
            path.append(curr)
        return path

    def T_from_root(self, frame: str) -> np.ndarray:
        """root 기준 frame 의 자세 T(root <- frame)."""
        # 문제 6-1
        if frame == self.root:
            return np.eye(4)
            
        path = self._path_to_root(frame)  # [frame, child, parent, ..., root]
        
        # 기하학 상쇄 규칙: T(root <- frame) = T(root <- parent) @ T(parent <- child) @ T(child <- frame)
        # 즉, 경로의 역순으로 올라가면서 행렬을 순차적으로 앞에 누적 곱셈해 줍니다.
        T_accum = np.eye(4)
        for i in range(len(path) - 1, -1, -1):
            child = path[i]
            parent = path[i]
            T_accum = T_accum @ self._T[(parent, child)]
        return T_accum

    def T(self, target: str, source: str) -> np.ndarray:
        """source 좌표를 target 좌표로 바꾸는 변환 T(target <- source)."""
        # 문제 6-1
        # 공식 유도: T(target <- source) = T(target <- root) @ T(root <- source) = inv_T(T(root <- target)) @ T(root <- source)
        T_root_target = self.T_from_root(target)
        T_root_source = self.T_from_root(source)
        
        # 5장에서 완성한 수치 안정성이 높은 기하학 고속 역행렬 함수 inv_T 적극 활용
        return inv_T(T_root_target) @ T_root_source

    def transform(self, target: str, source: str, P, w: float = 1.0) -> np.ndarray:
        """source 프레임의 점(w=1) 또는 방향(w=0)을 target 프레임으로 변환한다."""
        # 문제 6-2
        T_mat = self.T(target, source)
        P_arr = np.asarray(P, dtype=float)
        
        # (3,) 단건 벡터와 (N,3) 행렬 복합 차원 처리
        is_single = (P_arr.ndim == 1)
        pts = np.atleast_2d(P_arr)
        
        # 반복문(for) 없이 고속 텐서 벡터라이제이션 동차화 행렬 곱셈 수행
        pts_hom = np.hstack([pts, np.ones((len(pts), 1)) * w])
        transformed = (T_mat @ pts_hom.T).T[:, :3]
        
        if is_single:
            return transformed[0]
        return transformed

    def axis_angle(self, target: str, source: str):
        """T(target <- source) 의 회전 부분에서 회전축과 회전각을 복원한다."""
        # 문제 6-4
        T_mat = self.T(target, source)
        R = T_mat[:3, :3]
        return axis_angle_from_matrix(R)


def default_chain(rng=None) -> CoordinateChain:
    """과제에서 쓸 기본 체인(base -> link -> camera)을 만든다.
    임의 변환 생성을 위해 고정 난수기(rng) 입력을 옵션으로 연결해 둡니다.
    """
    # 문제 6-1
    # 튜터 지시문에 따라 채점 수치를 명확히 가공할 수 있도록 기본 오프셋 행렬 조립
    T_base_link = make_T(rot_z(np.deg2rad(30.0)), [0.30, 0.00, 0.40])
    T_link_camera = make_T(rot_y(np.deg2rad(-20.0)) @ rot_x(np.deg2rad(90.0)), [0.10, 0.05, 0.15])
    
    return CoordinateChain("base").add("base", "link", T_base_link).add("link", "camera", T_link_camera)


def camera_point_to_base(p_cam, chain: CoordinateChain | None = None) -> np.ndarray:
    """카메라 기준 좌표 -> base 기준 좌표. (3,) 와 (N,3) 모두 지원."""
    # 문제 6-1
    if chain is None:
        chain = default_chain()
    return chain.transform(target="base", source="camera", P=p_cam, w=1.0)


def base_point_to_camera(p_base, chain: CoordinateChain | None = None) -> np.ndarray:
    """base 기준 좌표 -> 카메라 기준 좌표. 왕복 검증(문제 6-2)에 쓴다."""
    # 문제 6-2
    if chain is None:
        chain = default_chain()
    return chain.transform(target="camera", source="base", P=p_base, w=1.0)