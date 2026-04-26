from pathlib import Path

import numpy as np
import pytest

import optimizers.problem as problem_module
from evaluation.io import load_spec
from optimizers.codec import extract_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.models import OptimizationSpec
from optimizers.problem import CHEAP_GEOMETRY_ISSUE_CONSTRAINT_ID, ThermalOptimizationProblem


SPEC_PATH = Path("scenarios/optimization/s1_typical_raw.yaml")
EVALUATION_SPEC_PATH = Path("scenarios/evaluation/s1_typical_eval.yaml")


class _ImmediateFuture:
    def __init__(self, result):
        self._result = result

    def result(self):
        return self._result


class _FakeExecutor:
    def __init__(self, *args, **kwargs):
        del args, kwargs
        self.futures = []

    def submit(self, fn, *args, **kwargs):
        future = _ImmediateFuture(fn(*args, **kwargs))
        self.futures.append(future)
        return future

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        del wait, cancel_futures


def _zero_constraint_reports(evaluation_spec: dict) -> list[dict]:
    return [
        {
            "constraint_id": item["constraint_id"],
            "metric": item["metric"],
            "actual": 0.0,
            "limit": 0.0,
            "relation": "<=",
            "margin": 0.0,
            "satisfied": True,
        }
        for item in evaluation_spec["constraints"]
    ]


def _impossible_overlap_spec() -> OptimizationSpec:
    payload = load_optimization_spec(SPEC_PATH).to_dict()
    payload["spec_meta"] = {
        "spec_id": "s1_typical_parallel_impossible_overlap",
        "description": "Parallel problem regression fixture with impossible overlap bounds.",
    }
    payload["design_variables"] = [
        {
            "variable_id": "c01_x",
            "path": "components[0].pose.x",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "c01_y",
            "path": "components[0].pose.y",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "c02_x",
            "path": "components[1].pose.x",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "c02_y",
            "path": "components[1].pose.y",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "sink_start",
            "path": "boundary_features[0].start",
            "lower_bound": 0.2,
            "upper_bound": 0.25,
        },
        {
            "variable_id": "sink_end",
            "path": "boundary_features[0].end",
            "lower_bound": 0.6,
            "upper_bound": 0.65,
        },
    ]
    return OptimizationSpec.from_dict(payload)


