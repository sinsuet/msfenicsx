from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model


def test_sample_template_parameters_is_deterministic_for_fixed_seed() -> None:
    template = load_template_model("scenarios/templates/panel_radiation_baseline.yaml")

    sample_a = sample_template_parameters(template, seed=7)
    sample_b = sample_template_parameters(template, seed=7)

    assert sample_a == sample_b
