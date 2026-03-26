"""Layout legality checks shared by generator and solver preparation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from shapely.geometry import Polygon

from core.geometry.primitives import polygon_outline, primitive_polygon
from core.geometry.transforms import transform_polygon


def component_polygon(component: dict[str, Any]) -> Polygon:
    local_polygon = primitive_polygon(component["shape"], component["geometry"])
    return transform_polygon(local_polygon, component["pose"])


def panel_domain_polygon(panel_domain: dict[str, float]) -> Polygon:
    width = float(panel_domain["width"])
    height = float(panel_domain["height"])
    return Polygon(((0.0, 0.0), (width, 0.0), (width, height), (0.0, height)))


def component_within_domain(component: dict[str, Any], panel_domain: dict[str, float]) -> bool:
    return panel_domain_polygon(panel_domain).covers(component_polygon(component))


def components_overlap(component_a: dict[str, Any], component_b: dict[str, Any], tolerance: float = 1.0e-12) -> bool:
    overlap_area = component_polygon(component_a).intersection(component_polygon(component_b)).area
    return overlap_area > tolerance


def component_respects_keep_out_regions(
    component: dict[str, Any],
    keep_out_regions: Sequence[dict[str, Any]],
    tolerance: float = 1.0e-12,
) -> bool:
    footprint = component_polygon(component)
    for region in keep_out_regions:
        if footprint.intersection(region_polygon(region)).area > tolerance:
            return False
    return True


def validate_line_sink_edge_segment(feature: dict[str, Any]) -> bool:
    if feature.get("kind") != "line_sink":
        return False
    if feature.get("edge") not in {"left", "right", "top", "bottom"}:
        return False
    start = float(feature.get("start", -1.0))
    end = float(feature.get("end", -1.0))
    return 0.0 <= start < end <= 1.0


def region_polygon(region: dict[str, Any]) -> Polygon:
    kind = region.get("kind", "rect")
    if kind == "rect":
        return Polygon(
            (
                (float(region["x_min"]), float(region["y_min"])),
                (float(region["x_max"]), float(region["y_min"])),
                (float(region["x_max"]), float(region["y_max"])),
                (float(region["x_min"]), float(region["y_max"])),
            )
        )
    if kind == "polygon":
        return Polygon(polygon_outline(region["vertices"]))
    raise ValueError(f"Unsupported keep-out region kind: {kind}")
