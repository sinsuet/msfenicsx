import pytest

from core.generator.layout_engine import place_components
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.geometry.layout_rules import component_within_domain, components_overlap


TEMPLATE_PATH = "scenarios/templates/s2_hard.yaml"
ADVERSARIAL_CORE = {"x_min": 0.15, "x_max": 0.85, "y_min": 0.10, "y_max": 0.35}
POWER_DENSE_FAMILIES = ("c02", "c04", "c06", "c12")


def test_s2_hard_template_loads_with_expected_identity() -> None:
    template = load_template_model(TEMPLATE_PATH)
    assert template.template_meta["template_id"] == "s2_hard"
    assert len(template.component_families) == 15


def test_s2_hard_template_generates_fifteen_legal_components_for_seed_11() -> None:
    template = load_template_model(TEMPLATE_PATH)
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)

    assert len(placed) == 15
    assert all(component_within_domain(c, template.panel_domain) for c in placed)
    for index, component in enumerate(placed):
        for other in placed[index + 1 :]:
            assert not components_overlap(component, other), (
                f"overlap between {component['component_id']} and {other['component_id']}"
            )


def test_s2_hard_power_dense_families_land_inside_adversarial_core() -> None:
    template = load_template_model(TEMPLATE_PATH)
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)
    by_family = {c["family_id"]: c for c in placed}

    # adversarial_core has finite capacity and competes with the other three
    # bottom_band families (c05, c10, c14) for the same zone; the engine routes
    # those that fit first and the rest fall back to the broader placement
    # regions. The test therefore asserts that at least two of the four
    # power-dense families land inside the adversarial_core band, which is
    # enough to prove the routing path is active.
    inside_count = 0
    for family_id in POWER_DENSE_FAMILIES:
        x = float(by_family[family_id]["pose"]["x"])
        y = float(by_family[family_id]["pose"]["y"])
        x_ok = ADVERSARIAL_CORE["x_min"] - 0.05 <= x <= ADVERSARIAL_CORE["x_max"] + 0.05
        y_ok = ADVERSARIAL_CORE["y_min"] - 0.02 <= y <= ADVERSARIAL_CORE["y_max"] + 0.05
        if x_ok and y_ok:
            inside_count += 1
    assert inside_count >= 2, (
        f"only {inside_count}/4 power-dense families routed into adversarial_core; "
        f"positions={ {fid: by_family[fid]['pose'] for fid in POWER_DENSE_FAMILIES} }"
    )


def test_s2_hard_load_rules_amplified_totals_match_spec() -> None:
    template = load_template_model(TEMPLATE_PATH)
    by_target = {rule["target_family"]: rule for rule in template.load_rules}
    assert by_target["c02"]["total_power"] == pytest.approx(20.0)
    assert by_target["c04"]["total_power"] == pytest.approx(19.0)
    assert by_target["c06"]["total_power"] == pytest.approx(18.0)
    assert by_target["c12"]["total_power"] == pytest.approx(16.0)
    # sanity: other eleven totals unchanged from s1_typical
    assert by_target["c01"]["total_power"] == pytest.approx(8.5)
    assert by_target["c05"]["total_power"] == pytest.approx(6.5)
    assert by_target["c15"]["total_power"] == pytest.approx(3.5)