def test_problem_evaluate_vectors_commits_results_in_evaluation_index_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    optimization_spec = load_optimization_spec(SPEC_PATH)
    evaluation_spec = load_spec(EVALUATION_SPEC_PATH)
    base_case = generate_benchmark_case(SPEC_PATH, optimization_spec)
    vector = extract_decision_vector(base_case, optimization_spec)
    evaluation_payload = evaluation_spec.to_dict()
    objective_ids = [item["objective_id"] for item in evaluation_payload["objectives"]]
    call_count = {"value": 0}

    def _fake_worker(candidate_payload: dict, _evaluation_spec: dict) -> dict:
        call_count["value"] += 1
        peak_value = 310.0 - float(call_count["value"])
        gradient_value = 11.0 - float(call_count["value"])
        return {
            "success": True,
            "case_payload": candidate_payload,
            "solution_payload": {
                "schema_version": "1.0",
                "solution_meta": {
                    "case_id": candidate_payload["case_meta"]["case_id"],
                    "solution_id": f"{candidate_payload['case_meta']['case_id']}-solution-{call_count['value']}",
                },
                "solver_diagnostics": {"solver": "fake"},
                "field_records": {},
                "summary_metrics": {
                    "temperature_max": peak_value,
                    "temperature_gradient_rms": gradient_value,
                },
                "component_summaries": [],
                "provenance": {"source_case_id": candidate_payload["case_meta"]["case_id"]},
            },
                "evaluation_payload": {
                    "schema_version": "1.0",
                    "evaluation_meta": {
                        "report_id": f"{candidate_payload['case_meta']['case_id']}-report-{call_count['value']}",
                        "case_id": candidate_payload["case_meta"]["case_id"],
                        "solution_id": f"{candidate_payload['case_meta']['case_id']}-solution-{call_count['value']}",
                        "spec_id": evaluation_payload["spec_meta"]["spec_id"],
                    },
                    "feasible": True,
                    "metric_values": {
                        "summary.temperature_max": peak_value,
                        "summary.temperature_gradient_rms": gradient_value,
                    },
                    "objective_summary": [
                        {
                            "objective_id": evaluation_payload["objectives"][0]["objective_id"],
                            "metric": evaluation_payload["objectives"][0]["metric"],
                            "sense": evaluation_payload["objectives"][0]["sense"],
                            "value": peak_value,
                        },
                        {
                            "objective_id": evaluation_payload["objectives"][1]["objective_id"],
                            "metric": evaluation_payload["objectives"][1]["metric"],
                            "sense": evaluation_payload["objectives"][1]["sense"],
                            "value": gradient_value,
                        },
                    ],
                    "constraint_reports": _zero_constraint_reports(evaluation_payload),
                    "violations": [],
                    "derived_signals": {},
                "provenance": {},
            },
            "objective_values": {
                objective_ids[0]: peak_value,
                objective_ids[1]: gradient_value,
            },
            "constraint_values": {
                item["constraint_id"]: 0.0 for item in evaluation_payload["constraints"]
            },
            "field_exports": None,
        }

    monkeypatch.setattr(problem_module, "ProcessPoolExecutor", _FakeExecutor)
    monkeypatch.setattr(problem_module, "as_completed", lambda futures: list(reversed(list(futures))))
    monkeypatch.setattr(problem_module, "evaluate_candidate_payload", _fake_worker)

    problem = ThermalOptimizationProblem(
        base_case,
        optimization_spec,
        evaluation_spec,
        evaluation_workers=2,
    )

    records, objective_matrix, constraint_matrix = problem.evaluate_vectors(
        np.asarray([vector, vector], dtype=np.float64),
        source="optimizer",
    )

    assert [record["evaluation_index"] for record in records] == [1, 2]
    assert [record["evaluation_index"] for record in problem.history] == [1, 2]
    assert records[0]["objective_values"][objective_ids[0]] == pytest.approx(309.0)
    assert records[1]["objective_values"][objective_ids[0]] == pytest.approx(308.0)
    assert objective_matrix.shape == (2, len(evaluation_payload["objectives"]))
    assert constraint_matrix.shape == (2, problem.n_ieq_constr)
    assert all(record["constraint_values"][CHEAP_GEOMETRY_ISSUE_CONSTRAINT_ID] == 0.0 for record in records)


def test_problem_evaluate_vectors_skips_worker_dispatch_for_cheap_constraint_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_case = generate_benchmark_case(SPEC_PATH, load_optimization_spec(SPEC_PATH))
    optimization_spec = _impossible_overlap_spec()
    evaluation_spec = load_spec(EVALUATION_SPEC_PATH)
    vector = np.asarray([0.16, 0.16, 0.16, 0.16, 0.2, 0.65], dtype=np.float64)

    def _fail_if_called(*args, **kwargs):
        del args, kwargs
        raise AssertionError("worker evaluation should be skipped for cheap-constraint failures")

    monkeypatch.setattr(problem_module, "evaluate_candidate_payload", _fail_if_called)

    problem = ThermalOptimizationProblem(
        base_case,
        optimization_spec,
        evaluation_spec,
        evaluation_workers=2,
    )

    records, objective_matrix, constraint_matrix = problem.evaluate_vectors(
        np.asarray([vector], dtype=np.float64),
        source="optimizer",
    )

    assert records[0]["failure_reason"] == "cheap_constraint_violation"
    assert records[0]["solver_skipped"] is True
    assert records[0]["evaluation_index"] == 1
    assert objective_matrix.shape == (1, len(evaluation_spec.objectives))
    assert constraint_matrix.shape == (1, problem.n_ieq_constr)
    assert records[0]["constraint_values"][CHEAP_GEOMETRY_ISSUE_CONSTRAINT_ID] > 0.0
