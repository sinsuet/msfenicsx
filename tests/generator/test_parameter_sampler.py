from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model


def test_sample_template_parameters_is_deterministic_for_fixed_seed() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")

    sample_a = sample_template_parameters(template, seed=7)
    sample_b = sample_template_parameters(template, seed=7)

    assert sample_a == sample_b


def test_s1_typical_template_samples_fifteen_fixed_component_families() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")

    sample = sample_template_parameters(template, seed=11)
    family_ids = [component["family_id"] for component in sample["components"]]

    assert family_ids == [f"c{i:02d}" for i in range(1, 16)]
