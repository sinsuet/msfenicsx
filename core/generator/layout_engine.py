"""Placement engine for sampled component requests."""

from __future__ import annotations

import random
from typing import Any

from core.geometry.layout_rules import (
    component_respects_keep_out_regions,
    component_within_domain,
    components_overlap,
)
from core.geometry.primitives import primitive_polygon
from core.geometry.transforms import transform_polygon
from core.schema.models import ScenarioTemplate


class LayoutGenerationError(RuntimeError):
    """Raised when the layout engine cannot place all components legally."""


def place_components(
    template: ScenarioTemplate,
    sampled_components: list[dict[str, Any]],
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    placed_components: list[dict[str, Any]] = []
    placement_regions = template.placement_regions or [
        {
            "region_id": "panel-domain",
            "kind": "rect",
            "x_min": 0.0,
            "x_max": float(template.panel_domain["width"]),
            "y_min": 0.0,
            "y_max": float(template.panel_domain["height"]),
        }
    ]
    max_attempts = int(template.generation_rules.get("max_placement_attempts", 100))
    family_counts: dict[str, int] = {}
    for sampled_component in sampled_components:
        family_id = sampled_component["family_id"]
        family_counts[family_id] = family_counts.get(family_id, 0) + 1
        component_id = f"{family_id}-{family_counts[family_id]:03d}"
        placed_components.append(
            _place_single_component(
                component_id=component_id,
                sampled_component=sampled_component,
                placement_regions=placement_regions,
                keep_out_regions=template.keep_out_regions,
                panel_domain=template.panel_domain,
                existing_components=placed_components,
                max_attempts=max_attempts,
                rng=rng,
            )
        )
    return placed_components


def _place_single_component(
    component_id: str,
    sampled_component: dict[str, Any],
    placement_regions: list[dict[str, Any]],
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    existing_components: list[dict[str, Any]],
    max_attempts: int,
    rng: random.Random,
) -> dict[str, Any]:
    rotation_deg = float(sampled_component.get("rotation_deg", 0.0))
    local_polygon = primitive_polygon(sampled_component["shape"], sampled_component["geometry"])
    rotated_polygon = transform_polygon(local_polygon, {"x": 0.0, "y": 0.0, "rotation_deg": rotation_deg})
    min_x, min_y, max_x, max_y = rotated_polygon.bounds
    region_candidates = placement_regions[:]
    rng.shuffle(region_candidates)
    for _ in range(max_attempts):
        region = region_candidates[0]
        x_min = float(region["x_min"]) - min_x
        x_max = float(region["x_max"]) - max_x
        y_min = float(region["y_min"]) - min_y
        y_max = float(region["y_max"]) - max_y
        if x_min > x_max or y_min > y_max:
            continue
        candidate = {
            "component_id": component_id,
            "role": sampled_component["role"],
            "shape": sampled_component["shape"],
            "pose": {
                "x": round(rng.uniform(x_min, x_max), 6),
                "y": round(rng.uniform(y_min, y_max), 6),
                "rotation_deg": rotation_deg,
            },
            "geometry": sampled_component["geometry"],
            "material_ref": sampled_component["material_ref"],
            "thermal_tags": sampled_component.get("thermal_tags", []),
        }
        if not component_within_domain(candidate, panel_domain):
            continue
        if not component_respects_keep_out_regions(candidate, keep_out_regions):
            continue
        if any(components_overlap(candidate, existing_component) for existing_component in existing_components):
            continue
        if sampled_component.get("total_power") is not None:
            candidate["total_power"] = sampled_component["total_power"]
        candidate["family_id"] = sampled_component["family_id"]
        return candidate
    raise LayoutGenerationError(f"Unable to place component {component_id} without overlap or keep-out violation.")
