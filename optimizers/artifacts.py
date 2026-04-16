"""Artifact writers for single-case Pareto optimizer runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.io.scenario_runs import write_field_export_artifacts
from core.schema.io import save_case, save_solution
from evaluation.io import save_report
from optimizers.io import save_optimization_result
from optimizers.problem import CandidateArtifacts
from optimizers.run_telemetry import build_evaluation_events, build_generation_summary_rows
from visualization.case_pages import render_case_page


def write_optimization_artifacts(
    output_root: str | Path,
    run: Any,
    *,
    mode_id: str,
    seed: int,
    objective_definitions: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> Path:
    resolved_output_root = Path(output_root)
    _initialize_seed_bundle_root(resolved_output_root)
    save_optimization_result(run.result, resolved_output_root / "optimization_result.json")
    save_optimization_result({"pareto_front": run.result.pareto_front}, resolved_output_root / "pareto_front.json")
    evaluation_rows = build_evaluation_events(
        run_id=str(run.result.run_meta["run_id"]),
        mode_id=mode_id,
        seed=seed,
        history=run.result.history,
        objectives=objective_definitions,
        generation_rows=getattr(run, "generation_summary_rows", []),
    )
    generation_rows = build_generation_summary_rows(
        run_id=str(run.result.run_meta["run_id"]),
        mode_id=mode_id,
        seed=seed,
        rows=getattr(run, "generation_summary_rows", []),
    )
    _write_jsonl_payload(resolved_output_root / "evaluation_events.jsonl", evaluation_rows)
    _write_jsonl_payload(resolved_output_root / "generation_summary.jsonl", generation_rows)
    snapshots = {
        "optimization_result": "optimization_result.json",
        "pareto_front": "pareto_front.json",
        "evaluation_events": "evaluation_events.jsonl",
        "generation_summary": "generation_summary.jsonl",
    }
    if hasattr(run, "controller_trace"):
        _write_trace_payload(resolved_output_root / "controller_trace.json", getattr(run, "controller_trace"))
        snapshots["controller_trace"] = "controller_trace.json"
    if hasattr(run, "operator_trace"):
        _write_trace_payload(resolved_output_root / "operator_trace.json", getattr(run, "operator_trace"))
        snapshots["operator_trace"] = "operator_trace.json"
    if getattr(run, "controller_attempt_trace", None):
        _write_trace_payload(
            resolved_output_root / "controller_attempt_trace.json",
            getattr(run, "controller_attempt_trace"),
        )
        snapshots["controller_attempt_trace"] = "controller_attempt_trace.json"
    if getattr(run, "operator_attempt_trace", None):
        _write_trace_payload(
            resolved_output_root / "operator_attempt_trace.json",
            getattr(run, "operator_attempt_trace"),
        )
        snapshots["operator_attempt_trace"] = "operator_attempt_trace.json"
    if getattr(run, "llm_request_trace", None):
        _write_jsonl_payload(resolved_output_root / "llm_request_trace.jsonl", getattr(run, "llm_request_trace"))
        snapshots["llm_request_trace"] = "llm_request_trace.jsonl"
    if getattr(run, "llm_response_trace", None):
        _write_jsonl_payload(resolved_output_root / "llm_response_trace.jsonl", getattr(run, "llm_response_trace"))
        snapshots["llm_response_trace"] = "llm_response_trace.jsonl"
    if getattr(run, "llm_reflection_trace", None):
        _write_jsonl_payload(
            resolved_output_root / "llm_reflection_trace.jsonl",
            getattr(run, "llm_reflection_trace"),
        )
        snapshots["llm_reflection_trace"] = "llm_reflection_trace.jsonl"
    if getattr(run, "llm_metrics", None):
        _write_json_payload(resolved_output_root / "llm_metrics.json", getattr(run, "llm_metrics"))
        snapshots["llm_metrics"] = "llm_metrics.json"
    representatives_root = resolved_output_root / "representatives"
    for name, artifacts in run.representative_artifacts.items():
        _write_representative_bundle(representatives_root / name.replace("_", "-"), artifacts)
    manifest = {
        "run_id": run.result.run_meta["run_id"],
        "optimization_spec_id": run.result.run_meta["optimization_spec_id"],
        "evaluation_spec_id": run.result.run_meta["evaluation_spec_id"],
        "mode_id": mode_id,
        "benchmark_seed": int(seed),
        "snapshots": snapshots,
        "directories": _seed_bundle_directories(),
    }
    _write_manifest(resolved_output_root / "manifest.json", manifest)
    return resolved_output_root


def _write_representative_bundle(bundle_root: Path, artifacts: CandidateArtifacts) -> None:
    _initialize_representative_bundle_root(bundle_root)
    case_snapshot = "case.yaml"
    solution_snapshot = "solution.yaml"
    save_case(artifacts.case, bundle_root / "case.yaml")
    save_solution(artifacts.solution, bundle_root / "solution.yaml")
    if artifacts.evaluation is not None:
        save_report(artifacts.evaluation, bundle_root / "evaluation.yaml")
    exported_fields = None
    if artifacts.field_exports is not None:
        exported_fields = write_field_export_artifacts(bundle_root, artifacts.field_exports)
        render_case_page(bundle_root)
    manifest = {
        "case_snapshot": case_snapshot,
        "solution_snapshot": solution_snapshot,
        "evaluation_snapshot": "evaluation.yaml" if artifacts.evaluation is not None else None,
        "directories": _representative_bundle_directories(),
    }
    if exported_fields is not None:
        manifest["field_exports"] = exported_fields
    _write_manifest(bundle_root / "manifest.json", manifest)


def _initialize_seed_bundle_root(bundle_root: Path) -> None:
    bundle_root.mkdir(parents=True, exist_ok=True)
    for directory_name in _seed_bundle_directories().values():
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)


def _initialize_representative_bundle_root(bundle_root: Path) -> None:
    bundle_root.mkdir(parents=True, exist_ok=True)
    for directory_name in _representative_bundle_directories().values():
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)


def _seed_bundle_directories() -> dict[str, str]:
    return {
        "logs": "logs",
        "summaries": "summaries",
        "representatives": "representatives",
    }


def _representative_bundle_directories() -> dict[str, str]:
    return {
        "logs": "logs",
        "fields": "fields",
        "summaries": "summaries",
        "figures": "figures",
        "pages": "pages",
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_trace_payload(path: Path, rows: list[Any]) -> None:
    payload = [row.to_dict() if hasattr(row, "to_dict") else row for row in rows]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl_payload(path: Path, rows: list[Any]) -> None:
    serialized_rows = [json.dumps(row.to_dict() if hasattr(row, "to_dict") else row) for row in rows]
    path.write_text("\n".join(serialized_rows) + "\n", encoding="utf-8")


def _write_json_payload(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
