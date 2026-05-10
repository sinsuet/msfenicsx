from __future__ import annotations

from math import pi
from pathlib import Path
from typing import Any

import yaml


TEMPLATE = Path("scenarios/templates/s4_aggressive10.yaml")


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
    raise AssertionError(f"Unexpected shape in S4 template: {shape}")


def test_s4_template_identity_and_component_contract() -> None:
    payload = _load()

    assert payload["template_meta"]["template_id"] == "s4_aggressive10"
    assert "operating_case_profiles" not in payload
    assert len(payload["component_families"]) == 10
    assert len(payload["load_rules"]) == 10
    assert [family["family_id"] for family in payload["component_families"]] == [
        f"c{index:02d}" for index in range(1, 11)
    ]
    assert [rule["target_family"] for rule in payload["load_rules"]] == [
        f"c{index:02d}" for index in range(1, 11)
    ]


def test_s4_template_uses_single_top_sink_with_low_dimensional_budget_span() -> None:
    payload = _load()

    assert len(payload["boundary_feature_families"]) == 1
    sink = payload["boundary_feature_families"][0]
    assert sink["kind"] == "line_sink"
    assert sink["edge"] == "top"
    assert sink["sink_temperature"]["min"] == 290.5
    assert sink["transfer_coefficient"]["min"] == 7.5
    assert 0.39 <= float(sink["span"]["max"]) - float(sink["span"]["min"]) <= 0.41


def test_s4_template_load_and_fill_ratio_match_low_dimensional_aggressive_band() -> None:
    payload = _load()
    region = payload["placement_regions"][0]

    assert region["x_min"] == 0.05
    assert region["x_max"] == 0.95
    assert region["y_min"] == 0.04
    assert region["y_max"] == 0.72

    placement_area = (float(region["x_max"]) - float(region["x_min"])) * (
        float(region["y_max"]) - float(region["y_min"])
    )
    component_area = sum(_family_area(family) for family in payload["component_families"])
    assert 0.27 <= component_area / placement_area <= 0.31

    total_power = sum(float(rule["total_power"]) for rule in payload["load_rules"])
    assert 98.0 <= total_power <= 106.0


def test_s4_template_declares_semantic_layout_metadata() -> None:
    payload = _load()

    hints = {family.get("placement_hint") for family in payload["component_families"]}
    assert {"adversarial_core", "center_mass", "left_edge", "right_edge", "bottom_band"} <= hints

    groups = {family.get("adjacency_group") for family in payload["component_families"]}
    assert {"primary-hot-cluster", "sink-lane", "io-shoulder", "support-band"} <= groups

    for family in payload["component_families"]:
        assert family.get("layout_tags")
        assert family.get("placement_hint")
        assert 0.0 < float(family.get("clearance", 0.0)) <= 0.014
