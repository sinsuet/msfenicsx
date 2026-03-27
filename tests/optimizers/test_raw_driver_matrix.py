from pathlib import Path

from optimizers.drivers.raw_driver import run_raw_optimization_from_spec
from optimizers.raw_backbones.registry import list_registered_backbones


def test_raw_backbone_registry_contains_first_batch_algorithms() -> None:
    assert list_registered_backbones() == [
        "cmopso",
        "ctaea",
        "moead",
        "nsga2",
        "nsga3",
        "rvea",
    ]


def test_raw_driver_dispatches_nsga2_and_nsga3_specs() -> None:
    optimization_specs_root = Path("scenarios/optimization")

    for spec_name in [
        "panel_four_component_hot_cold_nsga2_raw_b0.yaml",
        "panel_four_component_hot_cold_nsga3_raw_b0.yaml",
    ]:
        run = run_raw_optimization_from_spec(optimization_specs_root / spec_name)
        assert run.result.aggregate_metrics["num_evaluations"] > 0
        assert run.result.run_meta["optimization_spec_id"].endswith("-raw-b0")
