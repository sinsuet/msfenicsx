"""Interpret canonical cases into solver-ready geometry and physics inputs."""

from __future__ import annotations

from typing import Any

from shapely.affinity import scale

from core.geometry.layout_rules import component_polygon


def interpret_case(case: Any) -> dict[str, Any]:
    payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    materials = payload["materials"]
    panel_material = materials[payload["panel_material_ref"]]
    loads_by_component = {load["target_component_id"]: load for load in payload["loads"]}
    components = []
    for component in payload["components"]:
        material = materials[component["material_ref"]]
        polygon = component_polygon(component)
        load = loads_by_component.get(component["component_id"], {})
        source_polygon = _build_source_polygon(polygon, load.get("source_area_ratio"))
        components.append(
            {
                "component_id": component["component_id"],
                "polygon": polygon,
                "source_polygon": source_polygon,
                "conductivity": float(material["conductivity"]),
                "emissivity": float(material.get("emissivity", panel_material.get("emissivity", 0.8))),
                "total_power": float(load.get("total_power", 0.0)),
                "area": float(polygon.area),
                "source_area": float(source_polygon.area),
            }
        )
    physics = payload.get("physics", {})
    background_boundary = dict(physics.get("background_boundary_cooling", {}))
    return {
        "panel_domain": payload["panel_domain"],
        "mesh_profile": payload["mesh_profile"],
        "solver_profile": payload["solver_profile"],
        "default_conductivity": float(panel_material["conductivity"]),
        "default_emissivity": float(panel_material.get("emissivity", 0.8)),
        "ambient_temperature": float(physics.get("ambient_temperature", 290.0)),
        "stefan_boltzmann": float(physics.get("stefan_boltzmann", 5.670374419e-8)),
        "background_boundary_cooling": {
            "transfer_coefficient": float(background_boundary.get("transfer_coefficient", 0.0)),
            "emissivity": float(background_boundary.get("emissivity", panel_material.get("emissivity", 0.8))),
        },
        "components": components,
        "line_sinks": payload["boundary_features"],
    }


def _build_source_polygon(polygon: Any, source_area_ratio: Any) -> Any:
    if source_area_ratio is None:
        return polygon
    ratio = float(source_area_ratio)
    if ratio >= 1.0:
        return polygon
    if ratio <= 0.0:
        return polygon
    scale_factor = ratio ** 0.5
    localized = scale(polygon, xfact=scale_factor, yfact=scale_factor, origin="centroid")
    if localized.is_empty or localized.area <= 0.0:
        return polygon
    return localized
