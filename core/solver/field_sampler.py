"""Sample solved fields into canonical summaries."""

from __future__ import annotations

from typing import Any

import numpy as np
from shapely import covers, points


def sample_solution_fields(temperature_function: Any, components: list[dict[str, Any]]) -> dict[str, Any]:
    coordinates = temperature_function.function_space.tabulate_dof_coordinates()
    xy_coordinates = coordinates[:, :2]
    values = np.asarray(temperature_function.x.array, dtype=np.float64)
    component_summaries = []
    query_points = points(xy_coordinates[:, 0], xy_coordinates[:, 1])
    for component in components:
        mask = np.asarray(covers(component["polygon"], query_points))
        if not np.any(mask):
            centroid = np.array(component["polygon"].centroid.coords[0], dtype=np.float64)
            distances = np.linalg.norm(xy_coordinates - centroid, axis=1)
            mask = distances == np.min(distances)
        component_values = values[mask]
        component_summaries.append(
            {
                "component_id": component["component_id"],
                "temperature_min": float(np.min(component_values)),
                "temperature_mean": float(np.mean(component_values)),
                "temperature_max": float(np.max(component_values)),
            }
        )
    return {
        "field_records": {
            "temperature": {
                "kind": "cg1_dofs",
                "num_dofs": int(values.size),
            }
        },
        "summary_metrics": {
            "temperature_min": float(np.min(values)),
            "temperature_mean": float(np.mean(values)),
            "temperature_max": float(np.max(values)),
        },
        "component_summaries": component_summaries,
    }
