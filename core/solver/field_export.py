"""Page-ready regular-grid field exports for solved thermal cases."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np


DEFAULT_GRID_SHAPE = (81, 101)


def export_field_views(
    temperature_function: Any,
    *,
    panel_domain: dict[str, float],
    components: Sequence[dict[str, Any]],
    line_sinks: Sequence[dict[str, Any]] | None = None,
    grid_shape: tuple[int, int] = DEFAULT_GRID_SHAPE,
) -> dict[str, Any]:
    height_samples, width_samples = grid_shape
    panel_width = float(panel_domain["width"])
    panel_height = float(panel_domain["height"])
    x_coords = np.linspace(0.0, panel_width, width_samples, dtype=np.float64)
    y_coords = np.linspace(0.0, panel_height, height_samples, dtype=np.float64)
    xx, yy = np.meshgrid(x_coords, y_coords)
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])

    dof_coordinates = temperature_function.function_space.tabulate_dof_coordinates()[:, :2]
    values = np.asarray(temperature_function.x.array, dtype=np.float64)
    temperature_grid = _nearest_neighbor_grid(dof_coordinates, values, grid_points).reshape(grid_shape)

    dx = panel_width / float(max(1, width_samples - 1))
    dy = panel_height / float(max(1, height_samples - 1))
    gradient_y, gradient_x = np.gradient(temperature_grid, dy, dx)
    gradient_magnitude_grid = np.sqrt((gradient_x**2) + (gradient_y**2))

    hottest_index = int(np.argmax(temperature_grid))
    hottest_row, hottest_col = np.unravel_index(hottest_index, temperature_grid.shape)
    line_sink_rows = [] if line_sinks is None else [_serialize_line_sink(line_sink, panel_width, panel_height) for line_sink in line_sinks]

    return {
        "arrays": {
            "temperature": temperature_grid,
            "gradient_magnitude": gradient_magnitude_grid,
        },
        "field_view": {
            "panel_domain": {
                "width": panel_width,
                "height": panel_height,
            },
            "temperature": {
                "grid_shape": [int(height_samples), int(width_samples)],
                "min": float(np.min(temperature_grid)),
                "max": float(np.max(temperature_grid)),
                "hotspot": {
                    "x": float(x_coords[hottest_col]),
                    "y": float(y_coords[hottest_row]),
                    "value": float(temperature_grid[hottest_row, hottest_col]),
                },
                "contour_levels": _build_contour_levels(temperature_grid),
            },
            "gradient_magnitude": {
                "grid_shape": [int(height_samples), int(width_samples)],
                "min": float(np.min(gradient_magnitude_grid)),
                "max": float(np.max(gradient_magnitude_grid)),
            },
            "layout": {
                "components": [_serialize_component(component) for component in components],
                "line_sinks": line_sink_rows,
            },
        },
    }


def _nearest_neighbor_grid(
    dof_coordinates: np.ndarray,
    values: np.ndarray,
    grid_points: np.ndarray,
) -> np.ndarray:
    distances = np.sum((grid_points[:, None, :] - dof_coordinates[None, :, :]) ** 2, axis=2)
    nearest_indices = np.argmin(distances, axis=1)
    return values[nearest_indices]


def _build_contour_levels(grid: np.ndarray, count: int = 6) -> list[float]:
    minimum = float(np.min(grid))
    maximum = float(np.max(grid))
    if np.isclose(minimum, maximum):
        return [minimum]
    return [float(value) for value in np.linspace(minimum, maximum, count, dtype=np.float64)]


def _serialize_component(component: dict[str, Any]) -> dict[str, Any]:
    polygon = component["polygon"]
    min_x, min_y, max_x, max_y = polygon.bounds
    return {
        "component_id": str(component["component_id"]),
        "outline": [
            [float(x_coord), float(y_coord)]
            for x_coord, y_coord in list(polygon.exterior.coords)[:-1]
        ],
        "bounds": {
            "x_min": float(min_x),
            "y_min": float(min_y),
            "x_max": float(max_x),
            "y_max": float(max_y),
        },
    }


def _serialize_line_sink(line_sink: dict[str, Any], panel_width: float, panel_height: float) -> dict[str, Any]:
    edge = str(line_sink["edge"])
    start = float(line_sink["start"])
    end = float(line_sink["end"])
    if edge in {"top", "bottom"}:
        return {
            "feature_id": str(line_sink["feature_id"]),
            "edge": edge,
            "start_x": start * panel_width,
            "end_x": end * panel_width,
        }
    return {
        "feature_id": str(line_sink["feature_id"]),
        "edge": edge,
        "start_y": start * panel_height,
        "end_y": end * panel_height,
    }
