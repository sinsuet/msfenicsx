"""Assemble shared sampled layouts into operating-case-specific thermal cases."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.schema.models import ScenarioTemplate, ThermalCase


def build_operating_case(
    template: ScenarioTemplate,
    sampled_payload: dict[str, Any],
    placed_components: list[dict[str, Any]],
    boundary_features: list[dict[str, Any]],
    operating_case_profile: dict[str, Any],
    seed: int,
) -> ThermalCase:
    template_id = template.template_meta["template_id"]
    operating_case_id = operating_case_profile["operating_case_id"]
    case_id = f"{template_id}-seed-{seed:04d}-{operating_case_id}"
    panel_material_ref = "panel_substrate" if "panel_substrate" in sampled_payload["materials"] else next(iter(sampled_payload["materials"]))
    components = [
        {
            key: value
            for key, value in component.items()
            if key not in {"family_id", "total_power"}
        }
        for component in placed_components
    ]
    loads = _build_operating_case_loads(components, operating_case_profile["component_power_overrides"])
    operating_boundary_features = _build_operating_case_boundary_features(
        boundary_features,
        operating_case_profile["boundary_feature_overrides"],
    )
    payload = {
        "schema_version": template.schema_version,
        "case_meta": {"case_id": case_id, "scenario_id": template_id},
        "coordinate_system": template.coordinate_system,
        "panel_domain": template.panel_domain,
        "panel_material_ref": panel_material_ref,
        "materials": sampled_payload["materials"],
        "components": components,
        "boundary_features": operating_boundary_features,
        "loads": loads,
        "physics": {
            "kind": "steady_heat_radiation",
            "ambient_temperature": float(operating_case_profile["ambient_temperature"]),
            "stefan_boltzmann": float(operating_case_profile.get("stefan_boltzmann", 5.670374419e-8)),
        },
        "mesh_profile": template.mesh_profile,
        "solver_profile": template.solver_profile,
        "provenance": {
            "source_template_id": template_id,
            "generation_seed": seed,
            "operating_case": operating_case_id,
        },
    }
    return ThermalCase.from_dict(payload)


def _build_operating_case_loads(
    components: list[dict[str, Any]],
    component_power_overrides: dict[str, Any],
) -> list[dict[str, Any]]:
    loads: list[dict[str, Any]] = []
    for component in components:
        role = component["role"]
        if role not in component_power_overrides:
            continue
        loads.append(
            {
                "load_id": f"load-{component['component_id']}",
                "target_component_id": component["component_id"],
                "total_power": float(component_power_overrides[role]),
            }
        )
    return loads


def _build_operating_case_boundary_features(
    boundary_features: list[dict[str, Any]],
    boundary_feature_overrides: dict[str, Any],
) -> list[dict[str, Any]]:
    operating_features: list[dict[str, Any]] = []
    for feature in boundary_features:
        override = boundary_feature_overrides.get(feature["feature_id"], {})
        updated_feature = deepcopy(feature)
        updated_feature.update(override)
        operating_features.append(updated_feature)
    return operating_features
