from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow


def create_experiment_root(
    tmp_path: Path,
    *,
    mode_id: str,
    seeds: tuple[int, ...] = (11, 17),
) -> Path:
    root = tmp_path / "panel-four-component-hot-cold-benchmark" / "experiments" / f"{mode_id}__0401_1430"
    for directory_name in ("spec_snapshot", "runs", "summaries", "figures", "dashboards", "logs", "representatives"):
        (root / directory_name).mkdir(parents=True, exist_ok=True)

    _write_json(
        root / "manifest.json",
        {
            "scenario_template_id": "panel-four-component-hot-cold-benchmark",
            "mode_id": mode_id,
            "benchmark_seeds": list(seeds),
            "directories": {
                "spec_snapshot": "spec_snapshot",
                "runs": "runs",
                "summaries": "summaries",
                "figures": "figures",
                "dashboards": "dashboards",
                "logs": "logs",
                "representatives": "representatives",
            },
        },
    )
    (root / "spec_snapshot" / "optimization_spec.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "spec_meta": {"spec_id": f"{mode_id}-spec"},
                "design_variables": [
                    {"variable_id": "processor_x"},
                    {"variable_id": "processor_y"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    for seed in seeds:
        _create_run_bundle(root / "runs" / f"seed-{seed}", mode_id=mode_id, seed=seed)
    return root


def create_template_root_with_modes(tmp_path: Path) -> Path:
    from optimizers.experiment_summary import build_experiment_summaries

    template_root = tmp_path / "panel-four-component-hot-cold-benchmark"
    build_experiment_summaries(create_experiment_root(tmp_path, mode_id="nsga2_raw"))
    build_experiment_summaries(create_experiment_root(tmp_path, mode_id="nsga2_union"))
    build_experiment_summaries(create_experiment_root(tmp_path, mode_id="nsga2_llm"))
    return template_root


def _create_run_bundle(run_root: Path, *, mode_id: str, seed: int) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    history = [
        _record(
            1,
            {"processor_x": 0.2, "processor_y": 0.3},
            feasible=False,
            objective_values={
                "minimize_hot_pa_peak": 303.0,
                "maximize_cold_battery_min": 255.0,
                "minimize_radiator_resource": 0.5,
            },
            constraint_values={"cold_battery_floor": 0.5, "hot_pa_limit": 0.2},
            source="baseline",
        ),
        _record(
            2,
            {"processor_x": 0.25, "processor_y": 0.35},
            feasible=False,
            objective_values={
                "minimize_hot_pa_peak": 301.0,
                "maximize_cold_battery_min": 256.0,
                "minimize_radiator_resource": 0.47,
            },
            constraint_values={"cold_battery_floor": 0.2, "hot_pa_limit": 0.1},
        ),
        _record(
            3,
            {"processor_x": 0.4, "processor_y": 0.5},
            feasible=True,
            objective_values={
                "minimize_hot_pa_peak": 299.0,
                "maximize_cold_battery_min": 259.0,
                "minimize_radiator_resource": 0.44,
            },
            constraint_values={"cold_battery_floor": 0.0, "hot_pa_limit": 0.0},
        ),
    ]
    _write_json(
        run_root / "optimization_result.json",
        {
            "schema_version": "1.0",
            "run_meta": {
                "run_id": f"{mode_id}-seed-{seed}-run",
                "optimization_spec_id": f"{mode_id}-spec",
                "evaluation_spec_id": "panel-four-component-hot-cold-baseline",
                "base_case_ids": {"hot": f"hot-{seed}", "cold": f"cold-{seed}"},
            },
            "baseline_candidates": [history[0]],
            "pareto_front": [history[-1]],
            "representative_candidates": {},
            "aggregate_metrics": {
                "num_evaluations": len(history),
                "feasible_rate": 1.0 / 3.0,
                "first_feasible_eval": 3,
                "pareto_size": 1,
            },
            "history": history,
            "provenance": {
                "benchmark_source": {"seed": seed},
                "source_case_ids": {"hot": f"hot-{seed}", "cold": f"cold-{seed}"},
                "source_optimization_spec_id": f"{mode_id}-spec",
                "source_evaluation_spec_id": "panel-four-component-hot-cold-baseline",
            },
        },
    )
    _write_jsonl(
        run_root / "evaluation_events.jsonl",
        [
            {
                "run_id": f"{mode_id}-seed-{seed}-run",
                "mode_id": mode_id,
                "seed": seed,
                "generation_index": 0,
                "evaluation_index": 1,
                "source": "baseline",
                "decision_vector": history[0]["decision_vector"],
                "objective_values": history[0]["objective_values"],
                "constraint_values": history[0]["constraint_values"],
                "feasible": False,
                "total_constraint_violation": 0.7,
                "dominant_violation_constraint_id": "cold_battery_floor",
                "dominant_violation_constraint_family": "cold_dominant",
                "violation_count": 2,
                "entered_feasible_region": False,
                "preserved_feasibility": False,
                "pareto_membership_after_eval": False,
                "failure_reason": None,
                "feasibility_phase": "prefeasible",
            },
            {
                "run_id": f"{mode_id}-seed-{seed}-run",
                "mode_id": mode_id,
                "seed": seed,
                "generation_index": 1,
                "evaluation_index": 2,
                "source": "optimizer",
                "decision_vector": history[1]["decision_vector"],
                "objective_values": history[1]["objective_values"],
                "constraint_values": history[1]["constraint_values"],
                "feasible": False,
                "total_constraint_violation": 0.3,
                "dominant_violation_constraint_id": "cold_battery_floor",
                "dominant_violation_constraint_family": "cold_dominant",
                "violation_count": 2,
                "entered_feasible_region": False,
                "preserved_feasibility": False,
                "pareto_membership_after_eval": False,
                "failure_reason": None,
                "feasibility_phase": "prefeasible",
            },
            {
                "run_id": f"{mode_id}-seed-{seed}-run",
                "mode_id": mode_id,
                "seed": seed,
                "generation_index": 1,
                "evaluation_index": 3,
                "source": "optimizer",
                "decision_vector": history[2]["decision_vector"],
                "objective_values": history[2]["objective_values"],
                "constraint_values": history[2]["constraint_values"],
                "feasible": True,
                "total_constraint_violation": 0.0,
                "dominant_violation_constraint_id": None,
                "dominant_violation_constraint_family": None,
                "violation_count": 0,
                "entered_feasible_region": True,
                "preserved_feasibility": False,
                "pareto_membership_after_eval": True,
                "failure_reason": None,
                "feasibility_phase": "prefeasible",
            },
        ],
    )
    _write_jsonl(
        run_root / "generation_summary.jsonl",
        [
            {
                "run_id": f"{mode_id}-seed-{seed}-run",
                "mode_id": mode_id,
                "seed": seed,
                "generation_index": 1,
                "num_evaluations_so_far": 3,
                "feasible_fraction": 1.0 / 3.0,
                "best_total_constraint_violation": 0.0,
                "best_hot_pa_peak": 299.0,
                "best_cold_battery_min": 259.0,
                "best_radiator_resource": 0.44,
                "pareto_size": 1,
                "new_feasible_entries": 1,
                "new_pareto_entries": 1,
            }
        ],
    )

    if mode_id in {"nsga2_union", "nsga2_llm"}:
        controller_id = "llm" if mode_id == "nsga2_llm" else "random_uniform"
        controller_rows = [
            ControllerTraceRow(
                generation_index=1,
                evaluation_index=3,
                family="genetic",
                backbone="nsga2",
                controller_id=controller_id,
                candidate_operator_ids=("native_sbx_pm", "local_refine"),
                selected_operator_id="local_refine",
                phase="prefeasible_progress",
                rationale="local cleanup",
                metadata={
                    "fallback_used": mode_id != "nsga2_llm",
                    "guardrail_reason_codes": ["prefeasible_forced_reset"] if mode_id == "nsga2_llm" else [],
                },
            )
        ]
        operator_rows = [
            OperatorTraceRow(
                generation_index=1,
                evaluation_index=3,
                operator_id="local_refine",
                parent_count=2,
                parent_vectors=((0.2, 0.3), (0.25, 0.35)),
                proposal_vector=(0.41, 0.51),
                metadata={"repaired_vector": [0.4, 0.5]},
            )
        ]
        _write_json(run_root / "controller_trace.json", [row.to_dict() for row in controller_rows])
        _write_json(run_root / "operator_trace.json", [row.to_dict() for row in operator_rows])

    if mode_id == "nsga2_llm":
        _write_jsonl(
            run_root / "llm_request_trace.jsonl",
            [
                {
                    "generation_index": 1,
                    "evaluation_index": 3,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
                    "policy_phase": "prefeasible_progress",
                    "system_prompt": "system prompt",
                    "user_prompt": "user prompt",
                    "guardrail": {"dominant_operator_id": "native_sbx_pm"},
                }
            ],
        )
        _write_jsonl(
            run_root / "llm_response_trace.jsonl",
            [
                {
                    "generation_index": 1,
                    "evaluation_index": 3,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "selected_operator_id": "local_refine",
                    "phase": "prefeasible_progress",
                    "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
                    "fallback_used": False,
                    "elapsed_seconds": 1.25,
                }
            ],
        )
        _write_json(
            run_root / "llm_metrics.json",
            {
                "provider": "openai-compatible",
                "model": "GPT-5.4",
                "capability_profile": "responses_native",
                "performance_profile": "balanced",
                "request_count": 1,
                "response_count": 1,
                "fallback_count": 0,
                "retry_count": 1,
                "invalid_response_count": 1,
                "schema_invalid_count": 1,
                "semantic_invalid_count": 0,
                "elapsed_seconds_total": 1.25,
                "elapsed_seconds_avg": 1.25,
                "elapsed_seconds_max": 1.25,
            },
        )


def _record(
    evaluation_index: int,
    decision_vector: dict[str, float],
    *,
    feasible: bool,
    objective_values: dict[str, float],
    constraint_values: dict[str, float],
    source: str = "optimizer",
) -> dict[str, Any]:
    return {
        "evaluation_index": evaluation_index,
        "source": source,
        "feasible": feasible,
        "decision_vector": decision_vector,
        "objective_values": objective_values,
        "constraint_values": constraint_values,
        "case_reports": {},
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
