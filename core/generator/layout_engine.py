"""Placement engine for sampled component requests."""

from __future__ import annotations

import random
from typing import Any

from core.generator.layout_metrics import measure_layout_quality
from core.geometry.layout_rules import (
    component_polygon,
    component_respects_keep_out_regions,
    component_within_domain,
    components_violate_clearance,
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
    placement_regions = template.placement_regions or [_panel_domain_region(template.panel_domain)]
    layout_strategy = _resolve_layout_strategy(template)
    max_attempts = int(template.generation_rules.get("max_placement_attempts", 100))
    placement_retries = int(template.generation_rules.get("placement_retries", 4))
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
            -_placement_span(item[1], family_profiles.get(item[1]["family_id"], {})),
            -_component_area(item[1]),
            item[0],
        ),
    )
    last_error: LayoutGenerationError | None = None
    retry_count = max(1, placement_retries)
    for attempt_index in range(retry_count):
        rng = random.Random(seed + attempt_index * 7919)
        family_counts: dict[str, int] = {}
        placed_components: list[dict[str, Any]] = []
        placed_records: list[tuple[int, dict[str, Any]]] = []
        try:
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
                    layout_strategy=layout_strategy,
                    max_attempts=max_attempts,
                    rng=rng,
                )
                placed_components.append(candidate)
                placed_records.append((source_index, candidate))
        except LayoutGenerationError as exc:
            last_error = exc
            continue
        return _refine_layout_compactness(
            [component for _, component in sorted(placed_records, key=lambda item: item[0])],
            placement_regions=placement_regions,
            keep_out_regions=template.keep_out_regions,
            panel_domain=template.panel_domain,
            family_profiles=family_profiles,
            layout_strategy=layout_strategy,
        )
    raise last_error or LayoutGenerationError("Unable to place components without overlap or keep-out violation.")


