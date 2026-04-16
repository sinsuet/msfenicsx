"""LLM decision-log and key-decision summaries for the new run tree."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optimizers.llm_summary import build_mode_llm_summaries
from optimizers.mode_summary import build_mode_summaries
from optimizers.run_telemetry import load_jsonl_rows


def build_llm_decision_summaries(mode_root: str | Path) -> dict[str, str]:
    root = Path(mode_root)
    summaries_root = root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    build_mode_summaries(root)
    build_mode_llm_summaries(root)
    decision_rows: list[dict[str, Any]] = []

    for seed_root in _iter_seed_roots(root):
        seed = int(seed_root.name.removeprefix("seed-"))
        timeline_lookup = {
            int(row["evaluation_index"]): row
            for row in load_jsonl_rows(summaries_root / f"progress_timeline__seed-{seed}.jsonl")
        }
        request_rows = _accepted_trace_lookup(load_jsonl_rows(seed_root / "llm_request_trace.jsonl"))
        response_rows = _accepted_trace_lookup(load_jsonl_rows(seed_root / "llm_response_trace.jsonl"))
        controller_rows = {
            int(row["evaluation_index"]): row
            for row in _load_optional_json(seed_root / "controller_trace.json")
        }
        operator_rows = {
            int(row["evaluation_index"]): row
            for row in _load_optional_json(seed_root / "operator_trace.json")
        }
        evaluation_ids = sorted(set(request_rows) | set(response_rows) | set(controller_rows))
        for evaluation_index in evaluation_ids:
            request_row = request_rows.get(evaluation_index, {})
            response_row = response_rows.get(evaluation_index, {})
            controller_row = controller_rows.get(evaluation_index, {})
            operator_row = operator_rows.get(evaluation_index, {})
            progress_row = timeline_lookup.get(evaluation_index, {})
            decision_rows.append(
                {
                    "mode_id": root.name,
                    "seed": seed,
                    "evaluation_index": evaluation_index,
                    "generation_index": int(
                        request_row.get("generation_index")
                        or response_row.get("generation_index")
                        or controller_row.get("generation_index")
                        or 0
                    ),
                    "candidate_operator_ids": list(
                        request_row.get("candidate_operator_ids")
                        or controller_row.get("candidate_operator_ids")
                        or []
                    ),
                    "selected_operator_id": str(
                        response_row.get("selected_operator_id")
                        or controller_row.get("selected_operator_id")
                        or ""
                    ),
                    "system_prompt": str(request_row.get("system_prompt", "")),
                    "user_prompt": str(request_row.get("user_prompt", "")),
                    "response_text": str(response_row.get("response_text", "")),
                    "controller_rationale": str(controller_row.get("rationale", "")),
                    "fallback_used": bool(
                        response_row.get("fallback_used")
                        or dict(controller_row.get("metadata", {})).get("fallback_used", False)
                    ),
                    "prompt_ref": f"seeds/seed-{seed}/llm_request_trace.jsonl#evaluation_index={evaluation_index}",
                    "response_ref": f"seeds/seed-{seed}/llm_response_trace.jsonl#evaluation_index={evaluation_index}",
                    "controller_ref": f"seeds/seed-{seed}/controller_trace.json#evaluation_index={evaluation_index}",
                    "operator_ref": f"seeds/seed-{seed}/operator_trace.json#evaluation_index={evaluation_index}",
                    "first_feasible_eval_so_far": progress_row.get("first_feasible_eval_so_far"),
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
        "decision_ref": f"summaries/llm_decision_log.jsonl#evaluation_index={int(row['evaluation_index'])}",
    }


def _iter_seed_roots(mode_root: Path) -> list[Path]:
    seeds_root = mode_root / "seeds"
    if not seeds_root.exists():
        return []
    return sorted(
        [path for path in seeds_root.iterdir() if path.is_dir() and path.name.startswith("seed-")],
        key=lambda path: int(path.name.removeprefix("seed-")),
    )


def _load_optional_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _accepted_trace_lookup(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for row in rows:
        for evaluation_index in _accepted_evaluation_indices(row):
            lookup[int(evaluation_index)] = row
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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
