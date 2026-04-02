from pathlib import Path

import yaml


def test_s1_typical_template_has_expected_shape() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    assert payload["template_meta"]["template_id"] == "s1_typical"
    assert len(payload["component_families"]) == 15
    assert "operating_case_profiles" not in payload

    boundary_feature_families = payload["boundary_feature_families"]
    assert len(boundary_feature_families) == 1
    boundary_feature = boundary_feature_families[0]
    assert boundary_feature["kind"] == "line_sink"
    assert boundary_feature["edge"] == "top"

    load_rules = payload["load_rules"]
    assert len(load_rules) == 15
    load_target_ids = [load_rule["target_family"] for load_rule in load_rules]
    assert load_target_ids == [f"c{i:02d}" for i in range(1, 16)]


def test_s1_typical_template_declares_mixed_shape_component_families() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    shapes = {family["shape"] for family in payload["component_families"]}

    assert "rect" in shapes
    assert "slot" in shapes or "capsule" in shapes
    assert "circle" in shapes or "polygon" in shapes


def test_s1_typical_template_declares_layout_semantics() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    for family in payload["component_families"]:
        assert "layout_tags" in family
        assert "placement_hint" in family
