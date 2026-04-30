from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

from optimizers.artifacts import _coerce_operator_trace_rows, write_optimization_artifacts
from optimizers.models import OptimizationResult
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow
from optimizers.traces.correlation import format_decision_id


def _candidate_contract(decision_vector: dict[str, float], *, solver_skipped: bool = False) -> dict:
    return {
        "proposal_decision_vector": dict(decision_vector),
        "evaluated_decision_vector": dict(decision_vector),
        "decision_vector": dict(decision_vector),
        "legality_policy_id": "minimal_canonicalization",
        "vector_transform_codes": [],
        "solver_skipped": solver_skipped,
        "cheap_constraint_issues": [],
    }


def _fake_union_run() -> SimpleNamespace:
    history = [
        {
            "evaluation_index": 1,
            "source": "baseline",
            "feasible": False,
            **_candidate_contract({"c01_x": 0.2, "c01_y": 0.3}),
            "objective_values": {
                "minimize_peak_temperature": 320.0,
                "minimize_temperature_gradient_rms": 12.0,
            },
            "constraint_values": {"radiator_span_budget": 0.05},
            "evaluation_report": {"evaluation_meta": {"case_id": "s1_typical-case-001"}, "feasible": False},
        },
        {
            "evaluation_index": 2,
            "source": "optimizer",
            "feasible": True,
            **_candidate_contract({"c01_x": 0.25, "c01_y": 0.35}),
            "objective_values": {
                "minimize_peak_temperature": 300.0,
                "minimize_temperature_gradient_rms": 8.5,
            },
            "constraint_values": {"radiator_span_budget": 0.0},
            "evaluation_report": {"evaluation_meta": {"case_id": "s1_typical-case-001"}, "feasible": True},
        },
    ]
    result_payload = {
        "schema_version": "1.0",
        "run_meta": {
            "run_id": "s1-typical-union-run",
            "base_case_id": "s1_typical-case-001",
            "optimization_spec_id": "s1-typical-nsga2-union",
            "evaluation_spec_id": "s1_typical_eval",
            "benchmark_seed": 11,
            "algorithm_seed": 7,
        },
        "baseline_candidates": [history[0]],
        "pareto_front": [history[1]],
        "representative_candidates": {},
        "aggregate_metrics": {
            "num_evaluations": len(history),
            "feasible_rate": 0.5,
            "first_feasible_eval": 2,
            "pareto_size": 1,
        },
        "history": history,
        "provenance": {
            "benchmark_source": {"seed": 11},
            "source_case_id": "s1_typical-case-001",
            "source_optimization_spec_id": "s1-typical-nsga2-union",
            "source_evaluation_spec_id": "s1_typical_eval",
        },
    }
    return SimpleNamespace(
        result=OptimizationResult.from_dict(result_payload),
        representative_artifacts={},
        controller_trace=[
            ControllerTraceRow(
                generation_index=1,
                evaluation_index=2,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("native_sbx_pm", "local_refine"),
                selected_operator_id="local_refine",
                phase="prefeasible_progress",
                rationale="fallback legacy row",
                metadata={"fallback_used": False},
            )
        ],
        operator_trace=[
            OperatorTraceRow(
                generation_index=1,
                evaluation_index=2,
                operator_id="local_refine",
                parent_count=2,
                parent_vectors=((0.2, 0.3), (0.24, 0.34)),
                proposal_vector=(0.25, 0.35),
                metadata={},
            )
        ],
        generation_summary_rows=[],
        llm_request_trace=[{"evaluation_index": 2, "system_prompt": "legacy system"}],
        llm_response_trace=[{"evaluation_index": 2, "response_text": "legacy response"}],
        llm_reflection_trace=None,
        llm_metrics={"elapsed_seconds_total": 1.2, "elapsed_seconds_avg": 1.2},
        controller_attempt_trace=[],
        operator_attempt_trace=[],
    )