def _place_single_component(
    component_id: str,
    sampled_component: dict[str, Any],
    placement_regions: list[dict[str, Any]],
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    existing_components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
    layout_strategy: dict[str, Any],
    max_attempts: int,
    rng: random.Random,
) -> dict[str, Any]:
    rotation_deg = float(sampled_component.get("rotation_deg", 0.0))
    local_polygon = primitive_polygon(sampled_component["shape"], sampled_component["geometry"])
    rotated_polygon = transform_polygon(local_polygon, {"x": 0.0, "y": 0.0, "rotation_deg": rotation_deg})
    min_x, min_y, max_x, max_y = rotated_polygon.bounds
    profile = family_profiles.get(sampled_component["family_id"], {})
    semantic_regions = _preferred_regions(placement_regions, profile, layout_strategy)
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
        x_min, x_max = _coerce_sampling_bounds(x_min, x_max)
        y_min, y_max = _coerce_sampling_bounds(y_min, y_max)
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
        if sampled_component.get("source_area_ratio") is not None:
            candidate["source_area_ratio"] = float(sampled_component["source_area_ratio"])
        if sampled_component.get("clearance") is not None:
            candidate["clearance"] = float(sampled_component["clearance"])
        if _is_candidate_legal(
            candidate,
            keep_out_regions=keep_out_regions,
            panel_domain=panel_domain,
            existing_components=existing_components,
            family_profiles=family_profiles,
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
    placement_hint = str(profile.get("placement_hint", ""))
    if placement_hint in {"left_edge", "right_edge"}:
        x_target, _ = _target_point(profile, None, x_bounds, y_bounds)
        return {
            "x": round(_sample_axis_value(x_target, x_bounds, rng, spread=0.06, uniform_chance=0.08), 6),
            "y": round(rng.uniform(float(y_bounds[0]), float(y_bounds[1])), 6),
        }
    if placement_hint in {"top_band", "bottom_band"}:
        _, y_target = _target_point(profile, None, x_bounds, y_bounds)
        return {
            "x": round(rng.uniform(float(x_bounds[0]), float(x_bounds[1])), 6),
            "y": round(_sample_axis_value(y_target, y_bounds, rng, spread=0.05, uniform_chance=0.08), 6),
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


def _sample_axis_value(
    target: float,
    bounds: tuple[float, float],
    rng: random.Random,
    *,
    spread: float = 0.12,
    uniform_chance: float = 0.12,
) -> float:
    lower_bound = float(bounds[0])
    upper_bound = float(bounds[1])
    if upper_bound <= lower_bound:
        return lower_bound
    span = upper_bound - lower_bound
    if rng.random() < uniform_chance:
        return rng.uniform(lower_bound, upper_bound)
    sampled = rng.gauss(float(target), spread * span)
    return max(lower_bound, min(sampled, upper_bound))


def _preferred_regions(
    placement_regions: list[dict[str, Any]],
    profile: dict[str, Any],
    layout_strategy: dict[str, Any],
) -> list[dict[str, Any]]:
    strategy_regions = _strategy_regions_for_profile(layout_strategy, profile)
    if strategy_regions:
        return strategy_regions
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


def _resolve_layout_strategy(template: ScenarioTemplate) -> dict[str, Any]:
    raw_strategy = template.generation_rules.get("layout_strategy")
    if not isinstance(raw_strategy, dict):
        return {}
    raw_zones = raw_strategy.get("zones", {})
    if not isinstance(raw_zones, dict):
        return {}
    zones = {
        str(zone_name): {
            "x_min": float(zone["x_min"]),
            "x_max": float(zone["x_max"]),
            "y_min": float(zone["y_min"]),
            "y_max": float(zone["y_max"]),
        }
        for zone_name, zone in raw_zones.items()
        if isinstance(zone_name, str) and isinstance(zone, dict)
    }
    return {
        "kind": str(raw_strategy.get("kind", "")),
        "zones": zones,
    }


def _strategy_regions_for_profile(
    layout_strategy: dict[str, Any],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    zones = layout_strategy.get("zones", {})
    if not zones:
        return []
    active_deck = zones.get("active_deck")
    dense_core = zones.get("dense_core")
    placement_hint = str(profile.get("placement_hint", ""))
    if placement_hint == "left_edge":
        candidates = [zones.get("left_io_edge")]
    elif placement_hint == "right_edge":
        candidates = [zones.get("right_service_edge")]
    elif placement_hint == "top_band":
        candidates = [zones.get("top_sink_band")]
    elif placement_hint == "bottom_band":
        candidates = [_strategy_bottom_band(zones)]
    elif placement_hint == "adversarial_core":
        adversarial_core = zones.get("adversarial_core")
        if adversarial_core is not None:
            candidates = [adversarial_core]
        else:
            candidates = []
    elif placement_hint == "center_mass":
        candidates = [dense_core, active_deck]
    else:
        candidates = [active_deck, dense_core]
    return [_copy_region(region) for region in candidates if region is not None]


def _strategy_bottom_band(zones: dict[str, dict[str, float]]) -> dict[str, float] | None:
    active_deck = zones.get("active_deck")
    if active_deck is None:
        return None
    dense_core = zones.get("dense_core", active_deck)
    active_width = float(active_deck["x_max"]) - float(active_deck["x_min"])
    active_height = float(active_deck["y_max"]) - float(active_deck["y_min"])
    x_min = max(float(active_deck["x_min"]), float(dense_core["x_min"]) - 0.05 * active_width)
    x_max = min(float(active_deck["x_max"]), float(dense_core["x_max"]) + 0.05 * active_width)
    return {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": float(active_deck["y_min"]) + 0.02 * active_height,
        "y_max": float(active_deck["y_min"]) + 0.30 * active_height,
    }


def _copy_region(region: dict[str, Any]) -> dict[str, float]:
    return {
        "x_min": float(region["x_min"]),
        "x_max": float(region["x_max"]),
        "y_min": float(region["y_min"]),
        "y_max": float(region["y_max"]),
    }


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
        "adversarial_core": 0,
        "center_mass": 1,
        "bottom_band": 1,
    }.get(placement_hint, 3)
    if {"edge_connector", "io_board"} & layout_tags:
        tag_priority = 0
    elif placement_hint == "top_band" and {"elongated", "sink_aware"} <= layout_tags:
        tag_priority = 0
    elif "service_routed" in layout_tags:
        tag_priority = 2
    elif {"sink_aware", "power_dense"} & layout_tags:
        tag_priority = 1
    else:
        tag_priority = 1
    return hint_priority, tag_priority


def _is_candidate_legal(
    candidate: dict[str, Any],
    *,
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    existing_components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
) -> bool:
    if not component_within_domain(candidate, panel_domain):
        return False
    if not component_respects_keep_out_regions(candidate, keep_out_regions):
        return False
    return not any(
        _components_conflict_with_clearance(candidate, existing_component, family_profiles)
        for existing_component in existing_components
    )


def _components_conflict_with_clearance(
    candidate: dict[str, Any],
    existing_component: dict[str, Any],
    family_profiles: dict[str, dict[str, Any]],
) -> bool:
    clearance_by_family = {
        family_id: float(profile.get("clearance", 0.0))
        for family_id, profile in family_profiles.items()
    }
    return components_violate_clearance(candidate, existing_component, clearance_by_family)


def _refine_layout_compactness(
    components: list[dict[str, Any]],
    *,
    placement_regions: list[dict[str, Any]],
    keep_out_regions: list[dict[str, Any]],
    panel_domain: dict[str, Any],
    family_profiles: dict[str, dict[str, Any]],
    layout_strategy: dict[str, Any],
) -> list[dict[str, Any]]:
    refined = [_copy_component(component) for component in components]
    current_penalty = _layout_penalty(
        refined,
        placement_regions=placement_regions,
        family_profiles=family_profiles,
        layout_strategy=layout_strategy,
    )
    for _ in range(6):
        changed = False
        for index, component in enumerate(refined):
            best_component = component
            best_penalty = current_penalty
            for target in _refinement_candidates(
                component,
                components=refined,
                family_profiles=family_profiles,
                placement_regions=placement_regions,
                layout_strategy=layout_strategy,
            ):
                trial_component = _copy_component(component)
                trial_component["pose"]["x"] = round(float(target[0]), 6)
                trial_component["pose"]["y"] = round(float(target[1]), 6)
                other_components = [other for other_index, other in enumerate(refined) if other_index != index]
                if not _is_candidate_legal(
                    trial_component,
                    keep_out_regions=keep_out_regions,
                    panel_domain=panel_domain,
                    existing_components=other_components,
                    family_profiles=family_profiles,
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
                    layout_strategy=layout_strategy,
                )
                if trial_penalty + 1.0e-12 < best_penalty:
                    best_component = trial_component
                    best_penalty = trial_penalty
            if best_component is not component:
                refined[index] = best_component
                current_penalty = best_penalty
                changed = True
        if not changed:
            break
    return refined


def _refinement_candidates(
    component: dict[str, Any],
    *,
    components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
    placement_regions: list[dict[str, Any]],
    layout_strategy: dict[str, Any],
) -> list[tuple[float, float]]:
    profile = family_profiles.get(component["family_id"], {})
    preferred_regions = _preferred_regions(placement_regions, profile, layout_strategy)
    if not preferred_regions:
        return []
    region = preferred_regions[0]
    region_x = 0.5 * (float(region["x_min"]) + float(region["x_max"]))
    region_y = 0.5 * (float(region["y_min"]) + float(region["y_max"]))
    group_centroid = _group_centroid(
        [other for other in components if other["component_id"] != component["component_id"]],
        family_profiles,
        profile,
    )
    global_centroid = _layout_centroid(
        [other for other in components if other["component_id"] != component["component_id"]]
    )
    current_x = float(component["pose"]["x"])
    current_y = float(component["pose"]["y"])
    candidates = [
        (region_x, region_y),
        (0.5 * current_x + 0.5 * region_x, 0.5 * current_y + 0.5 * region_y),
    ]
    if group_centroid is not None:
        candidates.append((0.45 * region_x + 0.55 * float(group_centroid[0]), 0.45 * region_y + 0.55 * float(group_centroid[1])))
        candidates.append((0.35 * current_x + 0.65 * float(group_centroid[0]), 0.35 * current_y + 0.65 * float(group_centroid[1])))
        candidates.append((0.20 * region_x + 0.80 * float(group_centroid[0]), 0.20 * region_y + 0.80 * float(group_centroid[1])))
    if global_centroid is not None:
        candidates.append((0.4 * region_x + 0.6 * float(global_centroid[0]), 0.4 * region_y + 0.6 * float(global_centroid[1])))
        candidates.append((0.2 * region_x + 0.8 * float(global_centroid[0]), 0.2 * region_y + 0.8 * float(global_centroid[1])))
        candidates.append((0.15 * current_x + 0.85 * float(global_centroid[0]), 0.15 * current_y + 0.85 * float(global_centroid[1])))
    unique_candidates: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for x_value, y_value in candidates:
        clamped_x = max(float(region["x_min"]), min(float(x_value), float(region["x_max"])))
        clamped_y = max(float(region["y_min"]), min(float(y_value), float(region["y_max"])))
        key = (round(clamped_x, 6), round(clamped_y, 6))
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append((float(key[0]), float(key[1])))
    return unique_candidates


def _layout_penalty(
    components: list[dict[str, Any]],
    *,
    placement_regions: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
    layout_strategy: dict[str, Any],
) -> float:
    polygons = [component_polygon(component) for component in components]
    min_x = min(float(polygon.bounds[0]) for polygon in polygons)
    min_y = min(float(polygon.bounds[1]) for polygon in polygons)
    max_x = max(float(polygon.bounds[2]) for polygon in polygons)
    max_y = max(float(polygon.bounds[3]) for polygon in polygons)
    penalty = (max_x - min_x) * (max_y - min_y)
    for component in components:
        profile = family_profiles.get(component["family_id"], {})
        x_value = float(component["pose"]["x"])
        y_value = float(component["pose"]["y"])
        preferred_region = _preferred_regions(placement_regions, profile, layout_strategy)[0]
        penalty += 3.0 * _component_distance_outside_region(component, preferred_region)
        region_center_x = 0.5 * (float(preferred_region["x_min"]) + float(preferred_region["x_max"]))
        region_center_y = 0.5 * (float(preferred_region["y_min"]) + float(preferred_region["y_max"]))
        penalty += 0.18 * ((x_value - region_center_x) ** 2 + (y_value - region_center_y) ** 2) ** 0.5
    layout_metrics = measure_layout_quality(
        {"components": components},
        placement_region=placement_regions[0],
        active_deck=layout_strategy.get("zones", {}).get("active_deck"),
        dense_core=layout_strategy.get("zones", {}).get("dense_core"),
    )
    penalty += 0.20 * _group_dispersion_penalty(components, family_profiles)
    penalty += 0.60 * layout_metrics.nearest_neighbor_gap_mean
    penalty += 1.95 * layout_metrics.largest_dense_core_void_ratio
    penalty -= 1.15 * layout_metrics.bbox_fill_ratio
    return penalty


def _layout_centroid(components: list[dict[str, Any]]) -> tuple[float, float] | None:
    if not components:
        return None
    return (
        sum(float(component["pose"]["x"]) for component in components) / float(len(components)),
        sum(float(component["pose"]["y"]) for component in components) / float(len(components)),
    )


def _distance_outside_region(x_value: float, y_value: float, region: dict[str, Any]) -> float:
    dx = 0.0
    dy = 0.0
    if x_value < float(region["x_min"]):
        dx = float(region["x_min"]) - x_value
    elif x_value > float(region["x_max"]):
        dx = x_value - float(region["x_max"])
    if y_value < float(region["y_min"]):
        dy = float(region["y_min"]) - y_value
    elif y_value > float(region["y_max"]):
        dy = y_value - float(region["y_max"])
    return (dx**2 + dy**2) ** 0.5


def _component_distance_outside_region(component: dict[str, Any], region: dict[str, Any]) -> float:
    min_x, min_y, max_x, max_y = component_polygon(component).bounds
    dx = max(0.0, float(region["x_min"]) - float(min_x), float(max_x) - float(region["x_max"]))
    dy = max(0.0, float(region["y_min"]) - float(min_y), float(max_y) - float(region["y_max"]))
    return (dx**2 + dy**2) ** 0.5


def _group_dispersion_penalty(
    components: list[dict[str, Any]],
    family_profiles: dict[str, dict[str, Any]],
) -> float:
    groups: dict[str, list[dict[str, Any]]] = {}
    for component in components:
        adjacency_group = family_profiles.get(component["family_id"], {}).get("adjacency_group")
        if not adjacency_group:
            continue
        groups.setdefault(str(adjacency_group), []).append(component)
    penalty = 0.0
    for grouped_components in groups.values():
        if len(grouped_components) <= 1:
            continue
        centroid = _layout_centroid(grouped_components)
        if centroid is None:
            continue
        penalty += sum(
            ((float(component["pose"]["x"]) - float(centroid[0])) ** 2 + (float(component["pose"]["y"]) - float(centroid[1])) ** 2) ** 0.5
            for component in grouped_components
        ) / float(len(grouped_components))
    return penalty


def _component_area(sampled_component: dict[str, Any]) -> float:
    return float(primitive_polygon(sampled_component["shape"], sampled_component["geometry"]).area)


def _placement_span(sampled_component: dict[str, Any], profile: dict[str, Any]) -> float:
    rotation_deg = float(sampled_component.get("rotation_deg", 0.0))
    polygon = primitive_polygon(sampled_component["shape"], sampled_component["geometry"])
    rotated_polygon = transform_polygon(polygon, {"x": 0.0, "y": 0.0, "rotation_deg": rotation_deg})
    min_x, min_y, max_x, max_y = rotated_polygon.bounds
    placement_hint = str(profile.get("placement_hint", ""))
    if placement_hint in {"left_edge", "right_edge"}:
        return float(max_y) - float(min_y)
    if placement_hint in {"top_band", "bottom_band"}:
        return float(max_x) - float(min_x)
    return max(float(max_x) - float(min_x), float(max_y) - float(min_y))


def _coerce_sampling_bounds(lower: float, upper: float, *, tolerance: float = 1.0e-9) -> tuple[float, float]:
    lower_value = float(lower)
    upper_value = float(upper)
    if lower_value <= upper_value:
        return lower_value, upper_value
    if lower_value - upper_value <= tolerance:
        midpoint = 0.5 * (lower_value + upper_value)
        return midpoint, midpoint
    return lower_value, upper_value


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
