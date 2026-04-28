from __future__ import annotations

from pathlib import Path

import yaml


TEMPLATE_PATH = Path("scenarios/templates/s5_aggressive15.yaml")


def _load_template() -> dict:
    with TEMPLATE_PATH.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_s5_aggressive15_template_contract() -> None:
    assert TEMPLATE_PATH.exists()

    template = _load_template()
    families = template["component_families"]
    loads = template["load_rules"]

    assert template["template_meta"]["template_id"] == "s5_aggressive15"
    assert "operating_case_profiles" not in template
    assert len(families) == 15
    assert len(loads) == 15
    assert [family["family_id"] for family in families] == [f"c{index:02d}" for index in range(1, 16)]
    assert [load["target_family"] for load in loads] == [f"c{index:02d}" for index in range(1, 16)]


def test_s5_aggressive15_component_contract() -> None:
    template = _load_template()

    for family in template["component_families"]:
        assert family["count_range"] == {"min": 1, "max": 1}
        assert family["placement_hint"]
        assert family["layout_tags"]
        assert family["clearance"] > 0


def test_s5_aggressive15_sink_and_power_contract() -> None:
    template = _load_template()

    sinks = [feature for feature in template["boundary_feature_families"] if feature["kind"] == "line_sink"]
    assert len(sinks) == 1
    assert sinks[0]["edge"] == "top"
    assert 0.42 <= sinks[0]["span"]["max"] - sinks[0]["span"]["min"] <= 0.44

    total_power = sum(float(load["total_power"]) for load in template["load_rules"])
    assert 138.0 <= total_power <= 146.0
