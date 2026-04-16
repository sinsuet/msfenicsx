"""Artifact writers for single-case Pareto optimizer runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from core.io.scenario_runs import write_field_export_artifacts
from core.schema.io import save_case, save_solution
from evaluation.io import save_report
from optimizers.io import save_optimization_result
from optimizers.problem import CandidateArtifacts
from optimizers.run_telemetry import build_evaluation_events, build_generation_summary_rows


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
    evaluation_rows = build_evaluation_events(run.result.history)
    generation_rows = build_generation_summary_rows(
        run_id=str(run.result.run_meta["run_id"]),
        mode_id=mode_id,
        seed=seed,
        rows=getattr(run, "generation_summary_rows", []),
    )
    _write_jsonl_payload(resolved_output_root / "traces" / "evaluation_events.jsonl", evaluation_rows)
    _write_jsonl_payload(resolved_output_root / "traces" / "generation_summary.jsonl", generation_rows)
    snapshots = {
        "optimization_result": "optimization_result.json",
        "pareto_front": "pareto_front.json",
        "evaluation_events": "traces/evaluation_events.jsonl",
        "generation_summary": "traces/generation_summary.jsonl",
    }
    if getattr(run, "llm_request_trace", None):
        _write_jsonl_payload(resolved_output_root / "traces" / "llm_request_trace.jsonl", getattr(run, "llm_request_trace"))
        snapshots["llm_request_trace"] = "traces/llm_request_trace.jsonl"
    if getattr(run, "llm_response_trace", None):
        _write_jsonl_payload(resolved_output_root / "traces" / "llm_response_trace.jsonl", getattr(run, "llm_response_trace"))
        snapshots["llm_response_trace"] = "traces/llm_response_trace.jsonl"
    if getattr(run, "llm_reflection_trace", None):
        _write_jsonl_payload(
            resolved_output_root / "traces" / "llm_reflection_trace.jsonl",
            getattr(run, "llm_reflection_trace"),
        )
        snapshots["llm_reflection_trace"] = "traces/llm_reflection_trace.jsonl"
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
    manifest = {
        "case_snapshot": case_snapshot,
        "solution_snapshot": solution_snapshot,
        "evaluation_snapshot": "evaluation.yaml" if artifacts.evaluation is not None else None,
        "directories": _representative_bundle_directories(),
    }
    if exported_fields is not None:
        manifest["field_exports"] = exported_fields
    _write_manifest(bundle_root / "manifest.json", manifest)


def write_representative_bundle(
    root: Path,
    *,
    case_yaml: str,
    solution_yaml: str,
    evaluation_yaml: str,
    temperature_grid: np.ndarray,
    gradient_grid: np.ndarray,
) -> None:
    """Write the flat § 3.1 representative layout.

    Layout:
      representatives/<id>/case.yaml
      representatives/<id>/solution.yaml
      representatives/<id>/evaluation.yaml
      representatives/<id>/fields/temperature_grid.npz
      representatives/<id>/fields/gradient_magnitude_grid.npz
    """
    root = Path(root)
    (root / "fields").mkdir(parents=True, exist_ok=True)
    (root / "case.yaml").write_text(case_yaml, encoding="utf-8")
    (root / "solution.yaml").write_text(solution_yaml, encoding="utf-8")
    (root / "evaluation.yaml").write_text(evaluation_yaml, encoding="utf-8")
    np.savez_compressed(root / "fields" / "temperature_grid.npz", grid=temperature_grid)
    np.savez_compressed(root / "fields" / "gradient_magnitude_grid.npz", grid=gradient_grid)


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
        "traces": "traces",
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


def _write_jsonl_payload(path: Path, rows: list[Any]) -> None:
    serialized_rows = [json.dumps(row.to_dict() if hasattr(row, "to_dict") else row) for row in rows]
    path.write_text("\n".join(serialized_rows) + "\n", encoding="utf-8")


