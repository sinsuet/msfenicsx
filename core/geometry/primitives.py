"""Primitive shape constructors for canonical 2D layouts."""

from __future__ import annotations

from collections.abc import Sequence

from shapely.geometry import LineString, Point, Polygon


Vertex = tuple[float, float]


def rectangle_polygon(width: float, height: float) -> list[Vertex]:
    _require_positive(width, "width")
    _require_positive(height, "height")
    half_width = width / 2.0
    half_height = height / 2.0
    return [
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ]


def circle_polygon(radius: float, quad_segs: int = 16) -> list[Vertex]:
    _require_positive(radius, "radius")
    return _exterior_vertices(Point(0.0, 0.0).buffer(radius, quad_segs=quad_segs))


def capsule_polygon(length: float, radius: float, quad_segs: int = 16) -> list[Vertex]:
    _require_positive(length, "length")
    _require_positive(radius, "radius")
    straight_length = max(length - (2.0 * radius), 0.0)
    half_straight = straight_length / 2.0
    segment = LineString([(-half_straight, 0.0), (half_straight, 0.0)])
    return _exterior_vertices(segment.buffer(radius, quad_segs=quad_segs))


def slot_polygon(length: float, width: float, quad_segs: int = 16) -> list[Vertex]:
    _require_positive(length, "length")
    _require_positive(width, "width")
    if width > length:
        raise ValueError("slot width must not exceed slot length")
    return capsule_polygon(length=length, radius=width / 2.0, quad_segs=quad_segs)


def polygon_outline(vertices: Sequence[Sequence[float]]) -> list[Vertex]:
    if len(vertices) < 3:
        raise ValueError("polygon requires at least three vertices")
    outline: list[Vertex] = []
    for vertex in vertices:
        if len(vertex) != 2:
            raise ValueError("polygon vertices must be 2D")
        outline.append((float(vertex[0]), float(vertex[1])))
    return outline


def primitive_polygon(shape: str, geometry: dict[str, float | Sequence[Sequence[float]]]) -> Polygon:
    if shape == "rect":
        return Polygon(rectangle_polygon(float(geometry["width"]), float(geometry["height"])))
    if shape == "circle":
        return Polygon(circle_polygon(float(geometry["radius"])))
    if shape == "capsule":
        return Polygon(capsule_polygon(float(geometry["length"]), float(geometry["radius"])))
    if shape == "polygon":
        return Polygon(polygon_outline(geometry["vertices"]))  # type: ignore[index]
    if shape == "slot":
        return Polygon(slot_polygon(float(geometry["length"]), float(geometry["width"])))
    raise ValueError(f"Unsupported primitive shape: {shape}")


def _exterior_vertices(polygon: Polygon) -> list[Vertex]:
    coordinates = list(polygon.exterior.coords)
    return [(float(x), float(y)) for x, y in coordinates[:-1]]


def _require_positive(value: float, label: str) -> None:
    if value <= 0.0:
        raise ValueError(f"{label} must be positive")
