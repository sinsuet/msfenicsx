import pytest

from core.generator.layout_engine import _components_conflict_with_clearance, place_components
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.geometry.layout_rules import component_within_domain, components_overlap


def test_place_components_produces_non_overlapping_layout_inside_domain() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    sampled = sample_template_parameters(template, seed=5)

    placed_components = place_components(
        template=template,
        sampled_components=sampled["components"],
        seed=5,
    )

    assert len(placed_components) == len(sampled["components"])
    assert all(component_within_domain(component, template.panel_domain) for component in placed_components)
    for index, component in enumerate(placed_components):
        for other_component in placed_components[index + 1 :]:
            assert not components_overlap(component, other_component)


def test_place_components_keeps_v3_anchor_families_inside_tighter_zones() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    sampled = sample_template_parameters(template, seed=11)

    placed_components = place_components(
        template=template,
        sampled_components=sampled["components"],
        seed=11,
    )
    by_family = {component["family_id"]: component for component in placed_components}

    assert by_family["c12"]["pose"]["y"] >= 0.60
    assert by_family["c11"]["pose"]["x"] <= 0.17
    assert by_family["c08"]["pose"]["x"] >= 0.83


def test_place_components_groups_sink_aware_components_near_top_band() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    sampled = sample_template_parameters(template, seed=11)

    placed_components = place_components(
        template=template,
        sampled_components=sampled["components"],
        seed=11,
    )
    by_family = {component["family_id"]: component for component in placed_components}
    top_band_families = ("c02", "c04", "c06", "c12")
    mean_y = sum(float(by_family[family_id]["pose"]["y"]) for family_id in top_band_families) / len(top_band_families)

    assert mean_y >= 0.54


def test_place_components_generates_all_components_for_calibration_seed_sample() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")

    for seed in (11, 17, 23, 29, 31):
        sampled = sample_template_parameters(template, seed=seed)
        placed_components = place_components(
            template=template,
            sampled_components=sampled["components"],
            seed=seed,
        )
        assert len(placed_components) == 15


def test_components_conflict_with_clearance_detects_nearby_non_overlapping_parts() -> None:
    left = {
        "component_id": "c01-001",
        "family_id": "c01",
        "role": "left",
        "shape": "rect",
        "pose": {"x": 0.20, "y": 0.20, "rotation_deg": 0.0},
        "geometry": {"width": 0.10, "height": 0.10},
        "material_ref": "electronics_housing",
    }
    right = {
        "component_id": "c02-001",
        "family_id": "c02",
        "role": "right",
        "shape": "rect",
        "pose": {"x": 0.31, "y": 0.20, "rotation_deg": 0.0},
        "geometry": {"width": 0.10, "height": 0.10},
        "material_ref": "electronics_housing",
    }
    family_profiles = {
        "c01": {"clearance": 0.025},
        "c02": {"clearance": 0.025},
    }

    assert not components_overlap(left, right)
    assert _components_conflict_with_clearance(left, right, family_profiles)


def test_strategy_regions_for_profile_prefers_adversarial_core_for_bottom_band() -> None:
    from core.generator.layout_engine import _strategy_regions_for_profile

    layout_strategy = {
        "kind": "s2_adversarial_v1",
        "zones": {
            "active_deck": {"x_min": 0.08, "x_max": 0.92, "y_min": 0.08, "y_max": 0.68},
            "adversarial_core": {"x_min": 0.15, "x_max": 0.85, "y_min": 0.10, "y_max": 0.35},
            "top_sink_band": {"x_min": 0.20, "x_max": 0.80, "y_min": 0.55, "y_max": 0.68},
        },
    }
    profile = {"placement_hint": "bottom_band"}
    regions = _strategy_regions_for_profile(layout_strategy, profile)

    assert len(regions) == 1
    assert regions[0] == {"x_min": 0.15, "x_max": 0.85, "y_min": 0.10, "y_max": 0.35}


def test_strategy_regions_for_profile_falls_back_to_derived_bottom_band_without_adversarial_core() -> None:
    from core.generator.layout_engine import _strategy_regions_for_profile

    layout_strategy = {
        "kind": "legacy_aligned_dense_core_v1",
        "zones": {
            "active_deck": {"x_min": 0.12, "x_max": 0.88, "y_min": 0.10, "y_max": 0.67},
            "dense_core": {"x_min": 0.22, "x_max": 0.78, "y_min": 0.17, "y_max": 0.56},
        },
    }
    profile = {"placement_hint": "bottom_band"}
    regions = _strategy_regions_for_profile(layout_strategy, profile)

    assert len(regions) == 1
    region = regions[0]
    assert region["x_min"] > 0.12 - 1e-6
    assert region["x_max"] < 0.88 + 1e-6
    assert region["y_min"] < region["y_max"]
