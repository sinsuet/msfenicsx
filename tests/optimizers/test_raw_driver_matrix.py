from pathlib import Path

import pytest

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


def test_raw_nsga3_driver_finds_feasible_candidates_on_the_active_benchmark() -> None:
    run = run_raw_optimization_from_spec(
        Path("scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml")
    )

    assert run.result.aggregate_metrics["feasible_rate"] > 0.0
    assert run.result.aggregate_metrics["first_feasible_eval"] is not None
    assert run.result.aggregate_metrics["pareto_size"] > 0


def test_raw_nsga3_driver_never_uses_unseeded_tournament_tie_breaks(monkeypatch: pytest.MonkeyPatch) -> None:
    from pymoo.algorithms.moo import nsga3 as pymoo_nsga3

    original_compare = pymoo_nsga3.compare

    def guarded_compare(*args, **kwargs):
        if kwargs.get("random_state") is None:
            raise AssertionError("NSGA-III tournament tie-break called compare() without random_state.")
        return original_compare(*args, **kwargs)

    monkeypatch.setattr(pymoo_nsga3, "compare", guarded_compare)

    run = run_raw_optimization_from_spec(
        Path("scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml")
    )

    assert run.result.aggregate_metrics["num_evaluations"] > 0


@pytest.mark.parametrize(
    "spec_name",
    [
        "panel_four_component_hot_cold_ctaea_raw_b0.yaml",
        "panel_four_component_hot_cold_rvea_raw_b0.yaml",
        "panel_four_component_hot_cold_moead_raw_b0.yaml",
        "panel_four_component_hot_cold_cmopso_raw_b0.yaml",
    ],
)
def test_additional_raw_backbones_find_feasible_candidates_on_the_active_benchmark(spec_name: str) -> None:
    run = run_raw_optimization_from_spec(Path("scenarios/optimization") / spec_name)

    assert run.result.aggregate_metrics["feasible_rate"] > 0.0
    assert run.result.aggregate_metrics["first_feasible_eval"] is not None
    assert run.result.aggregate_metrics["pareto_size"] > 0
