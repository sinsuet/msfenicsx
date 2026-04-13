"""Deterministic parameter sampling for scenario templates."""

from __future__ import annotations

import random
from typing import Any

from core.schema.models import ScenarioTemplate


def sample_template_parameters(template: ScenarioTemplate, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    load_rules_by_family = {rule["target_family"]: rule for rule in template.load_rules}
    sampled_components: list[dict[str, Any]] = []
    for family in template.component_families:
        count_range = family.get("count_range", {"min": 1, "max": 1})
        count = int(_sample_value(count_range, rng))
        for instance_index in range(count):
            sampled_components.append(
                {
                    "family_id": family["family_id"],
                    "instance_index": instance_index,
                    "role": family["role"],
                    "shape": family["shape"],
                    "geometry": _sample_geometry(family.get("geometry", {}), rng),
                    "material_ref": family["material_ref"],
                    "rotation_deg": _sample_value(family.get("rotation_deg", 0.0), rng),
                    "thermal_tags": list(family.get("thermal_tags", [])),
                    "clearance": float(family.get("clearance", 0.0)),
                    "total_power": _sample_load_power(load_rules_by_family.get(family["family_id"]), rng),
                    "source_area_ratio": _sample_source_area_ratio(load_rules_by_family.get(family["family_id"]), rng),
                }
            )
    sampled_boundary_features = []
    for family in template.boundary_feature_families:
        sampled_boundary_features.append(
            {
                "family_id": family["family_id"],
                "kind": family["kind"],
                "edge": family["edge"],
                "start": float(family["span"]["min"]),
                "end": float(family["span"]["max"]),
                "sink_temperature": _sample_value(family["sink_temperature"], rng),
                "transfer_coefficient": _sample_value(family["transfer_coefficient"], rng),
            }
        )
    materials = {
        rule["material_id"]: {key: value for key, value in rule.items() if key != "material_id"}
        for rule in template.material_rules
    }
    return {
        "seed": seed,
        "template_id": template.template_meta["template_id"],
        "coordinate_system": template.coordinate_system,
        "panel_domain": template.panel_domain,
        "mesh_profile": template.mesh_profile,
        "solver_profile": template.solver_profile,
        "generation_rules": template.generation_rules,
        "materials": materials,
        "components": sampled_components,
        "boundary_features": sampled_boundary_features,
    }


def _sample_geometry(geometry_spec: dict[str, Any], rng: random.Random) -> dict[str, float]:
    return {key: _sample_value(value, rng) for key, value in geometry_spec.items()}


def _sample_load_power(rule: dict[str, Any] | None, rng: random.Random) -> float | None:
    if rule is None:
        return None
    power_spec = rule["total_power"]
    return _sample_value(power_spec, rng)


def _sample_source_area_ratio(rule: dict[str, Any] | None, rng: random.Random) -> float | None:
    if rule is None or "source_area_ratio" not in rule:
        return None
    return float(_sample_value(rule["source_area_ratio"], rng))


def _sample_value(spec: Any, rng: random.Random) -> Any:
    if isinstance(spec, dict) and {"min", "max"} <= set(spec):
        minimum = spec["min"]
        maximum = spec["max"]
        if isinstance(minimum, int) and isinstance(maximum, int):
            return rng.randint(int(minimum), int(maximum))
        return round(rng.uniform(float(minimum), float(maximum)), 6)
    if isinstance(spec, list):
        return rng.choice(spec)
    return spec
