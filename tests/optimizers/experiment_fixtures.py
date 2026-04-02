from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from optimizers.run_layout import initialize_run_root
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow


def create_run_root(
    tmp_path: Path,
    *,
    run_id: str = "0401_1430__raw",
    modes: tuple[str, ...] = ("raw",),
    include_comparison: bool = False,
) -> Path:
    root = initialize_run_root(
        tmp_path / "scenario_runs",
        scenario_template_id="s1_typical",
        run_id=run_id,
        modes=modes,
    )
    if include_comparison:
        (root / "comparison").mkdir(parents=True, exist_ok=True)
    return root


def create_mode_root(
    tmp_path: Path,
    *,
    mode: str = "raw",
    run_id: str | None = None,
    include_comparison: bool = False,
) -> Path:
    effective_run_id = run_id or f"0401_1430__{mode}"
    run_root = create_run_root(
        tmp_path,
        run_id=effective_run_id,
        modes=(mode,),
        include_comparison=include_comparison,
    )
    mode_root = run_root / mode
    for directory_name in ("logs", "summaries", "pages", "figures", "reports", "seeds"):
        (mode_root / directory_name).mkdir(parents=True, exist_ok=True)
    return mode_root


def create_mode_root_with_seed_bundles(
    tmp_path: Path,
    *,
    mode: str = "raw",
    seeds: tuple[int, ...] = (11,),
) -> Path:
    mode_root = create_mode_root(tmp_path, mode=mode)
    _write_json(
        mode_root / "manifest.json",
        {
            "mode_id": mode,
            "benchmark_seeds": list(seeds),
            "directories": {
                "logs": "logs",
                "summaries": "summaries",
                "pages": "pages",
                "figures": "figures",
                "reports": "reports",
                "seeds": "seeds",
            },
        },
    )
    for seed in seeds:
        _create_mode_seed_bundle(mode_root / "seeds" / f"seed-{seed}", mode=mode, seed=seed)
    return mode_root