def test_write_optimization_artifacts_preserves_live_llm_trace_sidecars(tmp_path: Path) -> None:
    output_root = tmp_path / "llm_run"
    traces_root = output_root / "traces"
    traces_root.mkdir(parents=True, exist_ok=True)
    controller_row = {
        "decision_id": "g001-e0002-d00",
        "phase": "prefeasible_progress",
        "operator_selected": "local_refine",
        "operator_pool_snapshot": ["native_sbx_pm", "local_refine"],
        "input_state_digest": "abc123",
        "prompt_ref": "prompts/request.md",
        "rationale": "use local refinement",
        "fallback_used": False,
        "latency_ms": 120.0,
    }
    request_row = {
        "decision_id": "g001-e0002-d00",
        "prompt_ref": "prompts/request.md",
        "model": "GPT-5.4",
        "http_status": None,
        "retries": 0,
        "latency_ms": 120.0,
    }
    response_row = {
        "decision_id": "g001-e0002-d00",
        "response_ref": "prompts/response.md",
        "model": "GPT-5.4",
        "tokens": {},
        "finish_reason": None,
        "http_status": None,
        "retries": 0,
        "latency_ms": 120.0,
    }
    (traces_root / "controller_trace.jsonl").write_text(json.dumps(controller_row) + "\n", encoding="utf-8")
    (traces_root / "llm_request_trace.jsonl").write_text(json.dumps(request_row) + "\n", encoding="utf-8")
    (traces_root / "llm_response_trace.jsonl").write_text(json.dumps(response_row) + "\n", encoding="utf-8")

    write_optimization_artifacts(
        output_root,
        _fake_union_run(),
        mode_id="llm",
        seed=11,
        objective_definitions=[
            {"objective_id": "minimize_peak_temperature", "metric": "summary.temperature_max", "sense": "minimize"},
            {
                "objective_id": "minimize_temperature_gradient_rms",
                "metric": "summary.temperature_gradient_rms",
                "sense": "minimize",
            },
        ],
    )

    assert json.loads((traces_root / "controller_trace.jsonl").read_text(encoding="utf-8").splitlines()[0]) == controller_row
    assert json.loads((traces_root / "llm_request_trace.jsonl").read_text(encoding="utf-8").splitlines()[0]) == request_row
    assert json.loads((traces_root / "llm_response_trace.jsonl").read_text(encoding="utf-8").splitlines()[0]) == response_row
    assert (traces_root / "operator_trace.jsonl").exists()
    assert not (output_root / "controller_trace.json").exists()
    assert not (output_root / "operator_trace.json").exists()
    assert not (output_root / "llm_metrics.json").exists()


