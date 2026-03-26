import pytest

from core.geometry.primitives import capsule_polygon, rectangle_polygon, slot_polygon
from core.geometry.transforms import apply_pose


def test_rectangle_polygon_returns_four_vertices() -> None:
    vertices = rectangle_polygon(width=0.4, height=0.2)

    assert len(vertices) == 4
    assert vertices[0] == (-0.2, -0.1)
    assert vertices[2] == (0.2, 0.1)


def test_apply_pose_translates_vertices_without_rotation() -> None:
    vertices = rectangle_polygon(width=0.4, height=0.2)

    transformed = apply_pose(vertices, {"x": 1.0, "y": 2.0, "rotation_deg": 0.0})

    assert transformed[0] == pytest.approx((0.8, 1.9))
    assert transformed[2] == pytest.approx((1.2, 2.1))


def test_capsule_and_slot_primitives_return_positive_area_outlines() -> None:
    capsule = capsule_polygon(length=0.3, radius=0.05)
    slot = slot_polygon(length=0.24, width=0.06)

    assert len(capsule) > 4
    assert len(slot) > 4
