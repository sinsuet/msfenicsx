import pytest

from evaluation.io import load_multicase_spec
from optimizers.io import generate_benchmark_cases, load_optimization_spec
from optimizers.pymoo_driver import run_multicase_optimization


SPEC_PATH = "scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml"


@pytest.fixture(scope="module")
def b0_run():
    optimization_spec = load_optimization_spec(SPEC_PATH)
    evaluation_spec = load_multicase_spec("scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml")
    base_cases = generate_benchmark_cases(SPEC_PATH, optimization_spec)
    return run_multicase_optimization(
        base_cases=base_cases,
        optimization_spec=optimization_spec,
        evaluation_spec=evaluation_spec,
    )


def test_b0_driver_optimizes_three_components_and_radiator_interval(b0_run) -> None:
    variable_ids = set(b0_run.result.history[0]["decision_vector"])

    assert variable_ids == {
        "processor_x",
        "processor_y",
        "rf_power_amp_x",
        "rf_power_amp_y",
        "battery_pack_x",
        "battery_pack_y",
        "radiator_start",
        "radiator_end",
    }
    assert set(b0_run.result.run_meta["base_case_ids"]) == {"hot", "cold"}
    assert {"hot", "cold"} <= set(b0_run.result.history[0]["case_reports"])


def test_b0_baseline_records_infeasible_starting_point(b0_run) -> None:
    assert b0_run.result.baseline_candidates[0]["feasible"] is False


def test_b0_driver_finds_feasible_candidates_and_nonempty_pareto_front(b0_run) -> None:
    assert b0_run.result.aggregate_metrics["feasible_rate"] > 0.0
    assert b0_run.result.aggregate_metrics["first_feasible_eval"] is not None
    assert b0_run.result.aggregate_metrics["pareto_size"] > 0
    assert b0_run.result.pareto_front
    assert b0_run.result.representative_candidates


def test_active_optimizer_spec_is_plain_nsga2() -> None:
    spec = load_optimization_spec(SPEC_PATH)

    assert spec.algorithm["family"] == "genetic"
    assert spec.algorithm["backbone"] == "nsga2"
    assert spec.algorithm["mode"] == "raw"
    assert spec.operator_control is None


def test_active_result_contract_has_no_operator_usage_metrics(b0_run) -> None:
    assert "operator_usage" not in b0_run.result.aggregate_metrics
    assert all("operator_id" not in entry for entry in b0_run.result.history)
