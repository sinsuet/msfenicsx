"""Pareto filtering and exact 2D hypervolume (minimization)."""

from __future__ import annotations

from collections.abc import Sequence

DEFAULT_REFERENCE_POINT = (400.0, 20.0)


def pareto_front_indices(objectives: Sequence[tuple[float, float]]) -> list[int]:
    """Return indices of non-dominated points under minimization."""
    result: list[int] = []
    for i, (a1, a2) in enumerate(objectives):
        dominated = False
        for j, (b1, b2) in enumerate(objectives):
            if i == j:
                continue
            if b1 <= a1 and b2 <= a2 and (b1 < a1 or b2 < a2):
                dominated = True
                break
        if not dominated:
            result.append(i)
    return result


def hypervolume_2d(
    points: Sequence[tuple[float, float]],
    *,
    reference_point: tuple[float, float],
) -> float:
    """Exact 2D hypervolume under minimization against `reference_point`."""
    idx = pareto_front_indices(list(points))
    front = sorted((points[i] for i in idx), key=lambda p: p[0])
    ref_x, ref_y = reference_point
    hv = 0.0
    prev_x = ref_x
    for x, y in reversed(front):
        # height from this point's y up to the reference y.
        height = ref_y - y
        width = prev_x - x
        if width > 0 and height > 0:
            hv += width * height
        prev_x = x
    return hv


def adaptive_reference_point_2d(
    points: Sequence[tuple[float, float]],
    *,
    default_reference_point: tuple[float, float] = DEFAULT_REFERENCE_POINT,
    margin_fraction: float = 0.05,
    minimum_margin: float = 1.0,
) -> tuple[float, float]:
    """Return a reference point that dominates all observed minimization points."""
    if not points:
        return default_reference_point
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)
    x_margin = max(float(minimum_margin), float(x_range * margin_fraction))
    y_margin = max(float(minimum_margin), float(y_range * margin_fraction))
    return (
        max(float(default_reference_point[0]), max(xs) + x_margin),
        max(float(default_reference_point[1]), max(ys) + y_margin),
    )
