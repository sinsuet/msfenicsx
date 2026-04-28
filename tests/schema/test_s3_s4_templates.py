from __future__ import annotations

from math import pi
from pathlib import Path
from typing import Any

import pytest
import yaml


SCENARIOS = {
    "s3_scale20": {
        "path": Path("scenarios/templates/s3_scale20.yaml"),
        "component_count": 20,
        "area_ratio": (0.52, 0.55),
        "load_power": (150.0, 158.0),
        "sink_span": (0.40, 0.44),
    },
    "s4_dense25": {
        "path": Path("scenarios/templates/s4_dense25.yaml"),
        "component_count": 25,
        "area_ratio": (0.60, 0.63),
        "load_power": (172.0, 182.0),
        "sink_span": (0.44, 0.48),
    },
}


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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
    raise AssertionError(f"Unexpected shape in S3/S4 template: {shape}")


def _placement_area(payload: dict[str, Any]) -> float:
    region = payload["placement_regions"][0]
    return (float(region["x_max"]) - float(region["x_min"])) * (
        float(region["y_max"]) - float(region["y_min"])
    )


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_identity_and_contract(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    assert payload["template_meta"]["template_id"] == template_id
    assert "operating_case_profiles" not in payload
    assert len(payload["component_families"]) == expected["component_count"]
    assert len(payload["load_rules"]) == expected["component_count"]
    assert [family["family_id"] for family in payload["component_families"]] == [
        f"c{index:02d}" for index in range(1, expected["component_count"] + 1)
    ]
    assert [rule["target_family"] for rule in payload["load_rules"]] == [
        f"c{index:02d}" for index in range(1, expected["component_count"] + 1)
    ]
    assert len(payload["boundary_feature_families"]) == 1
    assert payload["boundary_feature_families"][0]["edge"] == "top"


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_uses_higher_occupancy(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    component_area = sum(_family_area(family) for family in payload["component_families"])
    area_ratio = component_area / _placement_area(payload)

    lower, upper = expected["area_ratio"]
    assert lower <= area_ratio <= upper


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_power_and_sink_budget_shape(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    total_power = sum(float(rule["total_power"]) for rule in payload["load_rules"])
    power_lower, power_upper = expected["load_power"]
    assert power_lower <= total_power <= power_upper
    assert all(rule.get("source_area_ratio") is not None for rule in payload["load_rules"])

    sink = payload["boundary_feature_families"][0]
    sink_span = float(sink["span"]["max"]) - float(sink["span"]["min"])
    span_lower, span_upper = expected["sink_span"]
    assert span_lower <= sink_span <= span_upper


@pytest.mark.parametrize("template_id, expected", SCENARIOS.items())
def test_scale_template_declares_layout_semantics(template_id: str, expected: dict[str, Any]) -> None:
    payload = _load(expected["path"])

    hints = {family.get("placement_hint") for family in payload["component_families"]}
    assert {"adversarial_core", "center_mass", "left_edge", "right_edge", "bottom_band"} <= hints
    for family in payload["component_families"]:
        assert "layout_tags" in family
        assert "placement_hint" in family
        assert 0.0 < float(family.get("clearance", 0.0)) <= 0.014
