from __future__ import annotations

from math import pi
from pathlib import Path
from typing import Any

import pytest
import yaml


TEMPLATE = Path("scenarios/templates/s7_aggressive25.yaml")


def _load() -> dict[str, Any]:
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def _spec_value(spec: Any) -> float:
    if isinstance(spec, dict):
        return float(spec["min"])
    return float(spec)


def _family_area(family: dict[str, Any]) -> float:
    geometry = family["geometry"]
    shape = family["shape"]
    if shape == "rect":
        return _spec_value(geometry["width"]) * _spec_value(geometry["height"])
    if shape == "circle":
        radius = _spec_value(geometry["radius"])
        return pi * radius * radius
    if shape == "capsule":
        length = _spec_value(geometry["length"])
        radius = _spec_value(geometry["radius"])
        return max(0.0, length - 2.0 * radius) * (2.0 * radius) + pi * radius * radius
    if shape == "slot":
        length = _spec_value(geometry["length"])
        width = _spec_value(geometry["width"])
        return max(0.0, length - width) * width + pi * (0.5 * width) ** 2
    raise AssertionError(f"Unexpected shape in S7 template: {shape}")


def test_s7_template_identity_and_component_contract() -> None:
    payload = _load()

    assert payload["template_meta"]["template_id"] == "s7_aggressive25"
    assert "operating_case_profiles" not in payload
    assert len(payload["component_families"]) == 25
    assert len(payload["load_rules"]) == 25
    assert [family["family_id"] for family in payload["component_families"]] == [
        f"c{index:02d}" for index in range(1, 26)
    ]
    assert [rule["target_family"] for rule in payload["load_rules"]] == [
        f"c{index:02d}" for index in range(1, 26)
    ]


def test_s7_template_uses_single_top_sink_and_aggressive_sink_span() -> None:
    payload = _load()

    assert len(payload["boundary_feature_families"]) == 1
    sink = payload["boundary_feature_families"][0]
    assert sink["kind"] == "line_sink"
    assert sink["edge"] == "top"
    assert 0.46 <= float(sink["span"]["max"]) - float(sink["span"]["min"]) <= 0.48


def test_s7_template_uses_dense_target_region_and_load_band() -> None:
    payload = _load()
    region = payload["placement_regions"][0]

    assert region["x_min"] == pytest.approx(0.04)
    assert region["x_max"] == pytest.approx(0.96)
    assert region["y_min"] == pytest.approx(0.04)
    assert region["y_max"] == pytest.approx(0.74)

    placement_area = (float(region["x_max"]) - float(region["x_min"])) * (
        float(region["y_max"]) - float(region["y_min"])
    )
    component_area = sum(_family_area(family) for family in payload["component_families"])
    assert 0.58 <= component_area / placement_area <= 0.63

    total_power = sum(float(rule["total_power"]) for rule in payload["load_rules"])
    assert 176.0 <= total_power <= 190.0


def test_s7_template_declares_multiple_layout_regimes() -> None:
    payload = _load()

    hints = {family.get("placement_hint") for family in payload["component_families"]}
    assert {"adversarial_core", "secondary_lane", "center_mass", "left_edge", "right_edge", "bottom_band"} <= hints

    adjacency_groups = {family.get("adjacency_group") for family in payload["component_families"]}
    assert {
        "primary-hot-core",
        "secondary-hot-lane",
        "center-service-shoulder",
        "edge-routing-belt",
    } <= adjacency_groups

    for family in payload["component_families"]:
        assert "layout_tags" in family
        assert "placement_hint" in family
        assert 0.0 < float(family.get("clearance", 0.0)) <= 0.014
