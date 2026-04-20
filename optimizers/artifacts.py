"""Artifact writers for single-case Pareto optimizer runs."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from core.schema.io import save_case, save_solution
from evaluation.io import save_report
from optimizers.io import save_optimization_result
from optimizers.problem import CandidateArtifacts
from optimizers.run_telemetry import build_evaluation_events, build_generation_summary_rows
from optimizers.traces.correlation import format_decision_id


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
        run.result.history,
        objective_definitions=objective_definitions,
    )
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
    if mode_id == "llm" and hasattr(run, "controller_trace"):
        controller_trace_jsonl_path = resolved_output_root / "traces" / "controller_trace.jsonl"
        if controller_trace_jsonl_path.exists():
            snapshots["controller_trace"] = "traces/controller_trace.jsonl"
    if hasattr(run, "operator_trace"):
        operator_trace_rows = _coerce_operator_trace_rows(getattr(run, "operator_trace"))
        operator_trace_jsonl_path = resolved_output_root / "traces" / "operator_trace.jsonl"
        if operator_trace_rows:
            _write_jsonl_payload(
                operator_trace_jsonl_path,
                operator_trace_rows,
            )
        if operator_trace_jsonl_path.exists():
            snapshots["operator_trace"] = "traces/operator_trace.jsonl"
    llm_request_trace_path = resolved_output_root / "traces" / "llm_request_trace.jsonl"
    if llm_request_trace_path.exists():
        snapshots["llm_request_trace"] = "traces/llm_request_trace.jsonl"
    llm_response_trace_path = resolved_output_root / "traces" / "llm_response_trace.jsonl"
    if llm_response_trace_path.exists():
        snapshots["llm_response_trace"] = "traces/llm_response_trace.jsonl"
    if mode_id == "llm":
        missing = [
            name
            for name, path in {
                "controller_trace": resolved_output_root / "traces" / "controller_trace.jsonl",
                "llm_request_trace": llm_request_trace_path,
                "llm_response_trace": llm_response_trace_path,
            }.items()
            if not path.exists()
        ]
        if missing:
            raise ValueError(f"LLM runs require JSONL traces on disk before artifact finalization: {missing}.")
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
        exported_fields = _write_representative_field_exports(bundle_root, artifacts.field_exports)
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
    """Write the flat representative bundle layout.

    Layout:
      representatives/<id>/case.yaml
      representatives/<id>/solution.yaml
      representatives/<id>/evaluation.yaml
      representatives/<id>/fields/temperature_grid.npz
      representatives/<id>/fields/gradient_magnitude_grid.npz
    """
    root = Path(root)
    _initialize_representative_bundle_root(root)
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
    for stale_name in ("summaries", "pages", "figures", "logs"):
        stale_path = bundle_root / stale_name
        if stale_path.exists():
            shutil.rmtree(stale_path)
    for directory_name in _representative_bundle_directories().values():
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)


def _seed_bundle_directories() -> dict[str, str]:
    return {
        "analytics": "analytics",
        "figures": "figures",
        "representatives": "representatives",
        "tables": "tables",
        "traces": "traces",
    }


def _representative_bundle_directories() -> dict[str, str]:
    return {
        "fields": "fields",
    }


def _write_representative_field_exports(bundle_root: Path, field_exports: dict[str, Any]) -> dict[str, str]:
    arrays = field_exports.get("arrays") or {}
    exported_fields: dict[str, str] = {}
    for field_name, filename in (
        ("temperature", "temperature_grid.npz"),
        ("gradient_magnitude", "gradient_magnitude_grid.npz"),
    ):
        if field_name not in arrays:
            continue
        relative_path = Path("fields") / filename
        np.savez_compressed(
            bundle_root / relative_path,
            values=np.asarray(arrays[field_name], dtype=np.float64),
        )
        exported_fields[f"{field_name}_grid"] = relative_path.as_posix()
    return exported_fields


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl_payload(path: Path, rows: list[Any]) -> None:
    serialized_rows = [json.dumps(row.to_dict() if hasattr(row, "to_dict") else row) for row in rows]
    path.write_text("\n".join(serialized_rows) + "\n", encoding="utf-8")


def _coerce_operator_trace_rows(operator_trace: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in operator_trace or ():
        payload = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
        metadata = dict(payload.get("metadata", {}) or {})
        generation = int(payload.get("generation_index", payload.get("generation", 0)))
        evaluation_index = int(payload.get("evaluation_index", payload.get("provisional_evaluation_index", 0)))
        decision_id = _resolve_operator_decision_id(payload, metadata, generation=generation, evaluation_index=evaluation_index)
        parents = _resolve_operator_parents(payload, metadata)
        rows.append(
            {
                "decision_id": decision_id,
                "generation": generation,
                "operator_name": str(payload.get("operator_name") or payload.get("operator_id") or "unknown"),
                "parents": parents,
                "offspring": _resolve_operator_offspring(
                    payload,
                    decision_id=decision_id,
                    generation=generation,
                    evaluation_index=evaluation_index,
                ),
                "params_digest": _resolve_operator_params_digest(payload, metadata),
                "wall_ms": _resolve_operator_wall_ms(payload, metadata),
            }
        )
    return rows


def _resolve_operator_decision_id(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    *,
    generation: int,
    evaluation_index: int,
) -> str | None:
    direct_decision_id = _normalized_trace_identifier(payload.get("decision_id")) or _normalized_trace_identifier(
        metadata.get("decision_id")
    )
    if direct_decision_id is not None:
        return direct_decision_id
    raw_decision_index = payload.get("decision_index", metadata.get("decision_index"))
    decision_index = 0 if raw_decision_index is None else int(raw_decision_index)
    raw_decision_eval = payload.get("decision_evaluation_index", metadata.get("decision_evaluation_index"))
    decision_evaluation_index = evaluation_index if raw_decision_eval is None else int(raw_decision_eval)
    return format_decision_id(int(generation), int(decision_evaluation_index), int(decision_index))


def _resolve_operator_parents(payload: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    direct_parents = payload.get("parents", metadata.get("parents"))
    if isinstance(direct_parents, Sequence) and not isinstance(direct_parents, (str, bytes)):
        parent_labels = [str(value) for value in direct_parents]
        if parent_labels:
            return parent_labels
    parent_indices = payload.get("parent_indices", metadata.get("parent_indices"))
    if isinstance(parent_indices, Sequence) and not isinstance(parent_indices, (str, bytes)):
        parent_labels = [f"parent-{int(value)}" for value in parent_indices]
        if parent_labels:
            return parent_labels
    parent_count = int(payload.get("parent_count", 0) or 0)
    return [f"parent-{index}" for index in range(parent_count)]


def _resolve_operator_offspring(
    payload: dict[str, Any],
    *,
    decision_id: str | None,
    generation: int,
    evaluation_index: int,
) -> list[str]:
    direct_offspring = payload.get("offspring")
    if isinstance(direct_offspring, Sequence) and not isinstance(direct_offspring, (str, bytes)):
        offspring_labels = [str(value) for value in direct_offspring]
        if offspring_labels:
            return offspring_labels
    if decision_id is not None:
        return [decision_id]
    return [f"g{generation:03d}-e{evaluation_index:04d}"]


def _resolve_operator_params_digest(payload: dict[str, Any], metadata: dict[str, Any]) -> str:
    direct_digest = str(payload.get("params_digest", "") or "").strip()
    if direct_digest:
        return direct_digest
    digest_payload = payload.get("params", metadata.get("params"))
    if digest_payload is None:
        digest_payload = {
            "operator_id": payload.get("operator_name") or payload.get("operator_id"),
            "parent_count": payload.get("parent_count"),
            "parent_vectors": payload.get("parent_vectors"),
            "proposal_vector": payload.get("proposal_vector"),
            "repaired_vector": payload.get("repaired_vector", metadata.get("repaired_vector")),
            "metadata": {
                key: value
                for key, value in metadata.items()
                if key not in {"wall_ms", "decision_id"}
            },
        }
    serialized = json.dumps(digest_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def _resolve_operator_wall_ms(payload: dict[str, Any], metadata: dict[str, Any]) -> float:
    wall_ms = payload.get("wall_ms", metadata.get("wall_ms"))
    return 0.0 if wall_ms is None else float(wall_ms)


def _normalized_trace_identifier(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text