def test_write_optimization_artifacts_refreshes_llm_trace_statuses_from_memory(tmp_path: Path) -> None:
    output_root = tmp_path / "llm_run_refreshed"
    traces_root = output_root / "traces"
    traces_root.mkdir(parents=True, exist_ok=True)
    stale_request_row = {
        "decision_id": "g001-e0002-d00",
        "prompt_ref": "prompts/request.md",
        "accepted_for_evaluation": False,
        "accepted_evaluation_indices": [],
        "accepted_evaluation_index": None,
    }
    stale_response_row = {
        "decision_id": "g001-e0002-d00",
        "response_ref": "prompts/response.md",
        "accepted_for_evaluation": False,
        "accepted_evaluation_indices": [],
        "accepted_evaluation_index": None,
    }
    (traces_root / "controller_trace.jsonl").write_text(
        json.dumps(
            {
                "decision_id": "g001-e0002-d00",
                "phase": "prefeasible_progress",
                "operator_selected": "local_refine",
                "operator_pool_snapshot": ["native_sbx_pm", "local_refine"],
                "input_state_digest": "abc123",
                "prompt_ref": "prompts/request.md",
                "rationale": "use local refinement",
                "fallback_used": False,
                "latency_ms": 120.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (traces_root / "llm_request_trace.jsonl").write_text(json.dumps(stale_request_row) + "\n", encoding="utf-8")
    (traces_root / "llm_response_trace.jsonl").write_text(json.dumps(stale_response_row) + "\n", encoding="utf-8")
    run = _fake_union_run()
    run.llm_request_trace = [
        {
            **stale_request_row,
            "accepted_for_evaluation": True,
            "accepted_evaluation_indices": [2],
            "accepted_evaluation_index": 2,
            "rejection_reason": "",
        }
    ]
    run.llm_response_trace = [
        {
            **stale_response_row,
            "selected_operator_id": "local_refine",
            "accepted_for_evaluation": True,
            "accepted_evaluation_indices": [2],
            "accepted_evaluation_index": 2,
            "rejection_reason": "",
            "raw_payload": {"selected_operator_id": "local_refine"},
        }
    ]

    write_optimization_artifacts(
        output_root,
        run,
        mode_id="llm",
        seed=11,
        objective_definitions=[
            {"objective_id": "minimize_peak_temperature", "metric": "summary.temperature_max", "sense": "minimize"},
            {
                "objective_id": "minimize_temperature_gradient_rms",
                "metric": "summary.temperature_gradient_rms",
                "sense": "minimize",
            },
        ],
    )

    request_row = json.loads((traces_root / "llm_request_trace.jsonl").read_text(encoding="utf-8").splitlines()[0])
    response_row = json.loads((traces_root / "llm_response_trace.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert request_row["accepted_for_evaluation"] is True
    assert request_row["accepted_evaluation_indices"] == [2]
    assert response_row["accepted_for_evaluation"] is True
    assert response_row["accepted_evaluation_index"] == 2
    assert "raw_payload" not in response_row


def test_write_optimization_artifacts_requires_live_llm_sidecars_on_disk(tmp_path: Path) -> None:
    output_root = tmp_path / "llm_run_missing_sidecars"
    run = _fake_union_run()
    run.controller_trace = [
        {
            "decision_id": "g001-e0002-d00",
            "generation_index": 1,
            "evaluation_index": 2,
            "phase": "prefeasible_progress",
            "operator_selected": "local_refine",
            "selected_operator_id": "local_refine",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
            "metadata": {"fallback_used": False},
        }
    ]
    run.llm_request_trace = [
        {
            "decision_id": "g001-e0002-d00",
            "prompt_ref": "prompts/request.md",
            "model": "GPT-5.4",
            "http_status": 200,
            "retries": 0,
            "latency_ms": 120.0,
        }
    ]
    run.llm_response_trace = [
        {
            "decision_id": "g001-e0002-d00",
            "response_ref": "prompts/response.md",
            "model": "GPT-5.4",
            "tokens": {"total": 128},
            "finish_reason": "stop",
            "http_status": 200,
            "retries": 0,
            "latency_ms": 120.0,
        }
    ]

    try:
        write_optimization_artifacts(
            output_root,
            run,
            mode_id="llm",
            seed=11,
            objective_definitions=[
                {"objective_id": "minimize_peak_temperature", "metric": "summary.temperature_max", "sense": "minimize"},
                {
                    "objective_id": "minimize_temperature_gradient_rms",
                    "metric": "summary.temperature_gradient_rms",
                    "sense": "minimize",
                },
            ],
        )
    except ValueError as exc:
        assert "require JSONL traces on disk before artifact finalization" in str(exc)
    else:
        raise AssertionError("Expected llm artifact finalization to require pre-existing JSONL sidecars.")

    assert not (output_root / "traces" / "controller_trace.jsonl").exists()
    assert not (output_root / "traces" / "llm_request_trace.jsonl").exists()
    assert not (output_root / "traces" / "llm_response_trace.jsonl").exists()


def test_coerce_operator_trace_rows_derives_live_contract_fields_from_union_rows() -> None:
    rows = _coerce_operator_trace_rows(
        [
            OperatorTraceRow(
                generation_index=3,
                evaluation_index=12,
                operator_id="local_refine",
                parent_count=2,
                parent_vectors=((0.2, 0.3), (0.24, 0.34)),
                proposal_vector=(0.25, 0.35),
                metadata={
                    "decision_index": 4,
                    "attempt_index": 7,
                    "proposal_kind": "custom",
                    "wall_ms": 12.5,
                },
            )
        ]
    )

    assert rows == [
        {
            "decision_id": format_decision_id(3, 12, 4),
            "generation": 3,
            "operator_name": "local_refine",
            "parents": ["parent-0", "parent-1"],
            "offspring": [format_decision_id(3, 12, 4)],
            "params_digest": rows[0]["params_digest"],
            "wall_ms": 12.5,
        }
    ]
    assert len(rows[0]["params_digest"]) == 40


def test_coerce_operator_trace_rows_enriches_raw_like_rows_from_history_vectors() -> None:
    rows = _coerce_operator_trace_rows(
        [
            {
                "decision_id": "g001-e0002-d00",
                "generation": 1,
                "operator_name": "native_sbx_pm",
                "parents": [],
                "offspring": ["g001-i00"],
                "params_digest": "",
                "wall_ms": 0.0,
            }
        ],
        history_by_eval_index={
            1: {
                "evaluation_index": 1,
                "source": "baseline",
                **_candidate_contract({"c01_x": 0.1, "c01_y": 0.2}),
            },
            2: {
                "evaluation_index": 2,
                "source": "optimizer",
                "proposal_decision_vector": {"c01_x": 0.21, "c01_y": 0.31},
                "evaluated_decision_vector": {"c01_x": 0.22, "c01_y": 0.32},
                "decision_vector": {"c01_x": 0.22, "c01_y": 0.32},
                "legality_policy_id": "minimal_canonicalization",
                "vector_transform_codes": ["bound_clip"],
                "solver_skipped": False,
                "cheap_constraint_issues": [],
            },
        },
    )

    assert rows[0]["proposal_vector"] == [0.21, 0.31]
    assert rows[0]["evaluated_vector"] == [0.22, 0.32]
    assert rows[0]["legality_policy_id"] == "minimal_canonicalization"
