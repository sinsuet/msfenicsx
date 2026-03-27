"""Interpret canonical cases into solver-ready geometry and physics inputs."""

from __future__ import annotations

from typing import Any

from core.geometry.layout_rules import component_polygon


def interpret_case(case: Any) -> dict[str, Any]:
    payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    materials = payload["materials"]
    panel_material = materials[payload["panel_material_ref"]]
    loads_by_component = {load["target_component_id"]: float(load["total_power"]) for load in payload["loads"]}
    components = []
    for component in payload["components"]:
        material = materials[component["material_ref"]]
        polygon = component_polygon(component)
        components.append(
            {
                "component_id": component["component_id"],
                "polygon": polygon,
                "conductivity": float(material["conductivity"]),
                "emissivity": float(material.get("emissivity", panel_material.get("emissivity", 0.8))),
                "total_power": loads_by_component.get(component["component_id"], 0.0),
                "area": float(polygon.area),
            }
        )
    physics = payload.get("physics", {})
    return {
        "panel_domain": payload["panel_domain"],
        "mesh_profile": payload["mesh_profile"],
        "solver_profile": payload["solver_profile"],
        "default_conductivity": float(panel_material["conductivity"]),
        "default_emissivity": float(panel_material.get("emissivity", 0.8)),
        "ambient_temperature": float(physics.get("ambient_temperature", 290.0)),
        "stefan_boltzmann": float(physics.get("stefan_boltzmann", 5.670374419e-8)),
        "components": components,
        "line_sinks": payload["boundary_features"],
    }
