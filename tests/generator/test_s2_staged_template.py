from __future__ import annotations

from core.generator.layout_engine import place_components
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.geometry.layout_rules import component_within_domain, components_overlap


TEMPLATE_PATH = "scenarios/templates/s2_staged.yaml"
STAGED_CORE = {"x_min": 0.48, "x_max": 0.86, "y_min": 0.14, "y_max": 0.50}
HOT_CLUSTER_FAMILIES = ("c02", "c04", "c06", "c12")


def test_s2_staged_template_loads_with_expected_identity() -> None:
    template = load_template_model(TEMPLATE_PATH)
    assert template.template_meta["template_id"] == "s2_staged"
    assert len(template.component_families) == 15


def test_s2_staged_template_generates_fifteen_legal_components_for_seed_11() -> None:
    template = load_template_model(TEMPLATE_PATH)
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)

    assert len(placed) == 15
    assert all(component_within_domain(component, template.panel_domain) for component in placed)
    for index, component in enumerate(placed):
        for other in placed[index + 1 :]:
            assert not components_overlap(component, other), (
                f"overlap between {component['component_id']} and {other['component_id']}"
            )


def test_s2_staged_hot_cluster_families_land_inside_shifted_compact_core() -> None:
    template = load_template_model(TEMPLATE_PATH)
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)
    by_family = {component["family_id"]: component for component in placed}

    for family_id in HOT_CLUSTER_FAMILIES:
        x_value = float(by_family[family_id]["pose"]["x"])
        y_value = float(by_family[family_id]["pose"]["y"])
        assert STAGED_CORE["x_min"] <= x_value <= STAGED_CORE["x_max"], (
            f"{family_id} x={x_value} outside staged compact-core x-band"
        )
        assert STAGED_CORE["y_min"] <= y_value <= STAGED_CORE["y_max"], (
            f"{family_id} y={y_value} outside staged compact-core y-band"
        )
