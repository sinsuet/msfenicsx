from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from optimizers.run_layout import initialize_run_root


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
    for directory_name in ("seeds", "summaries"):
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
                "summaries": "summaries",
                "seeds": "seeds",
            },
        },
    )
    for seed in seeds:
        _create_mode_seed_bundle(mode_root / "seeds" / f"seed-{seed}", mode=mode, seed=seed)
    return mode_root


def create_mixed_run_root(
    tmp_path: Path,
    *,
    modes: tuple[str, ...] = ("raw", "union", "llm"),
    seeds: tuple[int, ...] = (11,),
) -> Path:
    mode_slug = "_".join(mode for mode in ("raw", "union", "llm") if mode in modes)
    run_root = create_run_root(
        tmp_path,
        run_id=f"0401_1430__{mode_slug}",
        modes=modes,
    )
    _write_json(
        run_root / "manifest.json",
        {
            "scenario_template_id": "s1_typical",
            "run_id": f"0401_1430__{mode_slug}",
            "mode_ids": list(modes),
            "benchmark_seeds": list(seeds),
            "directories": {
                "shared": "shared",
                **{mode: mode for mode in modes},
            },
        },
    )
    for mode in modes:
        mode_root = run_root / mode
        for directory_name in ("seeds", "summaries"):
            (mode_root / directory_name).mkdir(parents=True, exist_ok=True)
        _write_json(
            mode_root / "manifest.json",
            {
                "mode_id": mode,
                "benchmark_seeds": list(seeds),
                "directories": {
                    "summaries": "summaries",
                    "seeds": "seeds",
                },
            },
        )
        for seed in seeds:
            _create_mode_seed_bundle(mode_root / "seeds" / f"seed-{seed}", mode=mode, seed=seed)
    return run_root


def _create_mode_seed_bundle(seed_root: Path, *, mode: str, seed: int) -> None:
    seed_root.mkdir(parents=True, exist_ok=True)
    for directory_name in ("analytics", "figures", "representatives", "tables", "traces"):
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
                "baseline_feasible": False,
                "optimizer_num_evaluations": 3,
                "feasible_rate": 2.0 / 3.0,
                "optimizer_feasible_rate": 2.0 / 3.0,
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
        seed_root / "traces" / "evaluation_events.jsonl",
        [
            _evaluation_event(mode, seed, history[0], 0, 0.8, False, False, False),
            _evaluation_event(mode, seed, history[1], 1, 0.2, False, False, False),
            _evaluation_event(mode, seed, history[2], 1, 0.0, True, True, True),
            _evaluation_event(mode, seed, history[3], 2, 0.0, False, True, True),
        ],
    )
    _write_jsonl(
        seed_root / "traces" / "generation_summary.jsonl",
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
        _write_jsonl(
            seed_root / "traces" / "operator_trace.jsonl",
            [
                {
                    "decision_id": "g001-e0003-d00",
                    "generation": 1,
                    "operator_name": "local_refine",
                    "parents": ["baseline", "g001-i00"],
                    "offspring": ["g001-i01"],
                    "params_digest": "a" * 40,
                    "wall_ms": 12.5,
                },
                {
                    "decision_id": "g002-e0004-d00",
                    "generation": 2,
                    "operator_name": "slide_sink",
                    "parents": ["g001-i01", "g001-i00"],
                    "offspring": ["g002-i00"],
                    "params_digest": "b" * 40,
                    "wall_ms": 14.0,
                },
            ],
        )

    if mode == "llm":
        prompt_ref_a = _write_prompt_markdown(
            seed_root / "prompts" / "request-a.md",
            kind="request",
            body="# System\n\nsystem prompt\n\n# User\n\nuser prompt about first feasible\n",
        )
        prompt_ref_b = _write_prompt_markdown(
            seed_root / "prompts" / "request-b.md",
            kind="request",
            body="# System\n\nsystem prompt\n\n# User\n\nuser prompt about pareto expansion\n",
        )
        response_ref_a = _write_prompt_markdown(
            seed_root / "prompts" / "response-a.md",
            kind="response",
            body='{"selected_operator_id":"local_refine","rationale":"Choose local_refine to reach the first feasible layout."}\n',
        )
        response_ref_b = _write_prompt_markdown(
            seed_root / "prompts" / "response-b.md",
            kind="response",
            body='{"selected_operator_id":"slide_sink","rationale":"Choose slide_sink to improve peak temperature and expand pareto coverage."}\n',
        )
        _write_jsonl(
            seed_root / "traces" / "controller_trace.jsonl",
            [
                {
                    "decision_id": "g001-e0003-d00",
                    "phase": "prefeasible_progress",
                    "operator_selected": "local_refine",
                    "operator_pool_snapshot": ["native_sbx_pm", "local_refine"],
                    "input_state_digest": "a" * 40,
                    "prompt_ref": prompt_ref_a,
                    "rationale": "reduced hotspot",
                    "fallback_used": False,
                    "latency_ms": 1250.0,
                },
                {
                    "decision_id": "g002-e0004-d00",
                    "phase": "post_feasible_tradeoff",
                    "operator_selected": "slide_sink",
                    "operator_pool_snapshot": ["slide_sink", "local_refine"],
                    "input_state_digest": "b" * 40,
                    "prompt_ref": prompt_ref_b,
                    "rationale": "expand pareto front",
                    "fallback_used": False,
                    "latency_ms": 1400.0,
                },
            ],
        )
        _write_jsonl(
            seed_root / "traces" / "llm_request_trace.jsonl",
            [
                {
                    "decision_id": "g001-e0003-d00",
                    "generation_index": 1,
                    "evaluation_index": 3,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
                    "policy_phase": "prefeasible_progress",
                    "prompt_ref": prompt_ref_a,
                    "guardrail": {"dominant_operator_id": "local_refine"},
                    "http_status": 200,
                    "retries": 0,
                    "latency_ms": 1250.0,
                },
                {
                    "decision_id": "g002-e0004-d00",
                    "generation_index": 2,
                    "evaluation_index": 4,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "candidate_operator_ids": ["slide_sink", "local_refine"],
                    "policy_phase": "post_feasible_tradeoff",
                    "prompt_ref": prompt_ref_b,
                    "guardrail": {"dominant_operator_id": "slide_sink"},
                    "http_status": 200,
                    "retries": 0,
                    "latency_ms": 1400.0,
                },
            ],
        )
        _write_jsonl(
            seed_root / "traces" / "llm_response_trace.jsonl",
            [
                {
                    "decision_id": "g001-e0003-d00",
                    "generation_index": 1,
                    "evaluation_index": 3,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "selected_operator_id": "local_refine",
                    "response_ref": response_ref_a,
                    "tokens": {"total": 280},
                    "finish_reason": "stop",
                    "http_status": 200,
                    "retries": 0,
                    "latency_ms": 1250.0,
                },
                {
                    "decision_id": "g002-e0004-d00",
                    "generation_index": 2,
                    "evaluation_index": 4,
                    "provider": "openai-compatible",
                    "model": "GPT-5.4",
                    "capability_profile": "responses_native",
                    "performance_profile": "balanced",
                    "selected_operator_id": "slide_sink",
                    "response_ref": response_ref_b,
                    "tokens": {"total": 300},
                    "finish_reason": "stop",
                    "http_status": 200,
                    "retries": 0,
                    "latency_ms": 1400.0,
                },
            ],
        )


def _write_prompt_markdown(path: Path, *, kind: str, body: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "---\n"
            f"kind: {kind}\n"
            f"sha1: {path.stem}\n"
            "model: GPT-5.4\n"
            "decision_ids: [fixture]\n"
            "first_seen_at: 2026-04-16T08:21:03Z\n"
            "---\n\n"
            f"{body}"
        ),
        encoding="utf-8",
    )
    return f"prompts/{path.name}"


