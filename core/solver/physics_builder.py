"""Build FEniCSx variational forms for steady conduction with nonlinear radiation sinks."""

from __future__ import annotations

from typing import Any

import numpy as np
import shapely
import ufl
from dolfinx import fem, mesh
from shapely import covers, points


def build_thermal_problem(domain: mesh.Mesh, solver_inputs: dict[str, Any]) -> dict[str, Any]:
    function_space = fem.functionspace(domain, ("Lagrange", 1))
    temperature = fem.Function(function_space)
    ambient_temperature = float(solver_inputs["ambient_temperature"])
    temperature.interpolate(lambda x: np.full(x.shape[1], ambient_temperature, dtype=np.float64))

    conductivity = fem.Function(function_space)
    conductivity.interpolate(_field_interpolator(solver_inputs["components"], "conductivity", solver_inputs["default_conductivity"]))

    source = fem.Function(function_space)
    source.interpolate(_source_interpolator(solver_inputs["components"]))

    facet_tags, tag_lookup = build_line_sink_tags(domain, solver_inputs["panel_domain"], solver_inputs["line_sinks"])
    test_function = ufl.TestFunction(function_space)
    residual = conductivity * ufl.inner(ufl.grad(temperature), ufl.grad(test_function)) * ufl.dx
    residual -= source * test_function * ufl.dx
    ds = ufl.Measure("ds", domain=domain, subdomain_data=facet_tags)
    sigma = float(solver_inputs["stefan_boltzmann"])
    default_emissivity = float(solver_inputs["default_emissivity"])
    for line_sink in solver_inputs["line_sinks"]:
        tag = tag_lookup[line_sink["feature_id"]]
        sink_temperature = float(line_sink["sink_temperature"])
        transfer_coefficient = float(line_sink["transfer_coefficient"])
        emissivity = float(line_sink.get("emissivity", default_emissivity))
        residual += transfer_coefficient * (temperature - sink_temperature) * test_function * ds(tag)
        residual += emissivity * sigma * ((temperature**4) - (sink_temperature**4)) * test_function * ds(tag)
    return {
        "function_space": function_space,
        "temperature": temperature,
        "residual": residual,
        "facet_tags": facet_tags,
        "tag_lookup": tag_lookup,
    }


def build_line_sink_tags(
    domain: mesh.Mesh,
    panel_domain: dict[str, float],
    line_sinks: list[dict[str, Any]],
) -> tuple[mesh.MeshTags, dict[str, int]]:
    facet_dim = domain.topology.dim - 1
    facet_indices: list[np.ndarray] = []
    facet_values: list[np.ndarray] = []
    tag_lookup: dict[str, int] = {}
    for tag, line_sink in enumerate(line_sinks, start=1):
        locator = _line_sink_locator(panel_domain, line_sink)
        facets = mesh.locate_entities_boundary(domain, facet_dim, locator)
        if facets.size == 0:
            continue
        facet_indices.append(facets)
        facet_values.append(np.full(facets.shape, tag, dtype=np.int32))
        tag_lookup[line_sink["feature_id"]] = tag
    if facet_indices:
        entities = np.concatenate(facet_indices)
        values = np.concatenate(facet_values)
        order = np.argsort(entities)
        entities = entities[order]
        values = values[order]
    else:
        entities = np.array([], dtype=np.int32)
        values = np.array([], dtype=np.int32)
    return mesh.meshtags(domain, facet_dim, entities, values), tag_lookup


def _field_interpolator(components: list[dict[str, Any]], key: str, default_value: float):
    def interpolate(x: np.ndarray) -> np.ndarray:
        values = np.full(x.shape[1], default_value, dtype=np.float64)
        query_points = points(x[0], x[1])
        for component in components:
            mask = np.asarray(covers(component["polygon"], query_points))
            values[mask] = float(component[key])
        return values

    return interpolate


def _source_interpolator(components: list[dict[str, Any]]):
    def interpolate(x: np.ndarray) -> np.ndarray:
        values = np.zeros(x.shape[1], dtype=np.float64)
        query_points = points(x[0], x[1])
        for component in components:
            if component["area"] <= 0.0 or component["total_power"] == 0.0:
                continue
            mask = np.asarray(covers(component["polygon"], query_points))
            values[mask] = float(component["total_power"]) / float(component["area"])
        return values

    return interpolate


def _line_sink_locator(panel_domain: dict[str, float], line_sink: dict[str, Any]):
    width = float(panel_domain["width"])
    height = float(panel_domain["height"])
    start = float(line_sink["start"])
    end = float(line_sink["end"])
    edge = line_sink["edge"]
    tolerance = 1.0e-9
    if edge == "top":
        x_min = start * width
        x_max = end * width
        return lambda x: np.isclose(x[1], height, atol=tolerance) & (x[0] >= x_min - tolerance) & (x[0] <= x_max + tolerance)
    if edge == "bottom":
        x_min = start * width
        x_max = end * width
        return lambda x: np.isclose(x[1], 0.0, atol=tolerance) & (x[0] >= x_min - tolerance) & (x[0] <= x_max + tolerance)
    if edge == "left":
        y_min = start * height
        y_max = end * height
        return lambda x: np.isclose(x[0], 0.0, atol=tolerance) & (x[1] >= y_min - tolerance) & (x[1] <= y_max + tolerance)
    y_min = start * height
    y_max = end * height
    return lambda x: np.isclose(x[0], width, atol=tolerance) & (x[1] >= y_min - tolerance) & (x[1] <= y_max + tolerance)
