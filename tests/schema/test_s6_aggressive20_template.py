from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


S6_TEMPLATE = Path("scenarios/templates/s6_aggressive20.yaml")


def _load() -> dict[str, Any]:
    return yaml.safe_load(S6_TEMPLATE.read_text(encoding="utf-8"))


def test_s6_template_identity_and_single_case_contract() -> None:
    payload = _load()

    assert payload["template_meta"]["template_id"] == "s6_aggressive20"
    assert "operating_case_profiles" not in payload
    assert len(payload["component_families"]) == 20
    assert len(payload["load_rules"]) == 20
    assert [family["family_id"] for family in payload["component_families"]] == [
        f"c{index:02d}" for index in range(1, 21)
    ]
    assert [rule["target_family"] for rule in payload["load_rules"]] == [
        f"c{index:02d}" for index in range(1, 21)
    ]


def test_s6_template_uses_top_edge_line_sink_with_aggressive_span() -> None:
    payload = _load()

    assert len(payload["boundary_feature_families"]) == 1
    sink = payload["boundary_feature_families"][0]
    assert sink["kind"] == "line_sink"
    assert sink["edge"] == "top"
    assert sink["sink_temperature"]["min"] == 290.5
    assert sink["transfer_coefficient"]["min"] == 7.5

    sink_span = float(sink["span"]["max"]) - float(sink["span"]["min"])
    assert 0.44 <= sink_span <= 0.46


def test_s6_template_matches_aggressive20_region_and_power_band() -> None:
    payload = _load()

    region = payload["placement_regions"][0]
    assert region["x_min"] == 0.05
    assert region["x_max"] == 0.95
    assert region["y_min"] == 0.04
    assert region["y_max"] == 0.73

    total_power = sum(float(rule["total_power"]) for rule in payload["load_rules"])
    assert 155.0 <= total_power <= 166.0
    assert all(rule.get("source_area_ratio") is not None for rule in payload["load_rules"])


def test_s6_template_declares_semantic_layout_metadata() -> None:
    payload = _load()

    hints = {family.get("placement_hint") for family in payload["component_families"]}
    assert {"adversarial_core", "center_mass", "left_edge", "right_edge", "bottom_band"} <= hints

    groups = {family.get("adjacency_group") for family in payload["component_families"]}
    assert {"primary-hot-cluster", "secondary-hot-lane", "routing-pressure", "service-band"} <= groups

    for family in payload["component_families"]:
        assert family.get("layout_tags")
        assert family.get("placement_hint")
        assert 0.0 < float(family.get("clearance", 0.0)) <= 0.014
