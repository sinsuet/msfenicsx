"""LLM decision-log and key-decision summaries for the new run tree."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optimizers.llm_summary import build_mode_llm_summaries
from optimizers.mode_summary import build_mode_summaries
from optimizers.operator_pool.semantic_tasks import semantic_task_for_operator
from optimizers.run_telemetry import load_jsonl_rows
from optimizers.traces.llm_trace_io import (
    iter_mode_seed_roots,
    materialize_request_trace_rows,
    materialize_response_trace_rows,
    resolve_seed_trace_path,
)


def build_llm_decision_summaries(mode_root: str | Path) -> dict[str, str]:
    root = Path(mode_root)
    summaries_root = root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    build_mode_summaries(root)
    build_mode_llm_summaries(root)
    decision_rows: list[dict[str, Any]] = []
    seed_summary_rows = _load_summary_seed_rows(summaries_root / "seed_summary.json")
    progress_by_bundle = _progress_rows_by_bundle(root, seed_summary_rows)

    for seed_root in iter_mode_seed_roots(root):
        bundle_progress = progress_by_bundle.get(seed_root.resolve(), {})
        seed = int(bundle_progress.get("seed") or _resolve_benchmark_seed(seed_root) or 0)
        timeline_lookup = dict(bundle_progress.get("timeline_lookup", {}))
        request_trace_path = resolve_seed_trace_path(seed_root, "llm_request_trace.jsonl")
        response_trace_path = resolve_seed_trace_path(seed_root, "llm_response_trace.jsonl")
        request_rows_by_decision_id = _accepted_trace_lookup_by_decision_id(
            materialize_request_trace_rows(
                seed_root,
                load_jsonl_rows(request_trace_path) if request_trace_path.exists() else [],
            )
        )
        response_rows_by_decision_id = _accepted_trace_lookup_by_decision_id(
            materialize_response_trace_rows(
                seed_root,
                load_jsonl_rows(response_trace_path) if response_trace_path.exists() else [],
            )
        )
        controller_rows_by_decision_id = _load_controller_rows_by_decision_id(seed_root)
        operator_rows_by_decision_id = _load_operator_rows_by_decision_id(seed_root)
        decision_ids = sorted(
            set(request_rows_by_decision_id)
            | set(response_rows_by_decision_id)
            | set(controller_rows_by_decision_id)
            | set(operator_rows_by_decision_id),
            key=_decision_sort_key,
        )
        for decision_id in decision_ids:
            request_row = request_rows_by_decision_id.get(decision_id, {})
            response_row = response_rows_by_decision_id.get(decision_id, {})
            controller_row = controller_rows_by_decision_id.get(decision_id, {})
            operator_row = operator_rows_by_decision_id.get(decision_id, {})
            evaluation_index = _decision_evaluation_index(
                decision_id,
                request_row=request_row,
                response_row=response_row,
                controller_row=controller_row,
            )
            progress_row = timeline_lookup.get(evaluation_index, {})
            decision_rows.append(
                {
                    "mode_id": str(bundle_progress.get("mode_id") or _resolve_mode_id(root)),
                    "seed": seed,
                    "decision_id": decision_id,
                    "evaluation_index": evaluation_index,
                    "generation_index": int(
                        request_row.get("generation_index")
                        or response_row.get("generation_index")
                        or controller_row.get("generation_index")
                        or _decision_generation_index(decision_id)
                    ),
                    "candidate_operator_ids": list(
                        request_row.get("candidate_operator_ids")
                        or controller_row.get("candidate_operator_ids")
                        or controller_row.get("operator_pool_snapshot")
                        or []
                    ),
                    "selected_operator_id": str(
                        response_row.get("selected_operator_id")
                        or controller_row.get("selected_operator_id")
                        or controller_row.get("operator_selected")
                        or ""
                    ),
                    "selected_semantic_task": _selected_semantic_task(
                        response_row=response_row,
                        controller_row=controller_row,
                    ),
                    "system_prompt": str(request_row.get("system_prompt", "")),
                    "user_prompt": str(request_row.get("user_prompt", "")),
                    "response_text": str(response_row.get("response_text", "")),
                    "controller_rationale": str(controller_row.get("rationale", "")),
                    "fallback_used": bool(
                        response_row.get("fallback_used")
                        or controller_row.get("fallback_used")
                        or dict(controller_row.get("metadata", {})).get("fallback_used", False)
                    ),
                    "prompt_ref": str(
                        request_row.get("prompt_ref")
                        or f"seeds/seed-{seed}/traces/llm_request_trace.jsonl#decision_id={decision_id}"
                    ),
                    "response_ref": str(
                        response_row.get("response_ref")
                        or f"seeds/seed-{seed}/traces/llm_response_trace.jsonl#decision_id={decision_id}"
                    ),
                    "controller_ref": f"seeds/seed-{seed}/traces/controller_trace.jsonl#decision_id={decision_id}",
                    "operator_ref": f"seeds/seed-{seed}/traces/operator_trace.jsonl#decision_id={decision_id}",
                    "pde_evaluation_index": progress_row.get("pde_evaluation_index"),
                    "first_feasible_eval_so_far": progress_row.get("first_feasible_eval_so_far"),
                    "first_feasible_pde_eval_so_far": progress_row.get("first_feasible_pde_eval_so_far"),
                    "feasible_count_so_far": progress_row.get("feasible_count_so_far"),
                    "pareto_size_so_far": progress_row.get("pareto_size_so_far"),
                    "best_temperature_max_so_far": progress_row.get("best_temperature_max_so_far"),
                    "best_gradient_rms_so_far": progress_row.get("best_gradient_rms_so_far"),
                    "best_total_constraint_violation_so_far": progress_row.get("best_total_constraint_violation_so_far"),
                }
            )

    decision_rows.sort(key=lambda row: (int(row["seed"]), int(row["evaluation_index"])))
    key_decisions = _build_key_decisions(decision_rows)

    decision_log_path = summaries_root / "llm_decision_log.jsonl"
    key_decisions_path = summaries_root / "llm_key_decisions.json"
    _write_jsonl(decision_log_path, decision_rows)
    key_decisions_path.write_text(json.dumps(key_decisions, indent=2) + "\n", encoding="utf-8")
    return {
        "llm_decision_log": str(decision_log_path.relative_to(root).as_posix()),
        "llm_key_decisions": str(key_decisions_path.relative_to(root).as_posix()),
    }


def _selected_semantic_task(
    *,
    response_row: dict[str, Any],
    controller_row: dict[str, Any],
) -> str:
    explicit_task = str(
        response_row.get("selected_semantic_task")
        or controller_row.get("selected_semantic_task")
        or dict(controller_row.get("metadata", {})).get("selected_semantic_task")
        or ""
    ).strip()
    if explicit_task:
        return explicit_task
    operator_id = str(
        response_row.get("selected_operator_id")
        or controller_row.get("selected_operator_id")
        or controller_row.get("operator_selected")
        or ""
    ).strip()
    return semantic_task_for_operator(operator_id) if operator_id else ""


def _build_key_decisions(decision_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    previous_by_seed: dict[int, dict[str, Any]] = {}
    for row in decision_rows:
        seed = int(row["seed"])
        previous = previous_by_seed.get(seed, {})
        current_first_feasible = row.get("first_feasible_eval_so_far")
        previous_first_feasible = previous.get("first_feasible_eval_so_far")
        current_pareto_size = int(row.get("pareto_size_so_far") or 0)
        previous_pareto_size = int(previous.get("pareto_size_so_far") or 0)
        current_peak = row.get("best_temperature_max_so_far")
        previous_peak = previous.get("best_temperature_max_so_far")
        current_gradient = row.get("best_gradient_rms_so_far")
        previous_gradient = previous.get("best_gradient_rms_so_far")
        current_violation = row.get("best_total_constraint_violation_so_far")
        previous_violation = previous.get("best_total_constraint_violation_so_far")

        if current_first_feasible is not None and previous_first_feasible is None and int(current_first_feasible) == int(row["evaluation_index"]):
            rows.append(_trigger_row("first_feasible_trigger", row))
        if current_pareto_size > previous_pareto_size:
            rows.append(_trigger_row("pareto_expansion_trigger", row))
        if current_peak is not None and (previous_peak is None or float(current_peak) < float(previous_peak)):
            rows.append(_trigger_row("peak_drop_trigger", row))
        if current_gradient is not None and (previous_gradient is None or float(current_gradient) < float(previous_gradient)):
            rows.append(_trigger_row("gradient_drop_trigger", row))
        if (
            current_violation is not None
            and previous_violation is not None
            and float(previous_violation) > 0.0
            and float(current_violation) == 0.0
        ):
            rows.append(_trigger_row("violation_collapse_trigger", row))
        if previous.get("selected_operator_id") and row.get("selected_operator_id") and row["selected_operator_id"] != previous["selected_operator_id"]:
            rows.append(_trigger_row("operator_switch_trigger", row))
        if bool(row.get("fallback_used", False)) and int(row.get("feasible_count_so_far") or 0) > int(previous.get("feasible_count_so_far") or 0):
            rows.append(_trigger_row("fallback_rescue_trigger", row))
        previous_by_seed[seed] = row
    return {
        "row_count": int(len(rows)),
        "rows": rows,
    }


def _trigger_row(trigger_type: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "trigger_type": trigger_type,
        "evaluation_index": int(row["evaluation_index"]),
        "seed": int(row["seed"]),
        "selected_operator_id": row.get("selected_operator_id"),
        "prompt_ref": row.get("prompt_ref"),
        "response_ref": row.get("response_ref"),
        "decision_ref": f"summaries/llm_decision_log.jsonl#decision_id={row['decision_id']}",
    }


def _seed_name(seed_root: Path) -> str:
    if seed_root.name.startswith("seed-"):
        return seed_root.name
    if seed_root.parent.name.startswith("seed-"):
        return seed_root.parent.name
    return seed_root.name


def _load_optional_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _load_summary_seed_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _progress_rows_by_bundle(root: Path, rows: list[dict[str, Any]]) -> dict[Path, dict[str, Any]]:
    bundle_progress: dict[Path, dict[str, Any]] = {}
    mode_id = _resolve_mode_id(root)
    for row in rows:
        bundle_ref = str(row.get("bundle_root") or ".")
        timeline_ref = row.get("progress_timeline")
        if not timeline_ref:
            continue
        timeline_path = root / str(timeline_ref)
        if not timeline_path.exists():
            continue
        bundle_root = (root / bundle_ref).resolve()
        bundle_progress[bundle_root] = {
            "seed": row.get("seed"),
            "mode_id": mode_id,
            "timeline_lookup": {
                int(progress_row["evaluation_index"]): progress_row
                for progress_row in load_jsonl_rows(timeline_path)
            },
        }
    return bundle_progress


def _resolve_mode_id(root: Path) -> str:
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("mode_id"):
            return str(payload["mode_id"])
    run_yaml_path = root / "run.yaml"
    if run_yaml_path.exists():
        import yaml

        payload = yaml.safe_load(run_yaml_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("mode"):
            return str(payload["mode"])
    return root.name


def _resolve_benchmark_seed(bundle_root: Path) -> int | None:
    run_yaml_path = bundle_root / "run.yaml"
    if run_yaml_path.exists():
        import yaml

        payload = yaml.safe_load(run_yaml_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            benchmark_seed = payload.get("seeds", {}).get("benchmark")
            if benchmark_seed is not None:
                return int(benchmark_seed)
    optimization_result_path = bundle_root / "optimization_result.json"
    if optimization_result_path.exists():
        payload = json.loads(optimization_result_path.read_text(encoding="utf-8"))
        benchmark_seed = (
            payload.get("run_meta", {}).get("benchmark_seed")
            or payload.get("provenance", {}).get("benchmark_source", {}).get("seed")
        )
        if benchmark_seed is not None:
            return int(benchmark_seed)
    if bundle_root.name.startswith("seed-"):
        return int(bundle_root.name.removeprefix("seed-"))
    if bundle_root.parent.name.startswith("seed-"):
        return int(bundle_root.parent.name.removeprefix("seed-"))
    return None


def _accepted_trace_lookup(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for row in rows:
        for evaluation_index in _accepted_evaluation_indices(row):
            lookup[int(evaluation_index)] = row
    return lookup


def _accepted_trace_lookup_by_decision_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        decision_id = _normalized_decision_id(row.get("decision_id"))
        if decision_id is None:
            continue
        if not _accepted_evaluation_indices(row):
            continue
        lookup[decision_id] = row
    return lookup


def _accepted_evaluation_indices(row: dict[str, Any]) -> list[int]:
    raw_indices = row.get("accepted_evaluation_indices")
    if isinstance(raw_indices, list) and raw_indices:
        return [int(value) for value in raw_indices]
    accepted_index = row.get("accepted_evaluation_index")
    if accepted_index is not None:
        return [int(accepted_index)]
    if row.get("accepted_for_evaluation") is False:
        return []
    evaluation_index = row.get("evaluation_index")
    if evaluation_index is None:
        return []
    return [int(evaluation_index)]


def _load_controller_rows_by_decision_id(seed_root: Path) -> dict[str, dict[str, Any]]:
    trace_path = resolve_seed_trace_path(seed_root, "controller_trace.jsonl")
    rows = [dict(row) for row in load_jsonl_rows(trace_path)] if trace_path.exists() else []
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        payload = dict(row)
        decision_id = _normalized_decision_id(payload.get("decision_id"))
        if decision_id is not None:
            lookup[decision_id] = payload
    return lookup


def _load_operator_rows_by_decision_id(seed_root: Path) -> dict[str, dict[str, Any]]:
    trace_path = resolve_seed_trace_path(seed_root, "operator_trace.jsonl")
    rows = [dict(row) for row in load_jsonl_rows(trace_path)] if trace_path.exists() else []
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        payload = dict(row)
        decision_id = _normalized_decision_id(payload.get("decision_id"))
        if decision_id is not None:
            lookup[decision_id] = payload
    return lookup


def _normalized_decision_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"none", "null"}:
        return None
    return text


def _decision_sort_key(decision_id: str) -> tuple[int, int, int, str]:
    return (
        _decision_generation_index(decision_id),
        _decision_evaluation_index(decision_id),
        _decision_sequence_index(decision_id),
        decision_id,
    )


def _decision_generation_index(decision_id: str) -> int:
    try:
        return int(str(decision_id).split("-", 2)[0].removeprefix("g"))
    except (TypeError, ValueError, IndexError):
        return 0


def _decision_evaluation_index(
    decision_id: str,
    *,
    request_row: dict[str, Any] | None = None,
    response_row: dict[str, Any] | None = None,
    controller_row: dict[str, Any] | None = None,
) -> int:
    for row in (request_row or {}, response_row or {}, controller_row or {}):
        value = row.get("evaluation_index")
        if value is not None:
            return int(value)
    return _decision_evaluation_index_from_id(decision_id)


def _decision_evaluation_index_from_id(decision_id: str) -> int:
    try:
        return int(str(decision_id).split("-", 2)[1].removeprefix("e"))
    except (TypeError, ValueError, IndexError):
        return 0


def _decision_sequence_index(decision_id: str) -> int:
    try:
        return int(str(decision_id).split("-", 2)[2].removeprefix("d"))
    except (TypeError, ValueError, IndexError):
        return 0


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
