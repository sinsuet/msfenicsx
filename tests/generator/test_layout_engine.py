from core.generator.layout_engine import place_components
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.geometry.layout_rules import component_within_domain, components_overlap


def test_place_components_produces_non_overlapping_layout_inside_domain() -> None:
    template = load_template_model("scenarios/templates/panel_radiation_baseline.yaml")
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