def _evaluation_event(
    mode: str,
    seed: int,
    record: dict[str, Any],
    generation_index: int,
    total_constraint_violation: float,
    entered_feasible_region: bool,
    pareto_membership_after_eval: bool,
    preserved_feasibility: bool,
    solver_skipped: bool = False,
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
        "solver_skipped": solver_skipped,
    }


def _create_representative_bundle(
    bundle_root: Path,
    *,
    case_id: str,
    peak_value: float,
    gradient_value: float,
) -> None:
    for directory_name in ("fields",):
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)
    _write_yaml(
        bundle_root / "case.yaml",
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": case_id, "scenario_id": "s1_typical"},
            "panel_domain": {"width": 1.0, "height": 0.8},
            "boundary_features": [
                {
                    "feature_id": "sink-top",
                    "kind": "line_sink",
                    "edge": "top",
                    "start": 0.2,
                    "end": 0.58,
                }
            ],
            "components": [
                {
                    "component_id": "c01-001",
                    "family_id": "chip",
                    "shape": "rect",
                    "geometry": {"width": 0.18, "height": 0.12},
                    "pose": {"x": 0.22, "y": 0.18, "rotation_deg": 0.0},
                },
                {
                    "component_id": "c02-001",
                    "family_id": "chip",
                    "shape": "capsule",
                    "geometry": {"length": 0.24, "radius": 0.035},
                    "pose": {"x": 0.68, "y": 0.46, "rotation_deg": 90.0},
                },
            ],
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
        bundle_root / "manifest.json",
        {
            "case_snapshot": "case.yaml",
            "solution_snapshot": "solution.yaml",
            "evaluation_snapshot": "evaluation.yaml",
            "field_exports": {
                "temperature_grid": "fields/temperature_grid.npz",
                "gradient_magnitude_grid": "fields/gradient_magnitude_grid.npz",
            },
            "directories": {
                "fields": "fields",
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
