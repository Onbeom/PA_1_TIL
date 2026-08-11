"""KANT PA 6강(LiDAR 스캔) 예제 전체 실행 파일.

src/ 의 모듈을 활용해 360° 가상 스캔을 생성하고
전처리 → 최근접 장애물 → 직교좌표 변환 → 전방 위험 판정 → 회전 검증 순으로
전체 파이프라인을 실행해 결과를 출력한다.

사용법:
    python main.py               # 결과 출력(+ 시각화 이미지 저장)
    python main.py --no-plot     # 시각화 없이 텍스트 결과만 출력
"""
from __future__ import annotations

import argparse
import os

import numpy as np

import src.grader as grader
import src.lidar as lidar
import src.transform as transform

N_BEAMS: int = 360
SEED: int = 0
PLOT_PATH: str = os.path.join(os.path.dirname(__file__), "lidar_result.png")


def load_scan() -> tuple[np.ndarray, np.ndarray]:
    """시드를 고정한 가상 360° 스캔을 만들어 거리[m]와 각도[rad]를 반환한다."""
    rng = np.random.default_rng(SEED)
    scan = rng.random(N_BEAMS) * 12
    angles = np.linspace(0, 2 * np.pi, N_BEAMS)
    return scan, angles


def main() -> None:
    parser = argparse.ArgumentParser(description="LiDAR 스캔 예제 실행")
    parser.add_argument(
        "--plot",
        action="store_true",
        default=True,
        help="전방 위험 구간 시각화 이미지를 저장한다.",
    )
    parser.add_argument("--no-plot", dest="plot", action="store_false", help="텍스트 결과만 출력")
    args = parser.parse_args()

    scan, angles = load_scan()
    mask, valid, ratio = lidar.filter_valid(scan)

    print("=== 1. 유효 측정 필터링 ===")
    print(f"  유효 측정 {valid.shape[0]}개 / 비율 {ratio:.3f}")

    near_dist, near_deg = lidar.nearest_obstacle(scan, angles)
    print("\n=== 2. 최근접 장애물 ===")
    print(f"  최단 {near_dist:.3f} m @ {near_deg:.1f} deg")

    xy = lidar.polar_to_xy(scan, angles)
    print("\n=== 3. 극좌표 → 직교좌표 ===")
    print(f"  xy shape {xy.shape}, 앞 3행:\n{np.round(xy[:3], 3)}")

    ang_valid = angles[mask]
    front, danger, stop = lidar.detect_front_danger(valid, ang_valid)
    print("\n=== 4. 전방 위험 판정 ===")
    print(f"  전방 위험 측정 {int(danger.sum())}개 -> {'정지' if stop else '주행'}")

    xy_rot = transform.rotate_points(xy, np.radians(45))
    max_diff = np.abs(np.linalg.norm(xy, axis=1) - np.linalg.norm(xy_rot, axis=1)).max()
    print("\n=== 6. 회전은 길이를 바꾸지 않는다 ===")
    print(f"  회전 전후 거리 최대 차이 {max_diff:.2e}")

    looped = lidar.loop_filter(scan)
    print("\n=== 7. 벡터화 vs 반복문 필터 일치 ===")
    print(f"  결과 일치: {np.array_equal(looped, scan[mask])}")

    if args.plot:
        _plot(valid, ang_valid, danger)
        print(f"\n시각화 저장: {PLOT_PATH}")


def _plot(valid: np.ndarray, angles: np.ndarray, danger: np.ndarray) -> None:
    """유효 측정/위험 구간/로봇 위치를 그려 PNG로 저장한다."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = valid * np.cos(angles)
    y = valid * np.sin(angles)
    danger_xy = np.column_stack([x, y])[danger]

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(x, y, label="valid", color="gray")
    ax.scatter(danger_xy[:, 0], danger_xy[:, 1], label="danger", color="red")
    ax.plot(0, 0, marker="^", markersize=10, label="robot")
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.legend()
    fig.savefig(PLOT_PATH, dpi=100, bbox_inches="tight")


if __name__ == "__main__":
    main()