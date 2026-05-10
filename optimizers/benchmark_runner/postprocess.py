"""Post-run rendering, diagnostics, and summary helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.benchmark_runner.run_events import append_summary_event
from optimizers.run_telemetry import load_jsonl_rows


def build_runtime_summary(
    *,
    scenario_id: str,
    method_id: str,
    mode: str,
    seed: int,
    population_size: int,
    num_generations: int,
    run_wall_seconds: float,
    optimizer_wall_seconds: float,
    baseline_wall_seconds: float,
    postprocess_wall_seconds: float,
    render_wall_seconds: float,
    history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pde_attempt_count = 0
    cheap_skip_count = 0
    feasible_count = 0
    pde_wall_seconds_total = 0.0
    for row in history:
        solver_skipped = bool(row.get("solver_skipped", False))
        if solver_skipped:
            cheap_skip_count += 1
        else:
            pde_attempt_count += 1
        if bool(row.get("feasible", False)):
            feasible_count += 1
        timing = dict(row.get("timing", {}))
        solve_ms = timing.get("solve_ms") or timing.get("pde_ms") or 0.0
        pde_wall_seconds_total += float(solve_ms) / 1000.0
    return {
        "scenario_id": scenario_id,
        "method_id": method_id,
        "mode": mode,
        "seed": int(seed),
        "population_size": int(population_size),
        "num_generations": int(num_generations),
        "nominal_budget": int(population_size) * int(num_generations),
        "run_wall_seconds": float(run_wall_seconds),
        "optimizer_wall_seconds": float(optimizer_wall_seconds),
        "baseline_wall_seconds": float(baseline_wall_seconds),
        "postprocess_wall_seconds": float(postprocess_wall_seconds),
        "render_wall_seconds": float(render_wall_seconds),
        "pde_wall_seconds_total": float(pde_wall_seconds_total),
        "evaluation_count": int(len(history)),
        "pde_attempt_count": int(pde_attempt_count),
        "cheap_skip_count": int(cheap_skip_count),
        "feasible_count": int(feasible_count),
        "failed_evaluation_count": int(sum(1 for row in history if row.get("failure_reason"))),
    }


def write_runtime_summary(seed_root: str | Path, summary: Mapping[str, Any]) -> Path:
    root = Path(seed_root)
    output = root / "summaries" / "runtime_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_summary_event(
        root / "traces" / "run_events.jsonl",
        event="runtime_summary",
        scenario_id=str(summary["scenario_id"]),
        method_id=str(summary["method_id"]),
        mode=str(summary["mode"]),
        llm_profile=summary.get("llm_profile"),
        seed=int(summary["seed"]),
        summary=dict(summary),
    )
    return output


def write_llm_runtime_summary(seed_root: str | Path, summary: Mapping[str, Any]) -> Path:
    root = Path(seed_root)
    output = root / "summaries" / "llm_runtime_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_summary_event(
        root / "traces" / "run_events.jsonl",
        event="llm_runtime_summary",
        scenario_id=str(summary["scenario_id"]),
        method_id=str(summary["method_id"]),
        mode=str(summary["mode"]),
        llm_profile=str(summary.get("llm_profile") or ""),
        seed=int(summary.get("seed", 0) or 0),
        summary=dict(summary),
    )
    return output


def run_leaf_postprocess(
    seed_root: str | Path,
    *,
    mode: str,
    llm_profile: str | None,
    optimization_spec_path: Path,
    replay_mode: str | None = None,
) -> None:
    root = Path(seed_root)
    from optimizers.render_assets import render_assets

    render_assets(root, hires=False)
    if mode != "llm":
        return

    from llm.openai_compatible.replay import replay_request_trace_file, save_replay_summary
    from llm.openai_compatible.profile_loader import load_provider_profile_overlay
    from optimizers.cli import _temporary_env_overlay
    from optimizers.io import load_optimization_spec
    from optimizers.operator_pool.diagnostics import analyze_controller_trace, save_controller_trace_summary

    optimization_spec = load_optimization_spec(optimization_spec_path)
    operator_control = optimization_spec.operator_control or {}
    controller_parameters = dict(operator_control.get("controller_parameters", {}))
    effective_replay_mode = _resolve_llm_postprocess_replay_mode(replay_mode)
    if effective_replay_mode == "live":
        llm_overlay = load_provider_profile_overlay(llm_profile) if llm_profile else {}
        with _temporary_env_overlay(llm_overlay):
            replay_summary = replay_request_trace_file(
                root / "traces" / "llm_request_trace.jsonl",
                controller_parameters,
                limit=None,
            )
    else:
        replay_summary = build_offline_llm_replay_summary(
            root,
            controller_parameters=controller_parameters,
        )
    save_replay_summary(root / "summaries" / "llm_replay_summary.json", replay_summary)
    controller_summary = analyze_controller_trace(
        root / "traces" / "controller_trace.jsonl",
        optimization_result_path=root / "optimization_result.json",
        operator_trace_path=root / "traces" / "operator_trace.jsonl",
        llm_request_trace_path=root / "traces" / "llm_request_trace.jsonl",
        llm_response_trace_path=root / "traces" / "llm_response_trace.jsonl",
    )
    save_controller_trace_summary(root / "summaries" / "controller_trace_summary.json", controller_summary)


def _resolve_llm_postprocess_replay_mode(replay_mode: str | None) -> str:
    raw_mode = str(replay_mode or os.environ.get("MSFENICSX_LLM_POSTPROCESS_REPLAY", "offline")).strip().lower()
    if raw_mode in {"live", "provider"}:
        return "live"
    return "offline"


def build_offline_llm_replay_summary(
    seed_root: str | Path,
    *,
    controller_parameters: Mapping[str, Any],
) -> dict[str, Any]:
    """Summarize recorded LLM traces without issuing new provider requests."""
    root = Path(seed_root)
    request_trace_path = root / "traces" / "llm_request_trace.jsonl"
    response_trace_path = root / "traces" / "llm_response_trace.jsonl"
    request_rows = load_jsonl_rows(request_trace_path) if request_trace_path.exists() else []
    response_rows = load_jsonl_rows(response_trace_path) if response_trace_path.exists() else []
    response_by_decision_id = {
        str(row["decision_id"]): row
        for row in response_rows
        if row.get("decision_id") is not None
    }
    row_summaries: list[dict[str, Any]] = []
    elapsed_seconds_total = 0.0

    for row_index, request_row in enumerate(request_rows):
        decision_id = request_row.get("decision_id")
        response_row = (
            response_by_decision_id.get(str(decision_id))
            if decision_id is not None
            else None
        )
        if response_row is None and row_index < len(response_rows):
            response_row = response_rows[row_index]
        attempt_count = _offline_attempt_count(response_row)
        elapsed_seconds = _offline_elapsed_seconds(response_row)
        elapsed_seconds_total += elapsed_seconds
        selected_operator_id = None if response_row is None else response_row.get("selected_operator_id")
        error_message = _offline_error_message(response_row)
        valid = response_row is not None and selected_operator_id is not None and not bool(
            response_row.get("fallback_used", False)
        )
        row_summaries.append(
            {
                "row_index": int(row_index),
                "generation_index": int(request_row.get("generation_index", 0)),
                "evaluation_index": int(request_row.get("evaluation_index", 0)),
                "candidate_operator_ids": [str(value) for value in request_row.get("candidate_operator_ids", [])],
                "valid": bool(valid),
                "retried": bool(attempt_count > 1 or _offline_retry_count(response_row) > 0),
                "attempt_count": int(attempt_count),
                "selected_operator_id": None if selected_operator_id is None else str(selected_operator_id),
                "error": error_message,
                "elapsed_seconds": float(elapsed_seconds),
                "attempt_trace": [],
            }
        )

    request_count = len(row_summaries)
    success_count = sum(1 for row in row_summaries if row["valid"])
    retry_row_count = sum(1 for row in row_summaries if row["retried"])
    fallback_equivalent_count = request_count - success_count
    return {
        "aggregate": {
            "request_count": int(request_count),
            "success_count": int(success_count),
            "retry_row_count": int(retry_row_count),
            "fallback_equivalent_count": int(fallback_equivalent_count),
            "success_rate": 0.0 if request_count <= 0 else success_count / float(request_count),
            "retry_rate": 0.0 if request_count <= 0 else retry_row_count / float(request_count),
            "fallback_equivalent_rate": (
                0.0 if request_count <= 0 else fallback_equivalent_count / float(request_count)
            ),
            "elapsed_seconds_total": float(elapsed_seconds_total),
            "elapsed_seconds_avg": 0.0 if request_count <= 0 else elapsed_seconds_total / float(request_count),
        },
        "rows": row_summaries,
        "replay_meta": {
            "request_trace_path": str(request_trace_path),
            "response_trace_path": str(response_trace_path),
            "provider": str(controller_parameters.get("provider", "")),
            "model": _offline_controller_model(controller_parameters, request_rows=request_rows, response_rows=response_rows),
            "capability_profile": str(controller_parameters.get("capability_profile", "")),
            "performance_profile": str(controller_parameters.get("performance_profile", "")),
            "replay_mode": "offline_existing_trace",
            "live_provider_call_count": 0,
        },
    }


def _offline_controller_model(
    controller_parameters: Mapping[str, Any],
    *,
    request_rows: Sequence[Mapping[str, Any]],
    response_rows: Sequence[Mapping[str, Any]],
) -> str:
    for rows in (response_rows, request_rows):
        for row in rows:
            model = str(row.get("model", "")).strip()
            if model:
                return model
    return str(controller_parameters.get("model", ""))


def _offline_attempt_count(response_row: Mapping[str, Any] | None) -> int:
    if response_row is None:
        return 0
    if response_row.get("attempt_count") is not None:
        return int(response_row["attempt_count"])
    attempt_trace = response_row.get("attempt_trace", [])
    if isinstance(attempt_trace, Sequence) and not isinstance(attempt_trace, (str, bytes, bytearray)):
        return len(attempt_trace)
    return 0


def _offline_retry_count(response_row: Mapping[str, Any] | None) -> int:
    if response_row is None:
        return 0
    if response_row.get("retry_count") is not None:
        return int(response_row["retry_count"])
    retries = response_row.get("retries")
    return int(retries) if retries is not None else 0


def _offline_elapsed_seconds(response_row: Mapping[str, Any] | None) -> float:
    if response_row is None:
        return 0.0
    if response_row.get("elapsed_seconds") is not None:
        return float(response_row["elapsed_seconds"])
    if response_row.get("latency_ms") is not None:
        return float(response_row["latency_ms"]) / 1000.0
    return 0.0


def _offline_error_message(response_row: Mapping[str, Any] | None) -> str | None:
    if response_row is None:
        return "missing recorded response"
    error = response_row.get("error") or response_row.get("error_message")
    return None if error is None else str(error)
