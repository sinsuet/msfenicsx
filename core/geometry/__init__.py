"""Geometry primitives, transforms, and layout rules for Phase 1."""

from core.geometry.layout_rules import (
    component_respects_keep_out_regions,
    component_within_domain,
    components_overlap,
    validate_line_sink_edge_segment,
)
from core.geometry.primitives import (
    capsule_polygon,
    circle_polygon,
    polygon_outline,
    primitive_polygon,
    rectangle_polygon,
    slot_polygon,
)
from core.geometry.transforms import apply_pose, transform_polygon

__all__ = [
    "apply_pose",
    "capsule_polygon",
    "circle_polygon",
    "component_respects_keep_out_regions",
    "component_within_domain",
    "components_overlap",
    "polygon_outline",
    "primitive_polygon",
    "rectangle_polygon",
    "slot_polygon",
    "transform_polygon",
    "validate_line_sink_edge_segment",
]
