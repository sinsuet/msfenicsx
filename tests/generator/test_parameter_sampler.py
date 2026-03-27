from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model


def test_sample_template_parameters_is_deterministic_for_fixed_seed() -> None:
    template = load_template_model("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml")

    sample_a = sample_template_parameters(template, seed=7)
    sample_b = sample_template_parameters(template, seed=7)

    assert sample_a == sample_b


def test_benchmark_template_samples_four_fixed_roles() -> None:
    template = load_template_model("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml")

    sample = sample_template_parameters(template, seed=11)
    family_ids = [component["family_id"] for component in sample["components"]]

    assert family_ids == ["processor", "rf_power_amp", "obc", "battery_pack"]
