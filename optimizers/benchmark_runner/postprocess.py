"""Post-run rendering, diagnostics, and summary helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.benchmark_runner.run_events import append_summary_event


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
) -> None:
    root = Path(seed_root)
    from optimizers.render_assets import render_assets

    render_assets(root, hires=False)
    if mode != "llm":
        return

    from llm.openai_compatible.replay import replay_request_trace_file, save_replay_summary
    from optimizers.io import load_optimization_spec
    from optimizers.operator_pool.diagnostics import analyze_controller_trace, save_controller_trace_summary

    optimization_spec = load_optimization_spec(optimization_spec_path)
    operator_control = optimization_spec.operator_control or {}
    controller_parameters = dict(operator_control.get("controller_parameters", {}))
    replay_summary = replay_request_trace_file(
        root / "traces" / "llm_request_trace.jsonl",
        controller_parameters,
        limit=None,
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