def create_experiment_root(
    tmp_path: Path,
    *,
    mode_id: str,
    seeds: tuple[int, ...] = (11, 17),
) -> Path:
    root = tmp_path / "s1_typical" / "experiments" / f"{mode_id}__0401_1430"
    for directory_name in ("spec_snapshot", "runs", "summaries", "figures", "dashboards", "logs", "representatives"):
        (root / directory_name).mkdir(parents=True, exist_ok=True)

    _write_json(
        root / "manifest.json",
        {
            "scenario_template_id": "s1_typical",
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
                    {"variable_id": "c01_x"},
                    {"variable_id": "c01_y"},
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

    template_root = tmp_path / "s1_typical"
    build_experiment_summaries(create_experiment_root(tmp_path, mode_id="nsga2_raw"))
    build_experiment_summaries(create_experiment_root(tmp_path, mode_id="nsga2_union"))
    build_experiment_summaries(create_experiment_root(tmp_path, mode_id="nsga2_llm"))
    return template_root


def _create_run_bundle(run_root: Path, *, mode_id: str, seed: int) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    history = [
        _record(
            1,
            {"c01_x": 0.2, "c01_y": 0.3},
            feasible=False,
            objective_values={
                "minimize_peak_temperature": 303.0,
                "minimize_temperature_gradient_rms": 10.6,
            },
            constraint_values={"radiator_span_budget": 0.5},
            source="baseline",
        ),
        _record(
            2,
            {"c01_x": 0.25, "c01_y": 0.35},
            feasible=False,
            objective_values={
                "minimize_peak_temperature": 301.0,
                "minimize_temperature_gradient_rms": 9.4,
            },
            constraint_values={"radiator_span_budget": 0.2},
        ),
        _record(
            3,
            {"c01_x": 0.4, "c01_y": 0.5},
            feasible=True,
            objective_values={
                "minimize_peak_temperature": 299.0,
                "minimize_temperature_gradient_rms": 8.4,
            },
            constraint_values={"radiator_span_budget": 0.0},
        ),
    ]
    _write_json(
        run_root / "optimization_result.json",
        {
            "schema_version": "1.0",
            "run_meta": {
                "run_id": f"{mode_id}-seed-{seed}-run",
                "optimization_spec_id": f"{mode_id}-spec",
                "evaluation_spec_id": "s1_typical_eval",
                "base_case_id": f"s1_typical-case-{seed:03d}",
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
                "source_case_id": f"s1_typical-case-{seed:03d}",
                "source_optimization_spec_id": f"{mode_id}-spec",
                "source_evaluation_spec_id": "s1_typical_eval",
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
                "total_constraint_violation": 0.5,
                "dominant_violation_constraint_id": "radiator_span_budget",
                "dominant_violation_constraint_family": "geometry_dominant",
                "violation_count": 1,
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
                "total_constraint_violation": 0.2,
                "dominant_violation_constraint_id": "radiator_span_budget",
                "dominant_violation_constraint_family": "geometry_dominant",
                "violation_count": 1,
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
                "best_minimize_peak_temperature": 299.0,
                "best_minimize_temperature_gradient_rms": 8.4,
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


def _create_mode_seed_bundle(seed_root: Path, *, mode: str, seed: int) -> None:
    seed_root.mkdir(parents=True, exist_ok=True)
    for directory_name in ("logs", "summaries", "representatives"):
        (seed_root / directory_name).mkdir(parents=True, exist_ok=True)
    history = [
        _record(
            1,
            {"c01_x": 0.2, "c01_y": 0.3},
            feasible=False,
            objective_values={
                "summary.temperature_max": 320.0,
                "summary.temperature_gradient_rms": 12.0,
            },
            constraint_values={"radiator_span_budget": 0.8},
            source="baseline",
        ),
        _record(
            2,
            {"c01_x": 0.24, "c01_y": 0.34},
            feasible=False,
            objective_values={
                "summary.temperature_max": 314.0,
                "summary.temperature_gradient_rms": 10.8,
            },
            constraint_values={"radiator_span_budget": 0.2},
        ),
        _record(
            3,
            {"c01_x": 0.4, "c01_y": 0.5},
            feasible=True,
            objective_values={
                "summary.temperature_max": 301.0,
                "summary.temperature_gradient_rms": 8.8,
            },
            constraint_values={"radiator_span_budget": 0.0},
        ),
        _record(
            4,
            {"c01_x": 0.44, "c01_y": 0.56},
            feasible=True,
            objective_values={
                "summary.temperature_max": 297.0,
                "summary.temperature_gradient_rms": 9.4,
            },
            constraint_values={"radiator_span_budget": 0.0},
        ),
    ]
    _write_json(
        seed_root / "optimization_result.json",
        {
            "schema_version": "1.0",
            "run_meta": {
                "run_id": f"{mode}-seed-{seed}-run",
                "optimization_spec_id": f"{mode}-spec",
                "evaluation_spec_id": "s1_typical_eval",
                "base_case_id": f"s1_typical-case-{seed:03d}",
            },
            "baseline_candidates": [history[0]],
            "pareto_front": [history[2], history[3]],
            "representative_candidates": {
                "baseline": history[0],
                "first_feasible": history[2],
                "best_peak": history[3],
                "best_gradient": history[2],
                "knee": history[2],
            },
            "aggregate_metrics": {
                "num_evaluations": len(history),
                "feasible_rate": 0.5,
                "first_feasible_eval": 3,
                "pareto_size": 2,
            },
            "history": history,
            "provenance": {
                "benchmark_source": {"seed": seed},
                "source_case_id": f"s1_typical-case-{seed:03d}",
                "source_optimization_spec_id": f"{mode}-spec",
                "source_evaluation_spec_id": "s1_typical_eval",
            },
        },
    )
    _write_jsonl(
        seed_root / "evaluation_events.jsonl",
        [
            _evaluation_event(mode, seed, history[0], 0, 0.8, False, False, False),
            _evaluation_event(mode, seed, history[1], 1, 0.2, False, False, False),
            _evaluation_event(mode, seed, history[2], 1, 0.0, True, True, True),
            _evaluation_event(mode, seed, history[3], 2, 0.0, False, True, True),
        ],
    )
    _write_jsonl(
        seed_root / "generation_summary.jsonl",
        [
            {
                "run_id": f"{mode}-seed-{seed}-run",
                "mode_id": mode,
                "seed": seed,
                "generation_index": 1,
                "num_evaluations_so_far": 2,
                "feasible_fraction": 0.0,
                "best_total_constraint_violation": 0.2,
                "best_summary_temperature_max": 314.0,
                "best_summary_temperature_gradient_rms": 10.8,
                "pareto_size": 0,
                "new_feasible_entries": 0,
                "new_pareto_entries": 0,
            },
            {
                "run_id": f"{mode}-seed-{seed}-run",
                "mode_id": mode,
                "seed": seed,
                "generation_index": 2,
                "num_evaluations_so_far": 4,
                "feasible_fraction": 0.5,
                "best_total_constraint_violation": 0.0,
                "best_summary_temperature_max": 297.0,
                "best_summary_temperature_gradient_rms": 8.8,
                "pareto_size": 2,
                "new_feasible_entries": 1,
                "new_pareto_entries": 2,
            },
        ],
    )
    for representative_id, peak_value, gradient_value in (
        ("baseline", 320.0, 12.0),
        ("first-feasible", 301.0, 8.8),
        ("best-peak", 297.0, 9.4),
        ("best-gradient", 301.0, 8.8),
        ("knee", 301.0, 8.8),
    ):
        _create_representative_bundle(
            seed_root / "representatives" / representative_id,
            case_id=f"s1_typical-case-{seed:03d}",
            peak_value=peak_value,
            gradient_value=gradient_value,
        )

    if mode in {"union", "llm"}:
        controller_rows = [
            ControllerTraceRow(
                generation_index=1,
                evaluation_index=3,
                family="genetic",
                backbone="nsga2",
                controller_id="llm" if mode == "llm" else "random_uniform",
                candidate_operator_ids=("native_sbx_pm", "local_refine"),
                selected_operator_id="local_refine",
                phase="prefeasible_progress",
                rationale="reduced hotspot",
                metadata={"fallback_used": False},
            ),
            ControllerTraceRow(
                generation_index=2,
                evaluation_index=4,
                family="genetic",
                backbone="nsga2",
                controller_id="llm" if mode == "llm" else "random_uniform",
                candidate_operator_ids=("slide_sink", "local_refine"),
                selected_operator_id="slide_sink",
                phase="post_feasible_tradeoff",
                rationale="expand pareto front",
                metadata={"fallback_used": False},
            ),
        ]
        operator_rows = [
            OperatorTraceRow(
                generation_index=1,
                evaluation_index=3,
                operator_id="local_refine",
                parent_count=2,
                parent_vectors=((0.2, 0.3), (0.24, 0.34)),
                proposal_vector=(0.4, 0.5),
                metadata={},
            ),
            OperatorTraceRow(
                generation_index=2,
                evaluation_index=4,
                operator_id="slide_sink",
                parent_count=2,
                parent_vectors=((0.4, 0.5), (0.24, 0.34)),
                proposal_vector=(0.44, 0.56),
                metadata={},
            ),
        ]
        _write_json(seed_root / "controller_trace.json", [row.to_dict() for row in controller_rows])
        _write_json(seed_root / "operator_trace.json", [row.to_dict() for row in operator_rows])

    if mode == "llm":
        _write_jsonl(
            seed_root / "llm_request_trace.jsonl",
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
                    "user_prompt": "user prompt about first feasible",
                    "guardrail": {"dominant_operator_id": "local_refine"},
                },
                {
                    "generation_index": 2,
                    "evaluation_index": 4,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "candidate_operator_ids": ["slide_sink", "local_refine"],
                    "policy_phase": "post_feasible_tradeoff",
                    "system_prompt": "system prompt",
                    "user_prompt": "user prompt about pareto expansion",
                    "guardrail": {"dominant_operator_id": "slide_sink"},
                },
            ],
        )
        _write_jsonl(
            seed_root / "llm_response_trace.jsonl",
            [
                {
                    "generation_index": 1,
                    "evaluation_index": 3,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "selected_operator_id": "local_refine",
                    "response_text": "Choose local_refine to reach the first feasible layout.",
                    "elapsed_seconds": 1.25,
                },
                {
                    "generation_index": 2,
                    "evaluation_index": 4,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "selected_operator_id": "slide_sink",
                    "response_text": "Choose slide_sink to improve peak temperature and expand pareto coverage.",
                    "elapsed_seconds": 1.4,
                },
            ],
        )
        _write_json(
            seed_root / "llm_metrics.json",
            {
                "provider": "openai-compatible",
                "model": "GPT-5.4",
                "capability_profile": "responses_native",
                "performance_profile": "balanced",
                "request_count": 2,
                "response_count": 2,
                "fallback_count": 0,
                "retry_count": 0,
                "invalid_response_count": 0,
                "schema_invalid_count": 0,
                "semantic_invalid_count": 0,
                "elapsed_seconds_total": 2.65,
                "elapsed_seconds_avg": 1.325,
                "elapsed_seconds_max": 1.4,
            },
        )


def _evaluation_event(
    mode: str,
    seed: int,
    record: dict[str, Any],
    generation_index: int,
    total_constraint_violation: float,
    entered_feasible_region: bool,
    pareto_membership_after_eval: bool,
    preserved_feasibility: bool,
) -> dict[str, Any]:
    return {
        "run_id": f"{mode}-seed-{seed}-run",
        "mode_id": mode,
        "seed": seed,
        "generation_index": generation_index,
        "evaluation_index": record["evaluation_index"],
        "source": record["source"],
        "decision_vector": record["decision_vector"],
        "objective_values": record["objective_values"],
        "constraint_values": record["constraint_values"],
        "feasible": record["feasible"],
        "total_constraint_violation": total_constraint_violation,
        "dominant_violation_constraint_id": (
            None if total_constraint_violation <= 0.0 else "radiator_span_budget"
        ),
        "dominant_violation_constraint_family": (
            None if total_constraint_violation <= 0.0 else "geometry_dominant"
        ),
        "violation_count": 0 if total_constraint_violation <= 0.0 else 1,
        "entered_feasible_region": entered_feasible_region,
        "preserved_feasibility": preserved_feasibility,
        "pareto_membership_after_eval": pareto_membership_after_eval,
        "failure_reason": None,
        "feasibility_phase": "post_feasible" if record["evaluation_index"] >= 4 else "prefeasible",
    }


def _create_representative_bundle(
    bundle_root: Path,
    *,
    case_id: str,
    peak_value: float,
    gradient_value: float,
) -> None:
    for directory_name in ("logs", "fields", "summaries", "figures", "pages"):
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)
    _write_yaml(
        bundle_root / "case.yaml",
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": case_id, "scenario_id": "s1_typical"},
        },
    )
    _write_yaml(
        bundle_root / "solution.yaml",
        {
            "schema_version": "1.0",
            "solution_meta": {"case_id": case_id, "solution_id": f"{case_id}-solution"},
            "field_records": {
                "temperature": {"kind": "cg1_dofs", "num_dofs": 25},
                "gradient_magnitude": {"kind": "regular_grid", "grid_shape": [4, 4]},
            },
            "summary_metrics": {
                "temperature_max": peak_value,
                "temperature_gradient_rms": gradient_value,
            },
            "component_summaries": [],
            "solver_diagnostics": {"solver": "dolfinx_snes"},
            "provenance": {"source_case_id": case_id},
        },
    )
    _write_yaml(
        bundle_root / "evaluation.yaml",
        {
            "schema_version": "1.0",
            "evaluation_meta": {"case_id": case_id},
            "feasible": True,
            "metric_values": {
                "summary.temperature_max": peak_value,
                "summary.temperature_gradient_rms": gradient_value,
            },
            "constraint_reports": [
                {
                    "constraint_id": "radiator_span_budget",
                    "actual": 0.0,
                    "limit": 0.0,
                    "relation": "<=",
                }
            ],
        },
    )
    np.savez_compressed(bundle_root / "fields" / "temperature_grid.npz", values=np.arange(16, dtype=np.float64).reshape(4, 4))
    np.savez_compressed(
        bundle_root / "fields" / "gradient_magnitude_grid.npz",
        values=np.linspace(0.0, 3.0, 16, dtype=np.float64).reshape(4, 4),
    )
    _write_json(
        bundle_root / "summaries" / "field_view.json",
        {
            "panel_domain": {"width": 1.0, "height": 0.8},
            "temperature": {
                "grid_shape": [4, 4],
                "min": peak_value - 15.0,
                "max": peak_value,
                "hotspot": {"x": 0.8, "y": 0.6, "value": peak_value},
                "contour_levels": [peak_value - 15.0, peak_value - 8.0, peak_value],
            },
            "gradient_magnitude": {
                "grid_shape": [4, 4],
                "min": 0.0,
                "max": gradient_value,
            },
            "layout": {
                "components": [{"component_id": "comp-001", "bounds": {"x_min": 0.2, "y_min": 0.2, "x_max": 0.4, "y_max": 0.4}}],
                "line_sinks": [{"feature_id": "sink-top-window", "edge": "top", "start_x": 0.25, "end_x": 0.55}],
            },
        },
    )
    _write_json(
        bundle_root / "manifest.json",
        {
            "case_snapshot": "case.yaml",
            "solution_snapshot": "solution.yaml",
            "evaluation_snapshot": "evaluation.yaml",
            "field_exports": {
                "temperature_grid": "fields/temperature_grid.npz",
                "gradient_magnitude_grid": "fields/gradient_magnitude_grid.npz",
                "field_view": "summaries/field_view.json",
            },
            "directories": {
                "logs": "logs",
                "fields": "fields",
                "summaries": "summaries",
                "figures": "figures",
                "pages": "pages",
            },
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
        "evaluation_report": {"evaluation_meta": {"case_id": "fixture-case"}, "feasible": feasible},
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def _write_yaml(path: Path, payload: Any) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
