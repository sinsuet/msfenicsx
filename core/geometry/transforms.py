"""Pose application helpers for geometry primitives."""

from __future__ import annotations

from collections.abc import Sequence
from math import cos, radians, sin

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon


Vertex = tuple[float, float]


def apply_pose(vertices: Sequence[Sequence[float]], pose: dict[str, float]) -> list[Vertex]:
    rotation_rad = radians(float(pose.get("rotation_deg", 0.0)))
    offset_x = float(pose.get("x", 0.0))
    offset_y = float(pose.get("y", 0.0))
    cos_theta = cos(rotation_rad)
    sin_theta = sin(rotation_rad)
    transformed: list[Vertex] = []
    for x_coord, y_coord in vertices:
        rotated_x = (float(x_coord) * cos_theta) - (float(y_coord) * sin_theta)
        rotated_y = (float(x_coord) * sin_theta) + (float(y_coord) * cos_theta)
        transformed.append((rotated_x + offset_x, rotated_y + offset_y))
    return transformed


def transform_polygon(polygon: Polygon, pose: dict[str, float]) -> Polygon:
    rotated = rotate(polygon, float(pose.get("rotation_deg", 0.0)), origin=(0.0, 0.0))
    return translate(rotated, xoff=float(pose.get("x", 0.0)), yoff=float(pose.get("y", 0.0)))
