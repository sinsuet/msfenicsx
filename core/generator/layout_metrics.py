"""Derived layout-quality metrics for generated cases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import hypot
from typing import Any

from shapely.geometry import Point

from core.geometry.layout_rules import component_polygon


@dataclass(slots=True, frozen=True)
class LayoutQualityMetrics:
    component_count: int
    component_area_ratio: float
    active_deck_occupancy: float
    bbox_fill_ratio: float
    nearest_neighbor_gap_mean: float
    centroid_dispersion: float
    largest_dense_core_void_ratio: float


LAYOUT_METRIC_KEYS = (
    "component_area_ratio",
    "active_deck_occupancy",
    "bbox_fill_ratio",
    "nearest_neighbor_gap_mean",
    "centroid_dispersion",
    "largest_dense_core_void_ratio",
)


def build_layout_context(
    *,
    placement_region: Mapping[str, float],
    active_deck: Mapping[str, float] | None,
    dense_core: Mapping[str, float] | None,
) -> dict[str, dict[str, float]]:
    context = {"placement_region": _coerce_region(placement_region)}
    if active_deck is not None:
        context["active_deck"] = _coerce_region(active_deck)
    if dense_core is not None:
        context["dense_core"] = _coerce_region(dense_core)
    return context


def measure_case_layout_metrics(
    case_payload: Mapping[str, Any],
    *,
    layout_context: Mapping[str, Any],
) -> dict[str, float] | None:
    components = case_payload.get("components")
    if not isinstance(components, list):
        return None
    placement_region = _optional_region(layout_context.get("placement_region"))
    if placement_region is None:
        return None
    metrics = measure_layout_quality(
        {"components": components},
        placement_region=placement_region,
        active_deck=_optional_region(layout_context.get("active_deck")),
        dense_core=_optional_region(layout_context.get("dense_core")),
    )
    return layout_metrics_to_dict(metrics)


def layout_metrics_to_dict(metrics: LayoutQualityMetrics) -> dict[str, float]:
    return {key: float(getattr(metrics, key)) for key in LAYOUT_METRIC_KEYS}


def measure_layout_quality(
    case_payload: dict[str, Any],
    *,
    placement_region: dict[str, float],
    active_deck: dict[str, float] | None = None,
    dense_core: dict[str, float] | None = None,
) -> LayoutQualityMetrics:
    components = list(case_payload.get("components", []))
    polygons = [component_polygon(component) for component in components]
    component_count = len(polygons)
    if not polygons:
        return LayoutQualityMetrics(
            component_count=0,
            component_area_ratio=0.0,
            active_deck_occupancy=0.0,
            bbox_fill_ratio=0.0,
            nearest_neighbor_gap_mean=0.0,
            centroid_dispersion=0.0,
            largest_dense_core_void_ratio=0.0,
        )

    placement_area = _rect_area(placement_region)
    active_deck_area = placement_area if active_deck is None else _rect_area(active_deck)
    total_area = sum(float(polygon.area) for polygon in polygons)
    min_x = min(float(polygon.bounds[0]) for polygon in polygons)
    min_y = min(float(polygon.bounds[1]) for polygon in polygons)
    max_x = max(float(polygon.bounds[2]) for polygon in polygons)
    max_y = max(float(polygon.bounds[3]) for polygon in polygons)
    bbox_area = max(0.0, (max_x - min_x) * (max_y - min_y))
    centroids = [polygon.centroid.coords[0] for polygon in polygons]
    centroid_x = sum(float(x) for x, _ in centroids) / float(component_count)
    centroid_y = sum(float(y) for _, y in centroids) / float(component_count)
    centroid_dispersion = sum(
        hypot(float(x) - centroid_x, float(y) - centroid_y) for x, y in centroids
    ) / float(component_count)

    nearest_neighbor_gap_mean = 0.0
    if component_count > 1:
        nearest_neighbor_gap_mean = sum(
            min(float(polygon.distance(other)) for other_index, other in enumerate(polygons) if other_index != index)
            for index, polygon in enumerate(polygons)
        ) / float(component_count)
    void_region = dense_core or active_deck or placement_region
    largest_dense_core_void_ratio = _largest_empty_patch_ratio(polygons, void_region)

    return LayoutQualityMetrics(
        component_count=component_count,
        component_area_ratio=total_area / placement_area if placement_area > 0.0 else 0.0,
        active_deck_occupancy=total_area / active_deck_area if active_deck_area > 0.0 else 0.0,
        bbox_fill_ratio=total_area / bbox_area if bbox_area > 0.0 else 0.0,
        nearest_neighbor_gap_mean=nearest_neighbor_gap_mean,
        centroid_dispersion=centroid_dispersion,
        largest_dense_core_void_ratio=largest_dense_core_void_ratio,
    )


def _rect_area(region: dict[str, float]) -> float:
    return max(0.0, float(region["x_max"]) - float(region["x_min"])) * max(
        0.0,
        float(region["y_max"]) - float(region["y_min"]),
    )


def _largest_empty_patch_ratio(
    polygons: list[Any],
    region: dict[str, float],
    *,
    rows: int = 18,
    cols: int = 24,
) -> float:
    if not polygons:
        return 0.0
    region_min_x = float(region["x_min"])
    region_max_x = float(region["x_max"])
    region_min_y = float(region["y_min"])
    region_max_y = float(region["y_max"])
    bbox_min_x = max(region_min_x, min(float(polygon.bounds[0]) for polygon in polygons))
    bbox_min_y = max(region_min_y, min(float(polygon.bounds[1]) for polygon in polygons))
    bbox_max_x = min(region_max_x, max(float(polygon.bounds[2]) for polygon in polygons))
    bbox_max_y = min(region_max_y, max(float(polygon.bounds[3]) for polygon in polygons))
    width = bbox_max_x - bbox_min_x
    height = bbox_max_y - bbox_min_y
    if width <= 0.0 or height <= 0.0:
        return 0.0

    occupied = [[False for _ in range(cols)] for _ in range(rows)]
    for row_index in range(rows):
        y_value = bbox_min_y + (row_index + 0.5) * height / float(rows)
        for col_index in range(cols):
            x_value = bbox_min_x + (col_index + 0.5) * width / float(cols)
            point = Point(x_value, y_value)
            occupied[row_index][col_index] = any(polygon.covers(point) for polygon in polygons)

    visited = [[False for _ in range(cols)] for _ in range(rows)]
    largest_patch = 0
    total_cells = rows * cols
    for row_index in range(rows):
        for col_index in range(cols):
            if occupied[row_index][col_index] or visited[row_index][col_index]:
                continue
            patch_size = 0
            queue = [(row_index, col_index)]
            visited[row_index][col_index] = True
            while queue:
                current_row, current_col = queue.pop()
                patch_size += 1
                for next_row, next_col in (
                    (current_row - 1, current_col),
                    (current_row + 1, current_col),
                    (current_row, current_col - 1),
                    (current_row, current_col + 1),
                ):
                    if next_row < 0 or next_row >= rows or next_col < 0 or next_col >= cols:
                        continue
                    if occupied[next_row][next_col] or visited[next_row][next_col]:
                        continue
                    visited[next_row][next_col] = True
                    queue.append((next_row, next_col))
            largest_patch = max(largest_patch, patch_size)
    return float(largest_patch) / float(total_cells)


def _coerce_region(region: Mapping[str, Any]) -> dict[str, float]:
    coerced = _optional_region(region)
    if coerced is None:
        raise ValueError("layout regions must define numeric x_min/x_max/y_min/y_max values.")
    return coerced


def _optional_region(region: Any) -> dict[str, float] | None:
    if not isinstance(region, Mapping):
        return None
    keys = ("x_min", "x_max", "y_min", "y_max")
    if any(key not in region for key in keys):
        return None
    try:
        return {key: float(region[key]) for key in keys}
    except (TypeError, ValueError):
        return None
