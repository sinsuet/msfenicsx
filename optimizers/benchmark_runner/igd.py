"""IGD helpers for 2D minimization comparison contexts."""

from __future__ import annotations

import math
from collections.abc import Sequence

from optimizers.analytics.pareto import pareto_front_indices


Point = tuple[float, float]


def empirical_reference_front(points: Sequence[Point]) -> list[Point]:
    ordered = [(float(x), float(y)) for x, y in points]
    indices = pareto_front_indices(ordered)
    return sorted((ordered[index] for index in indices), key=lambda point: (point[0], point[1]))


def igd_2d(candidate_points: Sequence[Point], reference_points: Sequence[Point]) -> float | None:
    if not candidate_points or not reference_points:
        return None
    normalized_candidates, normalized_reference = _normalize_together(candidate_points, reference_points)
    distances = [
        min(_euclidean(ref, candidate) for candidate in normalized_candidates)
        for ref in normalized_reference
    ]
    return float(sum(distances) / len(distances))


def _normalize_together(candidate_points: Sequence[Point], reference_points: Sequence[Point]) -> tuple[list[Point], list[Point]]:
    all_points = [(float(x), float(y)) for x, y in list(candidate_points) + list(reference_points)]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    span_x = max(max_x - min_x, 1.0e-12)
    span_y = max(max_y - min_y, 1.0e-12)

    def normalize(points: Sequence[Point]) -> list[Point]:
        return [((float(x) - min_x) / span_x, (float(y) - min_y) / span_y) for x, y in points]

    return normalize(candidate_points), normalize(reference_points)


def _euclidean(left: Point, right: Point) -> float:
    return math.sqrt((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2)
