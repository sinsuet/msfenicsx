from pathlib import Path

from evaluation.io import load_spec
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.models import OptimizationSpec
from optimizers.raw_backbones.registry import list_registered_backbones


def _raw_spec(*, seed: int = 7, population_size: int = 4, num_generations: int = 2) -> OptimizationSpec:
    payload = load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml").to_dict()
    payload["algorithm"]["population_size"] = population_size
    payload["algorithm"]["num_generations"] = num_generations
    payload["algorithm"]["seed"] = seed
    return OptimizationSpec.from_dict(payload)


def test_repository_has_no_panel_four_component_hot_cold_specs() -> None:
    assert not any(Path("scenarios").rglob("panel_four_component_hot_cold*.yaml"))


def test_readme_mentions_only_s1_typical_as_active_mainline() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    assert "s1_typical" in text
    assert "panel_four_component_hot_cold" not in text


def test_raw_backbone_registry_contains_first_batch_algorithms() -> None:
    assert list_registered_backbones() == [
        "moead",
        "nsga2",
        "spea2",
    ]


def test_raw_driver_dispatches_s1_typical_spec() -> None:
    spec_path = "scenarios/optimization/s1_typical_raw.yaml"
    spec = _raw_spec()
    run = run_raw_optimization(
        generate_benchmark_case(spec_path, spec),
        spec,
        load_spec(resolve_evaluation_spec_path(spec_path, spec)),
        spec_path=spec_path,
    )

    assert run.result.aggregate_metrics["num_evaluations"] > 0
    assert run.result.run_meta["optimization_spec_id"] == "s1_typical_nsga2_raw"


def test_raw_driver_finds_feasible_candidates_on_s1_typical() -> None:
    spec_path = "scenarios/optimization/s1_typical_raw.yaml"
    spec = _raw_spec(seed=11)
    run = run_raw_optimization(
        generate_benchmark_case(spec_path, spec),
        spec,
        load_spec(resolve_evaluation_spec_path(spec_path, spec)),
        spec_path=spec_path,
    )

    assert run.result.aggregate_metrics["feasible_rate"] > 0.0
    assert run.result.aggregate_metrics["first_feasible_eval"] is not None
    assert run.result.aggregate_metrics["pareto_size"] > 0


def test_raw_driver_supports_desktop_safe_parallel_evaluation_workers() -> None:
    spec_path = "scenarios/optimization/s1_typical_raw.yaml"

    for evaluation_workers in (1, 2):
        spec = _raw_spec(seed=17, population_size=4, num_generations=1)
        run = run_raw_optimization(
            generate_benchmark_case(spec_path, spec),
            spec,
            load_spec(resolve_evaluation_spec_path(spec_path, spec)),
            spec_path=spec_path,
            evaluation_workers=evaluation_workers,
        )

        assert run.result.aggregate_metrics["optimizer_num_evaluations"] > 0
        assert run.result.aggregate_metrics["first_feasible_eval"] is not None
        assert [row["evaluation_index"] for row in run.result.history] == list(
            range(1, len(run.result.history) + 1)
        )
