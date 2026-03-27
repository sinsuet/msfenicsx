from evaluation.io import load_multicase_spec
from optimizers.io import load_optimization_spec
from optimizers.pymoo_driver import run_multicase_optimization


def test_run_multicase_optimization_produces_pareto_front() -> None:
    evaluation_spec = load_multicase_spec("scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml")
    optimization_spec = load_optimization_spec("scenarios/optimization/reference_hot_cold_nsga2.yaml")

    run = run_multicase_optimization(
        base_cases={
            "hot": "scenarios/manual/reference_case_hot.yaml",
            "cold": "scenarios/manual/reference_case_cold.yaml",
        },
        optimization_spec=optimization_spec,
        evaluation_spec=evaluation_spec,
    )

    assert run.result.aggregate_metrics["num_evaluations"] >= 4
    assert run.result.aggregate_metrics["pareto_size"] >= 1
    assert run.result.pareto_front
    assert "min_hot_peak" in run.result.representative_candidates
    assert "min_resource_proxy" in run.result.representative_candidates
    assert {"hot", "cold"} <= set(run.result.history[0]["case_reports"])
    assert run.representative_artifacts["min_hot_peak"].evaluation is not None

