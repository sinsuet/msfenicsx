"""Derived layout-quality metrics for generated cases."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any

from core.geometry.layout_rules import component_polygon


@dataclass(slots=True, frozen=True)
class LayoutQualityMetrics:
    component_count: int
    component_area_ratio: float
    bbox_fill_ratio: float
    nearest_neighbor_gap_mean: float
    centroid_dispersion: float


def measure_layout_quality(
    case_payload: dict[str, Any],
    *,
    placement_region: dict[str, float],
) -> LayoutQualityMetrics:
    components = list(case_payload.get("components", []))
    polygons = [component_polygon(component) for component in components]
    component_count = len(polygons)
    if not polygons:
        return LayoutQualityMetrics(
            component_count=0,
            component_area_ratio=0.0,
            bbox_fill_ratio=0.0,
            nearest_neighbor_gap_mean=0.0,
            centroid_dispersion=0.0,
        )

    placement_area = _rect_area(placement_region)
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

    return LayoutQualityMetrics(
        component_count=component_count,
        component_area_ratio=total_area / placement_area if placement_area > 0.0 else 0.0,
        bbox_fill_ratio=total_area / bbox_area if bbox_area > 0.0 else 0.0,
        nearest_neighbor_gap_mean=nearest_neighbor_gap_mean,
        centroid_dispersion=centroid_dispersion,
    )


def _rect_area(region: dict[str, float]) -> float:
    return max(0.0, float(region["x_max"]) - float(region["x_min"])) * max(
        0.0,
        float(region["y_max"]) - float(region["y_min"]),
    )
