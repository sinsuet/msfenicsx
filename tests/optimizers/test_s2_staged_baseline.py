from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest

from core.solver.nonlinear_solver import solve_case_artifacts
from evaluation.engine import evaluate_case_solution
from evaluation.io import load_spec
from optimizers.cheap_constraints import resolve_radiator_span_max
from optimizers.codec import extract_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.domain_state import build_spatial_motif_panel
from optimizers.problem import ThermalOptimizationProblem
from optimizers.repair import repair_case_payload_from_vector


RAW_SPEC_PATH = Path("scenarios/optimization/s2_staged_raw.yaml")
UNION_SPEC_PATH = Path("scenarios/optimization/s2_staged_union.yaml")
LLM_SPEC_PATH = Path("scenarios/optimization/s2_staged_llm.yaml")
EVALUATION_SPEC_PATH = Path("scenarios/evaluation/s2_staged_eval.yaml")


@lru_cache(maxsize=1)
def _baseline_outputs() -> dict[str, object]:
    optimization_spec = load_optimization_spec(RAW_SPEC_PATH)
    evaluation_spec = load_spec(EVALUATION_SPEC_PATH)
    base_case = generate_benchmark_case(RAW_SPEC_PATH, optimization_spec)
    baseline_vector = extract_decision_vector(base_case, optimization_spec)
    repaired_payload = repair_case_payload_from_vector(
        base_case,
        optimization_spec,
        baseline_vector,
        radiator_span_max=resolve_radiator_span_max(evaluation_spec.to_dict()),
    )
    generated_solution = solve_case_artifacts(base_case)["solution"]
    generated_evaluation = evaluate_case_solution(base_case, generated_solution, evaluation_spec).to_dict()
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)
    baseline = problem.evaluate_baseline()
    spatial_panel = build_spatial_motif_panel(
        decision_vector=baseline["decision_vector"],
        sink_budget_limit=problem.radiator_span_max,
        run_state={
            "peak_temperature": baseline["evaluation_report"]["metric_values"]["summary.temperature_max"],
            "temperature_gradient_rms": baseline["evaluation_report"]["metric_values"]["summary.temperature_gradient_rms"],
        },
    )
    problem.close()
    return {
        "generated_evaluation": generated_evaluation,
        "baseline": baseline,
        "spatial_panel": spatial_panel,
        "repaired_layout_metrics": repaired_payload["provenance"]["layout_metrics"],
    }


def test_s2_staged_specs_load_and_union_pool_matches_llm() -> None:
    raw = load_optimization_spec(RAW_SPEC_PATH).to_dict()
    union = load_optimization_spec(UNION_SPEC_PATH).to_dict()
    llm = load_optimization_spec(LLM_SPEC_PATH).to_dict()
    raw_design_vars = {item["variable_id"]: item for item in raw["design_variables"]}
    union_design_vars = {item["variable_id"]: item for item in union["design_variables"]}
    llm_design_vars = {item["variable_id"]: item for item in llm["design_variables"]}

    assert raw["benchmark_source"]["template_path"] == "scenarios/templates/s2_staged.yaml"
    assert raw["evaluation_protocol"]["evaluation_spec_path"] == "scenarios/evaluation/s2_staged_eval.yaml"
    assert union["operator_control"]["operator_pool"] == llm["operator_control"]["operator_pool"]
    assert union["algorithm"]["profile_path"] == "scenarios/optimization/profiles/s2_staged_union.yaml"
    assert llm["algorithm"]["profile_path"] == "scenarios/optimization/profiles/s2_staged_union.yaml"
    for variable_id in ("c02_x", "c04_x", "c06_x", "c12_x"):
        assert raw_design_vars[variable_id]["lower_bound"] == pytest.approx(0.45)
        assert union_design_vars[variable_id]["lower_bound"] == pytest.approx(0.45)
        assert llm_design_vars[variable_id]["lower_bound"] == pytest.approx(0.45)
    assert raw_design_vars["c02_y"]["lower_bound"] == pytest.approx(0.11)
    assert union_design_vars["c02_y"]["lower_bound"] == pytest.approx(0.11)
    assert llm_design_vars["c02_y"]["lower_bound"] == pytest.approx(0.11)


def test_s2_staged_generated_baseline_is_infeasible_before_repair_acceptance() -> None:
    generated = _baseline_outputs()["generated_evaluation"]
    by_constraint = {
        report["constraint_id"]: report
        for report in generated["constraint_reports"]
    }

    assert generated["feasible"] is False
    assert "radiator_span_budget" in by_constraint
    assert "c02_peak_temperature_limit" in by_constraint


def test_s2_staged_repaired_baseline_matches_acceptance_window() -> None:
    baseline = _baseline_outputs()["baseline"]
    spatial_panel = _baseline_outputs()["spatial_panel"]
    repaired_layout_metrics = _baseline_outputs()["repaired_layout_metrics"]
    positives = {
        constraint_id: float(value)
        for constraint_id, value in baseline["constraint_values"].items()
        if float(value) > 1.0e-9
    }
    total_violation = sum(positives.values())

    assert baseline["feasible"] is False
    assert set(positives) == {"c02_peak_temperature_limit"}
    assert 2.5 <= total_violation <= 4.0
    assert spatial_panel["hotspot_inside_sink_window"] is False
    assert repaired_layout_metrics["nearest_neighbor_gap_mean"] <= 0.06
    assert spatial_panel["hottest_cluster_compactness"] <= 0.13
    assert spatial_panel["sink_budget_bucket"] in {"tight", "full_sink"}
