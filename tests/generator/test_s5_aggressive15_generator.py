from __future__ import annotations

from core.generator.layout_engine import place_components
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.geometry.layout_rules import component_within_domain, components_overlap
from optimizers.codec import extract_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec


TEMPLATE_PATH = "scenarios/templates/s5_aggressive15.yaml"
OPTIMIZATION_SPEC_PATH = "scenarios/optimization/s5_aggressive15_raw.yaml"


def test_s5_aggressive15_template_generates_fifteen_legal_components_for_seed_11() -> None:
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


def test_s5_aggressive15_top_sink_remains_on_the_upper_edge() -> None:
    template = load_template_model(TEMPLATE_PATH)

    sinks = [feature for feature in template.boundary_feature_families if feature["kind"] == "line_sink"]
    assert len(sinks) == 1
    assert sinks[0]["edge"] == "top"


def test_s5_aggressive15_decision_vector_layout_resolves_to_32_variables() -> None:
    spec = load_optimization_spec(OPTIMIZATION_SPEC_PATH)
    case = generate_benchmark_case(OPTIMIZATION_SPEC_PATH, spec)
    vector = extract_decision_vector(case, spec)

    assert case.case_meta["scenario_id"] == "s5_aggressive15"
    assert len(case.components) == 15
    assert vector.shape == (32,)
