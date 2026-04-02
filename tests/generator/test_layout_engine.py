from core.generator.layout_engine import place_components
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


def test_place_components_keeps_anchor_families_in_preferred_bands() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    sampled = sample_template_parameters(template, seed=11)

    placed_components = place_components(
        template=template,
        sampled_components=sampled["components"],
        seed=11,
    )
    by_family = {component["family_id"]: component for component in placed_components}

    assert by_family["c12"]["pose"]["y"] >= 0.58
    assert by_family["c11"]["pose"]["x"] <= 0.18
    assert by_family["c08"]["pose"]["x"] >= 0.82
    assert by_family["c10"]["pose"]["y"] <= 0.18


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

    assert mean_y >= 0.56
