"""Assemble sampled layout outputs into canonical thermal cases."""

from __future__ import annotations

from typing import Any

from core.schema.models import ScenarioTemplate, ThermalCase


def build_thermal_case(
    template: ScenarioTemplate,
    sampled_payload: dict[str, Any],
    placed_components: list[dict[str, Any]],
    boundary_features: list[dict[str, Any]],
    seed: int,
) -> ThermalCase:
    template_id = template.template_meta["template_id"]
    case_id = f"{template_id}-seed-{seed:04d}"
    panel_material_ref = next(iter(sampled_payload["materials"]))
    components = []
    loads = []
    for component in placed_components:
        component_payload = {
            key: value
            for key, value in component.items()
            if key not in {"family_id", "total_power"}
        }
        components.append(component_payload)
        total_power = component.get("total_power")
        if total_power is not None:
            loads.append(
                {
                    "load_id": f"load-{component['component_id']}",
                    "target_component_id": component["component_id"],
                    "total_power": total_power,
                }
            )
    payload = {
        "schema_version": template.schema_version,
        "case_meta": {"case_id": case_id, "scenario_id": template_id},
        "coordinate_system": template.coordinate_system,
        "panel_domain": template.panel_domain,
        "panel_material_ref": panel_material_ref,
        "materials": sampled_payload["materials"],
        "components": components,
        "boundary_features": boundary_features,
        "loads": loads,
        "physics": {"kind": "steady_heat_radiation"},
        "mesh_profile": template.mesh_profile,
        "solver_profile": template.solver_profile,
        "provenance": {
            "source_template_id": template_id,
            "generation_seed": seed,
        },
    }
    return ThermalCase.from_dict(payload)
