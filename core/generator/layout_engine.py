"""Placement engine for sampled component requests."""

from __future__ import annotations

import random
from typing import Any

from core.geometry.layout_rules import (
    component_polygon,
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
    placed_records: list[tuple[int, dict[str, Any]]] = []
    placement_regions = template.placement_regions or [_panel_domain_region(template.panel_domain)]
    max_attempts = int(template.generation_rules.get("max_placement_attempts", 100))
    family_profiles = {
        family["family_id"]: {
            "layout_tags": tuple(str(tag) for tag in family.get("layout_tags", [])),
            "placement_hint": family.get("placement_hint"),
            "adjacency_group": family.get("adjacency_group"),
            "clearance": float(family.get("clearance", 0.0)),
        }
        for family in template.component_families
    }
    family_counts: dict[str, int] = {}
    work_items = sorted(
        enumerate(sampled_components),
        key=lambda item: (
            _placement_priority(family_profiles.get(item[1]["family_id"], {})),
            item[0],
        ),
    )
    for source_index, sampled_component in work_items:
        family_id = sampled_component["family_id"]
        family_counts[family_id] = family_counts.get(family_id, 0) + 1
        component_id = f"{family_id}-{family_counts[family_id]:03d}"
        candidate = _place_single_component(
                component_id=component_id,
                sampled_component=sampled_component,
                placement_regions=placement_regions,
                keep_out_regions=template.keep_out_regions,
                panel_domain=template.panel_domain,
                existing_components=placed_components,
                family_profiles=family_profiles,
                max_attempts=max_attempts,
                rng=rng,
            )
        placed_components.append(candidate)
        placed_records.append((source_index, candidate))
    refined_components = _refine_layout_compactness(
        [component for _, component in sorted(placed_records, key=lambda item: item[0])],
        placement_regions=placement_regions,
        keep_out_regions=template.keep_out_regions,
        panel_domain=template.panel_domain,
        family_profiles=family_profiles,
    )
    return refined_components


def _place_single_component(
    component_id: str,
    sampled_component: dict[str, Any],
    placement_regions: list[dict[str, Any]],
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    existing_components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
    max_attempts: int,
    rng: random.Random,
) -> dict[str, Any]:
    rotation_deg = float(sampled_component.get("rotation_deg", 0.0))
    local_polygon = primitive_polygon(sampled_component["shape"], sampled_component["geometry"])
    rotated_polygon = transform_polygon(local_polygon, {"x": 0.0, "y": 0.0, "rotation_deg": rotation_deg})
    min_x, min_y, max_x, max_y = rotated_polygon.bounds
    profile = family_profiles.get(sampled_component["family_id"], {})
    semantic_regions = _preferred_regions(placement_regions, profile)
    candidate = _try_place_with_regions(
        component_id=component_id,
        sampled_component=sampled_component,
        region_candidates=semantic_regions,
        keep_out_regions=keep_out_regions,
        panel_domain=panel_domain,
        existing_components=existing_components,
        family_profiles=family_profiles,
        bounds=(min_x, min_y, max_x, max_y),
        max_attempts=max_attempts,
        uniform=False,
        rng=rng,
    )
    if candidate is not None:
        return candidate
    candidate = _try_place_with_regions(
        component_id=component_id,
        sampled_component=sampled_component,
        region_candidates=placement_regions,
        keep_out_regions=keep_out_regions,
        panel_domain=panel_domain,
        existing_components=existing_components,
        family_profiles=family_profiles,
        bounds=(min_x, min_y, max_x, max_y),
        max_attempts=max_attempts,
        uniform=False,
        rng=rng,
    )
    if candidate is not None:
        return candidate
    candidate = _try_place_with_regions(
        component_id=component_id,
        sampled_component=sampled_component,
        region_candidates=placement_regions,
        keep_out_regions=keep_out_regions,
        panel_domain=panel_domain,
        existing_components=existing_components,
        family_profiles=family_profiles,
        bounds=(min_x, min_y, max_x, max_y),
        max_attempts=max_attempts,
        uniform=True,
        rng=rng,
    )
    if candidate is not None:
        return candidate
    raise LayoutGenerationError(f"Unable to place component {component_id} without overlap or keep-out violation.")


def _try_place_with_regions(
    *,
    component_id: str,
    sampled_component: dict[str, Any],
    region_candidates: list[dict[str, Any]],
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    existing_components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
    bounds: tuple[float, float, float, float],
    max_attempts: int,
    uniform: bool,
    rng: random.Random,
) -> dict[str, Any] | None:
    if not region_candidates:
        return None
    min_x, min_y, max_x, max_y = bounds
    profile = family_profiles.get(sampled_component["family_id"], {})
    group_centroid = _group_centroid(existing_components, family_profiles, profile)
    shuffled_regions = region_candidates[:]
    rng.shuffle(shuffled_regions)
    for _ in range(max_attempts):
        region = rng.choice(shuffled_regions)
        x_min = float(region["x_min"]) - min_x
        x_max = float(region["x_max"]) - max_x
        y_min = float(region["y_min"]) - min_y
        y_max = float(region["y_max"]) - max_y
        if x_min > x_max or y_min > y_max:
            continue
        pose = _sample_pose(
            profile=profile,
            group_centroid=None if uniform else group_centroid,
            x_bounds=(x_min, x_max),
            y_bounds=(y_min, y_max),
            uniform=uniform,
            rng=rng,
        )
        candidate = {
            "component_id": component_id,
            "role": sampled_component["role"],
            "shape": sampled_component["shape"],
            "pose": {
                "x": pose["x"],
                "y": pose["y"],
                "rotation_deg": float(sampled_component.get("rotation_deg", 0.0)),
            },
            "geometry": sampled_component["geometry"],
            "material_ref": sampled_component["material_ref"],
            "thermal_tags": sampled_component.get("thermal_tags", []),
            "family_id": sampled_component["family_id"],
        }
        if sampled_component.get("total_power") is not None:
            candidate["total_power"] = sampled_component["total_power"]
        if _is_candidate_legal(
            candidate,
            keep_out_regions=keep_out_regions,
            panel_domain=panel_domain,
            existing_components=existing_components,
        ):
            return candidate
    return None


def _sample_pose(
    *,
    profile: dict[str, Any],
    group_centroid: tuple[float, float] | None,
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
    uniform: bool,
    rng: random.Random,
) -> dict[str, float]:
    if uniform:
        return {
            "x": round(rng.uniform(float(x_bounds[0]), float(x_bounds[1])), 6),
            "y": round(rng.uniform(float(y_bounds[0]), float(y_bounds[1])), 6),
        }
    x_target, y_target = _target_point(profile, group_centroid, x_bounds, y_bounds)
    return {
        "x": round(_sample_axis_value(x_target, x_bounds, rng), 6),
        "y": round(_sample_axis_value(y_target, y_bounds, rng), 6),
    }


def _target_point(
    profile: dict[str, Any],
    group_centroid: tuple[float, float] | None,
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
) -> tuple[float, float]:
    x_center = 0.5 * (float(x_bounds[0]) + float(x_bounds[1]))
    y_center = 0.5 * (float(y_bounds[0]) + float(y_bounds[1]))
    if group_centroid is not None:
        x_center = max(float(x_bounds[0]), min(float(group_centroid[0]), float(x_bounds[1])))
        y_center = max(float(y_bounds[0]), min(float(group_centroid[1]), float(y_bounds[1])))
    placement_hint = profile.get("placement_hint")
    if placement_hint == "left_edge":
        x_center = float(x_bounds[0]) + 0.35 * (float(x_bounds[1]) - float(x_bounds[0]))
    elif placement_hint == "right_edge":
        x_center = float(x_bounds[1]) - 0.35 * (float(x_bounds[1]) - float(x_bounds[0]))
    elif placement_hint == "top_band":
        y_center = float(y_bounds[1]) - 0.3 * (float(y_bounds[1]) - float(y_bounds[0]))
    elif placement_hint == "bottom_band":
        y_center = float(y_bounds[0]) + 0.3 * (float(y_bounds[1]) - float(y_bounds[0]))
    return x_center, y_center


def _sample_axis_value(target: float, bounds: tuple[float, float], rng: random.Random) -> float:
    lower_bound = float(bounds[0])
    upper_bound = float(bounds[1])
    if upper_bound <= lower_bound:
        return lower_bound
    span = upper_bound - lower_bound
    if rng.random() < 0.3:
        return rng.uniform(lower_bound, upper_bound)
    sampled = rng.gauss(float(target), 0.18 * span)
    return max(lower_bound, min(sampled, upper_bound))


def _preferred_regions(
    placement_regions: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    placement_hint = profile.get("placement_hint")
    if not placement_hint:
        return placement_regions[:]
    preferred: list[dict[str, Any]] = []
    for region in placement_regions:
        if region.get("kind", "rect") != "rect":
            preferred.append(region)
            continue
        preferred.append(_hint_region(region, str(placement_hint)))
    return preferred


def _hint_region(region: dict[str, Any], placement_hint: str) -> dict[str, Any]:
    x_min = float(region["x_min"])
    x_max = float(region["x_max"])
    y_min = float(region["y_min"])
    y_max = float(region["y_max"])
    width = x_max - x_min
    height = y_max - y_min
    if placement_hint == "left_edge":
        return {**region, "x_max": x_min + 0.16 * width}
    if placement_hint == "right_edge":
        return {**region, "x_min": x_max - 0.16 * width}
    if placement_hint == "top_band":
        return {**region, "y_min": y_max - 0.24 * height}
    if placement_hint == "bottom_band":
        return {**region, "y_max": y_min + 0.20 * height}
    if placement_hint == "center_mass":
        return {
            **region,
            "x_min": x_min + 0.22 * width,
            "x_max": x_max - 0.22 * width,
            "y_min": y_min + 0.20 * height,
            "y_max": y_max - 0.20 * height,
        }
    return region


def _group_centroid(
    existing_components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
    profile: dict[str, Any],
) -> tuple[float, float] | None:
    adjacency_group = profile.get("adjacency_group")
    if not adjacency_group:
        return None
    grouped_components = [
        component
        for component in existing_components
        if family_profiles.get(component["family_id"], {}).get("adjacency_group") == adjacency_group
    ]
    if not grouped_components:
        return None
    return (
        sum(float(component["pose"]["x"]) for component in grouped_components) / float(len(grouped_components)),
        sum(float(component["pose"]["y"]) for component in grouped_components) / float(len(grouped_components)),
    )


def _placement_priority(profile: dict[str, Any]) -> tuple[int, int]:
    placement_hint = str(profile.get("placement_hint", ""))
    layout_tags = set(profile.get("layout_tags", ()))
    hint_priority = {
        "top_band": 0,
        "left_edge": 0,
        "right_edge": 0,
        "bottom_band": 1,
        "center_mass": 2,
    }.get(placement_hint, 3)
    tag_priority = 0 if {"sink_aware", "edge_connector"} & layout_tags else 1
    return hint_priority, tag_priority


def _is_candidate_legal(
    candidate: dict[str, Any],
    *,
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    existing_components: list[dict[str, Any]],
) -> bool:
    if not component_within_domain(candidate, panel_domain):
        return False
    if not component_respects_keep_out_regions(candidate, keep_out_regions):
        return False
    return not any(components_overlap(candidate, existing_component) for existing_component in existing_components)


def _refine_layout_compactness(
    components: list[dict[str, Any]],
    *,
    placement_regions: list[dict[str, Any]],
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    family_profiles: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    refined = [_copy_component(component) for component in components]
    current_penalty = _layout_penalty(refined, placement_regions=placement_regions, family_profiles=family_profiles)
    for index, component in enumerate(refined):
        profile = family_profiles.get(component["family_id"], {})
        target = _refinement_target(
            component,
            components=refined,
            family_profiles=family_profiles,
            placement_regions=placement_regions,
        )
        if target is None:
            continue
        trial_component = _copy_component(component)
        trial_component["pose"]["x"] = round(float(target[0]), 6)
        trial_component["pose"]["y"] = round(float(target[1]), 6)
        other_components = [other for other_index, other in enumerate(refined) if other_index != index]
        if not _is_candidate_legal(
            trial_component,
            keep_out_regions=keep_out_regions,
            panel_domain=panel_domain,
            existing_components=other_components,
        ):
            continue
        trial_components = [
            trial_component if other_index == index else _copy_component(other)
            for other_index, other in enumerate(refined)
        ]
        trial_penalty = _layout_penalty(
            trial_components,
            placement_regions=placement_regions,
            family_profiles=family_profiles,
        )
        if trial_penalty + 1.0e-12 < current_penalty:
            refined[index] = trial_component
            current_penalty = trial_penalty
    return refined


def _refinement_target(
    component: dict[str, Any],
    *,
    components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
    placement_regions: list[dict[str, Any]],
) -> tuple[float, float] | None:
    profile = family_profiles.get(component["family_id"], {})
    placement_hint = profile.get("placement_hint")
    region = _preferred_regions(placement_regions, profile)[0]
    target_x = float(component["pose"]["x"])
    target_y = float(component["pose"]["y"])
    region_x = 0.5 * (float(region["x_min"]) + float(region["x_max"]))
    region_y = 0.5 * (float(region["y_min"]) + float(region["y_max"]))
    if placement_hint == "left_edge":
        target_x = region_x
    elif placement_hint == "right_edge":
        target_x = region_x
    elif placement_hint == "top_band":
        target_y = region_y
    elif placement_hint == "bottom_band":
        target_y = region_y
    elif placement_hint == "center_mass":
        target_x = region_x
        target_y = region_y
    group_centroid = _group_centroid(
        [other for other in components if other["component_id"] != component["component_id"]],
        family_profiles,
        profile,
    )
    if group_centroid is not None:
        target_x = 0.55 * target_x + 0.45 * float(group_centroid[0])
        target_y = 0.55 * target_y + 0.45 * float(group_centroid[1])
    return target_x, target_y


def _layout_penalty(
    components: list[dict[str, Any]],
    *,
    placement_regions: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
) -> float:
    polygons = [component_polygon(component) for component in components]
    min_x = min(float(polygon.bounds[0]) for polygon in polygons)
    min_y = min(float(polygon.bounds[1]) for polygon in polygons)
    max_x = max(float(polygon.bounds[2]) for polygon in polygons)
    max_y = max(float(polygon.bounds[3]) for polygon in polygons)
    penalty = (max_x - min_x) * (max_y - min_y)
    region = placement_regions[0]
    left_threshold = float(region["x_min"]) + 0.16 * (float(region["x_max"]) - float(region["x_min"]))
    right_threshold = float(region["x_max"]) - 0.16 * (float(region["x_max"]) - float(region["x_min"]))
    top_threshold = float(region["y_max"]) - 0.24 * (float(region["y_max"]) - float(region["y_min"]))
    bottom_threshold = float(region["y_min"]) + 0.20 * (float(region["y_max"]) - float(region["y_min"]))
    for component in components:
        profile = family_profiles.get(component["family_id"], {})
        placement_hint = profile.get("placement_hint")
        x_value = float(component["pose"]["x"])
        y_value = float(component["pose"]["y"])
        if placement_hint == "left_edge":
            penalty += max(0.0, x_value - left_threshold)
        elif placement_hint == "right_edge":
            penalty += max(0.0, right_threshold - x_value)
        elif placement_hint == "top_band":
            penalty += max(0.0, top_threshold - y_value)
        elif placement_hint == "bottom_band":
            penalty += max(0.0, y_value - bottom_threshold)
    return penalty


def _copy_component(component: dict[str, Any]) -> dict[str, Any]:
    copied = dict(component)
    copied["pose"] = dict(component["pose"])
    copied["geometry"] = dict(component["geometry"])
    copied["thermal_tags"] = list(component.get("thermal_tags", []))
    return copied


def _panel_domain_region(panel_domain: dict[str, Any]) -> dict[str, Any]:
    return {
        "region_id": "panel-domain",
        "kind": "rect",
        "x_min": 0.0,
        "x_max": float(panel_domain["width"]),
        "y_min": 0.0,
        "y_max": float(panel_domain["height"]),
    }
