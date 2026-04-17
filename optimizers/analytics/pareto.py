"""Pareto filtering and exact 2D hypervolume (minimization)."""

from __future__ import annotations

from collections.abc import Sequence


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
