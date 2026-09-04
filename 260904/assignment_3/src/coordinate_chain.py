"""문제 6 — 좌표 변환 체인 모듈. (완성본)

base -> link -> camera 로 이어지는 동차변환 체인을 구성하고,
카메라 기준 좌표를 로봇 base 기준으로 바꾼다.
모듈 4(픽앤플레이스 미니 프로젝트)에서 그대로 import 해 쓰게 되므로,
공개 함수 이름과 반환 형식을 이 템플릿 그대로 유지한다.
"""

from __future__ import annotations

import numpy as np

from src.rotation import axis_angle_from_matrix, rot_x, rot_y, rot_z
from src.transform import inv_T, make_T, transform_points

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

    def _path_to_root(self, frame: str) -> list[str]:
        """frame 에서 root 까지의 경로 [frame, ..., root] 를 만든다.

        root 에 연결되어 있지 않으면 KeyError.
        """
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
        if frame == self.root:
            return np.eye(4)
            
        path = self._path_to_root(frame)  # [frame, parent_of_frame, ..., root]
        
        # 상쇄 규칙에 따라 root에서 출발하여 frame까지 내려오며 행렬을 순차적으로 곱함
        T_accum = np.eye(4)
        for i in range(len(path) - 2, -1, -1):
            parent = path[i + 1]
            child = path[i]
            T_accum = T_accum @ self._T[(parent, child)]
        return T_accum

    def T(self, target: str, source: str) -> np.ndarray:
        """source 좌표를 target 좌표로 바꾸는 변환 T(target <- source)."""
        T_root_target = self.T_from_root(target)
        T_root_source = self.T_from_root(source)
        
        # 기하학적 역행렬 함수 inv_T 활용: T(target <- source) = inv(T_root_target) @ T_root_source
        return inv_T(T_root_target) @ T_root_source

    def transform(self, target: str, source: str, P, w: float = 1.0) -> np.ndarray:
        """source 프레임의 점(w=1) 또는 방향(w=0)을 target 프레임으로 변환한다."""
        T_mat = self.T(target, source)
        P_arr = np.asarray(P, dtype=float)
        
        is_single = (P_arr.ndim == 1)
        pts = np.atleast_2d(P_arr)
        
        # 반복문 없이 고속 벡터라이제이션 연산 (w 값 반영)
        pts_hom = np.hstack([pts, np.ones((len(pts), 1)) * w])
        transformed = (T_mat @ pts_hom.T).T[:, :3]
        
        if is_single:
            return transformed[0]
        return transformed

    def axis_angle(self, target: str, source: str):
        """T(target <- source) 의 회전 부분에서 회전축과 회전각을 복원한다."""
        T_mat = self.T(target, source)
        R = T_mat[:3, :3]
        return axis_angle_from_matrix(R)


def default_chain(rng=None) -> CoordinateChain:
    """과제에서 쓸 기본 체인(base -> link -> camera)을 만든다."""
    # 각도 단위: 라디안 변환 처리 (회전 함수 내부가 라디안을 받으므로 np.radians 사용)
    T_base_link = make_T(rot_z(np.radians(30.0)), [0.30, 0.00, 0.40])
    T_link_camera = make_T(rot_y(np.radians(-20.0)) @ rot_x(np.radians(90.0)), [0.10, 0.05, 0.15])
    
    return CoordinateChain("base").add("base", "link", T_base_link).add("link", "camera", T_link_camera)


def camera_point_to_base(p_cam, chain: CoordinateChain | None = None) -> np.ndarray:
    """카메라 기준 좌표 -> base 기준 좌표. (3,) 와 (N,3) 모두 지원."""
    if chain is None:
        chain = default_chain()
    return chain.transform(target="base", source="camera", P=p_cam, w=1.0)


def base_point_to_camera(p_base, chain: CoordinateChain | None = None) -> np.ndarray:
    """base 기준 좌표 -> 카메라 기준 좌표. 왕복 검증(문제 6-2)에 쓴다."""
    if chain is None:
        chain = default_chain()
    return chain.transform(target="camera", source="base", P=p_base, w=1.0)
