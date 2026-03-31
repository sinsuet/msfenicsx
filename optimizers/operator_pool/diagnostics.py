"""Cheap local diagnostics for controller-trace artifacts."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.trace import ControllerTraceRow


def analyze_controller_trace(path: str | Path) -> dict[str, Any]:
    trace_path = Path(path)
    rows = json.loads(trace_path.read_text(encoding="utf-8"))
    controller_rows = [ControllerTraceRow.from_dict(dict(row)) for row in rows]
    summary = _summarize_controller_rows(controller_rows)
    summary["trace_path"] = str(trace_path)
    return summary


def save_controller_trace_summary(path: str | Path, summary: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")


def _summarize_controller_rows(rows: Sequence[ControllerTraceRow]) -> dict[str, Any]:
    aggregate_phase_counts: Counter[str] = Counter()
    aggregate_reason_code_counts: Counter[str] = Counter()
    phase_buckets = {
        "cold_start": _new_phase_bucket(),
        "prefeasible": _new_phase_bucket(),
        "post_feasible": _new_phase_bucket(),
        "unknown": _new_phase_bucket(),
    }
    current_speculative_streak = 0
    current_same_operator_streak = 0
    current_bucket = "unknown"
    current_operator_id = ""
    fallback_count = 0
    llm_valid_count = 0

    for row in rows:
        bucket = _phase_bucket(_policy_phase(row))
        phase_buckets[bucket]["decision_count"] += 1
        aggregate_phase_counts[bucket] += 1

        fallback_used = bool(row.metadata.get("fallback_used", False))
        if fallback_used:
            fallback_count += 1
            phase_buckets[bucket]["fallback_count"] += 1
        else:
            llm_valid_count += 1
            phase_buckets[bucket]["llm_valid_count"] += 1

        reason_codes = _reason_codes(row.metadata.get("guardrail_reason_codes", []))
        if bool(row.metadata.get("guardrail_policy_reset_active", False)) or "prefeasible_forced_reset" in reason_codes:
            phase_buckets[bucket]["forced_reset_count"] += 1
        for code in reason_codes:
            aggregate_reason_code_counts[code] += 1
            phase_buckets[bucket]["reason_code_counts"][code] += 1

        operator_family = _operator_family(row.selected_operator_id)
        if bucket != current_bucket:
            current_speculative_streak = 0
            current_same_operator_streak = 0
            current_operator_id = ""
            current_bucket = bucket

        if not fallback_used and operator_family == "speculative_custom":
            current_speculative_streak += 1
            phase_buckets[bucket]["max_speculative_family_streak"] = max(
                phase_buckets[bucket]["max_speculative_family_streak"],
                current_speculative_streak,
            )
        else:
            current_speculative_streak = 0

        if row.selected_operator_id == current_operator_id:
            current_same_operator_streak += 1
        else:
            current_operator_id = row.selected_operator_id
            current_same_operator_streak = 1
        phase_buckets[bucket]["max_same_operator_streak"] = max(
            phase_buckets[bucket]["max_same_operator_streak"],
            current_same_operator_streak,
        )

    return {
        "aggregate": {
            "decision_count": len(rows),
            "fallback_count": fallback_count,
            "llm_valid_count": llm_valid_count,
            "phase_counts": dict(aggregate_phase_counts),
            "reason_code_counts": dict(aggregate_reason_code_counts),
        },
        "cold_start": _finalize_phase_bucket(phase_buckets["cold_start"]),
        "prefeasible": _finalize_phase_bucket(phase_buckets["prefeasible"]),
        "post_feasible": _finalize_phase_bucket(phase_buckets["post_feasible"]),
        "unknown": _finalize_phase_bucket(phase_buckets["unknown"]),
    }


def _new_phase_bucket() -> dict[str, Any]:
    return {
        "decision_count": 0,
        "fallback_count": 0,
        "llm_valid_count": 0,
        "forced_reset_count": 0,
        "max_speculative_family_streak": 0,
        "max_same_operator_streak": 0,
        "reason_code_counts": Counter(),
    }


def _finalize_phase_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_count": int(bucket["decision_count"]),
        "fallback_count": int(bucket["fallback_count"]),
        "llm_valid_count": int(bucket["llm_valid_count"]),
        "forced_reset_count": int(bucket["forced_reset_count"]),
        "max_speculative_family_streak": int(bucket["max_speculative_family_streak"]),
        "max_same_operator_streak": int(bucket["max_same_operator_streak"]),
        "reason_code_counts": dict(bucket["reason_code_counts"]),
    }


def _phase_bucket(phase: str) -> str:
    normalized = phase.strip().lower()
    if normalized == "cold_start":
        return "cold_start"
    if normalized.startswith("prefeasible"):
        return "prefeasible"
    if normalized.startswith("post_feasible") or normalized.startswith("feasible"):
        return "post_feasible"
    return "unknown"


def _policy_phase(row: ControllerTraceRow) -> str:
    policy_phase = row.metadata.get("guardrail_policy_phase")
    if policy_phase:
        return str(policy_phase)
    if row.phase:
        return str(row.phase)
    return "unknown"


def _reason_codes(values: Any) -> list[str]:
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return [str(value) for value in values]
    if values:
        return [str(values)]
    return []


def _operator_family(operator_id: str) -> str:
    try:
        return get_operator_behavior_profile(operator_id).family
    except KeyError:
        normalized = str(operator_id)
        if normalized.startswith("native_"):
            return "native_baseline"
        return "unknown"
