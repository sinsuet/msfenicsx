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


def test_s1_typical_template_declares_legacy_aligned_layout_strategy() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    layout_strategy = payload["generation_rules"]["layout_strategy"]

    assert layout_strategy["kind"] == "legacy_aligned_dense_core_v1"
    assert {"dense_core", "top_sink_band", "left_io_edge", "right_service_edge"} <= set(layout_strategy["zones"])


def test_s1_typical_template_default_sink_span_stays_within_budget() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    sink_feature = payload["boundary_feature_families"][0]
    default_span = float(sink_feature["span"]["max"]) - float(sink_feature["span"]["min"])

    assert default_span <= 0.48


def test_s1_typical_template_declares_source_area_ratio_for_high_power_families() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    source_ratios = {
        rule["target_family"]: rule.get("source_area_ratio")
        for rule in payload["load_rules"]
    }

    assert source_ratios["c02"] is not None
    assert source_ratios["c04"] is not None
    assert source_ratios["c06"] is not None


def test_s1_typical_template_declares_source_area_ratio_for_all_families() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    source_ratios = {
        rule["target_family"]: rule.get("source_area_ratio")
        for rule in payload["load_rules"]
    }

    assert source_ratios.keys() == {f"c{i:02d}" for i in range(1, 16)}
    assert all(source_ratios[family_id] is not None for family_id in source_ratios)


def test_s1_typical_template_declares_explicit_background_boundary_cooling() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    physics = payload["physics"]
    background = physics["background_boundary_cooling"]

    assert physics["ambient_temperature"] > 0.0
    assert background["transfer_coefficient"] > 0.0
    assert 0.0 < background["emissivity"] <= 1.0


def test_s1_typical_template_realism_v2_tightens_generation_zones() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    zones = payload["generation_rules"]["layout_strategy"]["zones"]
    dense_core = zones["dense_core"]
    top_sink_band = zones["top_sink_band"]

    tolerance = 1.0e-9

    assert float(dense_core["x_max"]) - float(dense_core["x_min"]) <= 0.60 + tolerance
    assert float(dense_core["y_max"]) - float(dense_core["y_min"]) <= 0.42 + tolerance
    assert float(top_sink_band["x_max"]) - float(top_sink_band["x_min"]) <= 0.64 + tolerance


def test_s1_typical_template_realism_v2_uses_lower_conductivity_and_more_localized_hot_sources() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    materials = {item["material_id"]: item for item in payload["material_rules"]}
    source_ratios = {
        rule["target_family"]: rule.get("source_area_ratio")
        for rule in payload["load_rules"]
    }

    assert materials["panel_substrate"]["conductivity"] == 3.0
    assert materials["electronics_housing"]["conductivity"] == 12.0
    assert source_ratios["c02"] <= 0.18
    assert source_ratios["c04"] <= 0.18
    assert source_ratios["c06"] <= 0.18


def test_s1_typical_template_realism_v2_expands_selected_component_footprints() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    by_family = {family["family_id"]: family for family in payload["component_families"]}

    assert by_family["c10"]["geometry"]["width"]["min"] > 0.14
    assert by_family["c11"]["geometry"]["length"]["min"] > 0.24
    assert by_family["c15"]["geometry"]["radius"]["min"] > 0.07
