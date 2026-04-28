from __future__ import annotations

import pytest

from evaluation.io import load_spec
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.models import OptimizationSpec


def _small_spec(path: str, *, population_size: int = 4, num_generations: int = 1) -> OptimizationSpec:
    payload = load_optimization_spec(path).to_dict()
    payload["algorithm"]["population_size"] = population_size
    payload["algorithm"]["num_generations"] = num_generations
    payload["algorithm"]["seed"] = 7
    return OptimizationSpec.from_dict(payload)


def _evaluation_spec(path: str, spec: OptimizationSpec):
    return load_spec(resolve_evaluation_spec_path(path, spec))


@pytest.mark.parametrize(
    "spec_path",
    [
        "scenarios/optimization/s1_typical_spea2_raw.yaml",
        "scenarios/optimization/s1_typical_moead_raw.yaml",
    ],
)
def test_s1_additional_raw_backbones_execute_smoke(spec_path: str) -> None:
    from optimizers.drivers.raw_driver import run_raw_optimization

    spec = _small_spec(spec_path, num_generations=2)
    run = run_raw_optimization(
        generate_benchmark_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
        evaluation_workers=1,
    )

    assert run.result.aggregate_metrics["optimizer_num_evaluations"] > 0
    assert run.result.aggregate_metrics["pareto_size"] > 0


@pytest.mark.parametrize(
    "spec_path",
    [
        "scenarios/optimization/s2_staged_spea2_raw.yaml",
        "scenarios/optimization/s2_staged_moead_raw.yaml",
    ],
)
def test_s2_additional_raw_backbones_execute_smoke(spec_path: str) -> None:
    from optimizers.drivers.raw_driver import run_raw_optimization

    spec = _small_spec(spec_path, num_generations=2)
    run = run_raw_optimization(
        generate_benchmark_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
        evaluation_workers=1,
    )

    assert run.result.aggregate_metrics["optimizer_num_evaluations"] > 0
    assert any(
        row.get("source") == "optimizer" and not row.get("solver_skipped", False)
        for row in run.result.history
    )


def test_raw_driver_normalizes_generation_indices_from_callback_boundaries() -> None:
    from optimizers.drivers.raw_driver import _assign_generation_indices_from_callback

    history = [
        {"evaluation_index": 1, "source": "baseline", "generation": 0},
        {"evaluation_index": 2, "source": "optimizer", "generation": 0},
        {"evaluation_index": 3, "source": "optimizer", "generation": 0},
        {"evaluation_index": 4, "source": "optimizer", "generation": 0},
        {"evaluation_index": 5, "source": "optimizer", "generation": 0},
        {"evaluation_index": 6, "source": "optimizer", "generation": 1},
        {"evaluation_index": 7, "source": "optimizer", "generation": 2},
        {"evaluation_index": 8, "source": "optimizer", "generation": 3},
        {"evaluation_index": 9, "source": "optimizer", "generation": 4},
    ]
    generation_rows = [
        {"generation_index": 1, "num_evaluations_so_far": 5},
        {"generation_index": 2, "num_evaluations_so_far": 9},
    ]

    _assign_generation_indices_from_callback(history, generation_rows)

    optimizer_generations = [row["generation"] for row in history if row["source"] == "optimizer"]
    assert optimizer_generations == [0, 0, 0, 0, 1, 1, 1, 1]
