"""Cheap local diagnostics for controller-trace artifacts."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.operator_pool.domain_state import dominant_violation_family, total_violation
from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.route_families import operator_route_family, route_family_entropy
from optimizers.operator_pool.trace import ControllerTraceRow
from optimizers.run_telemetry import load_jsonl_rows
from optimizers.traces.llm_trace_io import materialize_request_trace_rows, materialize_response_trace_rows


def analyze_controller_trace(
    path: str | Path,
    *,
    optimization_result_path: str | Path | None = None,
    operator_trace_path: str | Path | None = None,
    llm_request_trace_path: str | Path | None = None,
    llm_response_trace_path: str | Path | None = None,
) -> dict[str, Any]:
    trace_path = Path(path)
    controller_rows = sorted(
        _load_controller_trace_rows(trace_path),
        key=lambda row: (int(row.evaluation_index), int(row.generation_index)),
    )
    artifact_context = _load_artifact_context(optimization_result_path)
    summary = summarize_controller_rows(controller_rows, artifact_context=artifact_context)
    summary["trace_path"] = str(trace_path)

    if optimization_result_path is not None:
        summary["optimization_result_path"] = str(Path(optimization_result_path))
    if operator_trace_path is not None:
        operator_trace_rows = _load_jsonl_rows(operator_trace_path)
        summary["operator_trace"] = {
            "row_count": len(operator_trace_rows),
            "path": str(Path(operator_trace_path)),
        }
    llm_trace_summary = _summarize_llm_traces(
        llm_request_trace_path=llm_request_trace_path,
        llm_response_trace_path=llm_response_trace_path,
    )
    if llm_trace_summary is not None:
        summary["llm_trace"] = llm_trace_summary
    return summary


def save_controller_trace_summary(path: str | Path, summary: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")


def summarize_controller_rows(
    rows: Sequence[ControllerTraceRow],
    *,
    artifact_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    current_same_family_streak = 0
    current_stable_family_streak = 0
    current_stable_role_streak = 0
    current_dominant_violation_family = ""
    current_dominant_violation_streak = 0
    current_bucket = "unknown"
    current_operator_id = ""
    current_family = ""
    current_stable_family = ""
    current_stable_role = ""
    fallback_count = 0
    llm_valid_count = 0
    latest_eval_by_bucket: dict[str, int] = {}
    first_feasible_eval = None if artifact_context is None else artifact_context.get("first_feasible_eval")
    semantic_visible_count = 0
    semantic_candidate_total = 0
    semantic_selection_count = 0
    semantic_frontier_add_count = 0
    semantic_feasible_preservation_count = 0
    stable_vs_semantic_pareto_ownership: Counter[str] = Counter({"stable": 0, "semantic": 0})
    expand_family_outcomes: dict[str, dict[str, int]] = {}
    pareto_evaluation_indices = (
        set()
        if artifact_context is None
        else {int(value) for value in artifact_context.get("pareto_evaluation_indices", [])}
    )

    for row in rows:
        bucket = _phase_bucket(_policy_phase(row), first_feasible_eval=first_feasible_eval, evaluation_index=row.evaluation_index)
        phase_buckets[bucket]["decision_count"] += 1
        aggregate_phase_counts[bucket] += 1
        latest_eval_by_bucket[bucket] = int(row.evaluation_index)

        semantic_candidate_ids = [
            str(operator_id)
            for operator_id in _effective_candidate_operator_ids(row)
            if not _operator_is_stable(str(operator_id))
        ]
        if semantic_candidate_ids:
            semantic_visible_count += 1
        semantic_candidate_total += len(semantic_candidate_ids)
        selected_is_semantic = not _operator_is_stable(row.selected_operator_id)
        if selected_is_semantic:
            semantic_selection_count += 1

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
        phase_buckets[bucket]["family_mix"][operator_family] += 1
        if bucket != current_bucket:
            current_speculative_streak = 0
            current_same_operator_streak = 0
            current_same_family_streak = 0
            current_stable_family_streak = 0
            current_stable_role_streak = 0
            current_dominant_violation_family = ""
            current_dominant_violation_streak = 0
            current_operator_id = ""
            current_family = ""
            current_stable_family = ""
            current_stable_role = ""
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

        if operator_family == current_family:
            current_same_family_streak += 1
        else:
            current_family = operator_family
            current_same_family_streak = 1
        phase_buckets[bucket]["max_same_family_streak"] = max(
            phase_buckets[bucket]["max_same_family_streak"],
            current_same_family_streak,
        )

        operator_role = _operator_role(row.selected_operator_id)
        stable_family = operator_family if _operator_is_stable(row.selected_operator_id) else ""
        stable_role = operator_role if _operator_is_stable(row.selected_operator_id) else ""
        if stable_family:
            if stable_family == current_stable_family:
                current_stable_family_streak += 1
            else:
                current_stable_family = stable_family
                current_stable_family_streak = 1
            phase_buckets[bucket]["max_stable_family_monopoly_streak"] = max(
                phase_buckets[bucket]["max_stable_family_monopoly_streak"],
                current_stable_family_streak,
            )
        else:
            current_stable_family = ""
            current_stable_family_streak = 0

        if stable_role:
            if stable_role == current_stable_role:
                current_stable_role_streak += 1
            else:
                current_stable_role = stable_role
                current_stable_role_streak = 1
            phase_buckets[bucket]["max_stable_role_monopoly_streak"] = max(
                phase_buckets[bucket]["max_stable_role_monopoly_streak"],
                current_stable_role_streak,
            )
        else:
            current_stable_role = ""
            current_stable_role_streak = 0

        reset_active = bool(row.metadata.get("guardrail_policy_reset_active", False)) or "prefeasible_forced_reset" in reason_codes
        if bucket == "prefeasible" and reset_active:
            phase_buckets[bucket]["reset_window_count"] += 1
            if stable_family:
                phase_buckets[bucket]["reset_family_counts"][stable_family] += 1

        entry_metrics = (
            {}
            if artifact_context is None
            else dict(artifact_context.get("entry_metrics", {}).get(int(row.evaluation_index), {}))
        )
        entry_convert_active = (
            bool(row.metadata.get("entry_convert_active", False))
            or bool(entry_metrics.get("entry_convert_active", False))
            or _policy_phase(row) == "prefeasible_convert"
        )
        if bucket == "prefeasible" and entry_convert_active:
            phase_buckets[bucket]["entry_convert_window_count"] += 1
            supported_entry_candidate_share = _supported_entry_candidate_share(row, entry_metrics=entry_metrics)
            if supported_entry_candidate_share is not None:
                phase_buckets[bucket]["supported_entry_candidate_share_total"] += supported_entry_candidate_share
                phase_buckets[bucket]["supported_entry_candidate_share_count"] += 1

        dominant_violation_family_name = str(
            row.metadata.get("dominant_violation_family", "") or entry_metrics.get("dominant_violation_family", "")
        ).strip()
        if bucket == "prefeasible" and dominant_violation_family_name:
            if dominant_violation_family_name == current_dominant_violation_family:
                current_dominant_violation_streak += 1
            else:
                current_dominant_violation_family = dominant_violation_family_name
                current_dominant_violation_streak = 1
            phase_buckets[bucket]["max_dominant_violation_persistence_streak"] = max(
                phase_buckets[bucket]["max_dominant_violation_persistence_streak"],
                current_dominant_violation_streak,
            )
        elif bucket == "prefeasible":
            current_dominant_violation_family = ""
            current_dominant_violation_streak = 0

        near_feasible_relief = bool(row.metadata.get("near_feasible_relief", False)) or bool(
            entry_metrics.get("near_feasible_relief", False)
        )
        if bucket == "prefeasible" and near_feasible_relief:
            phase_buckets[bucket]["near_feasible_relief_count"] += 1
            phase_buckets[bucket]["last_near_feasible_relief_eval"] = int(row.evaluation_index)

        if artifact_context is None:
            continue
        evaluation_metrics = artifact_context["evaluation_metrics"].get(int(row.evaluation_index), {})
        policy_phase = _policy_phase(row)
        if policy_phase.startswith("post_feasible_expand"):
            route_family = operator_route_family(row.selected_operator_id)
            family_summary = expand_family_outcomes.setdefault(
                route_family,
                {
                    "selection_count": 0,
                    "frontier_add_count": 0,
                    "feasible_regression_count": 0,
                    "feasible_preservation_count": 0,
                },
            )
            family_summary["selection_count"] += 1
            if evaluation_metrics.get("frontier_add", False):
                family_summary["frontier_add_count"] += 1
            if evaluation_metrics.get("feasible_regression", False):
                family_summary["feasible_regression_count"] += 1
            if evaluation_metrics.get("feasible_preservation", False):
                family_summary["feasible_preservation_count"] += 1
        if evaluation_metrics.get("frontier_add", False):
            phase_buckets[bucket]["frontier_add_count"] += 1
            if selected_is_semantic:
                semantic_frontier_add_count += 1
        if evaluation_metrics.get("feasible_regression", False):
            phase_buckets[bucket]["feasible_regression_count"] += 1
        if evaluation_metrics.get("feasible_preservation", False):
            phase_buckets[bucket]["feasible_preservation_count"] += 1
            if selected_is_semantic:
                semantic_feasible_preservation_count += 1
        if int(row.evaluation_index) in pareto_evaluation_indices:
            stable_vs_semantic_pareto_ownership["semantic" if selected_is_semantic else "stable"] += 1

    last_frontier_add_eval = None if artifact_context is None else artifact_context.get("last_frontier_add_eval")
    for bucket_name, bucket in phase_buckets.items():
        latest_eval = latest_eval_by_bucket.get(bucket_name)
        if bucket_name == "post_feasible" and latest_eval is not None and last_frontier_add_eval is not None:
            bucket["evaluations_since_frontier_add"] = max(0, int(latest_eval) - int(last_frontier_add_eval))
        if (
            bucket_name == "prefeasible"
            and latest_eval is not None
            and bucket["last_near_feasible_relief_eval"] is not None
        ):
            bucket["evaluations_since_last_near_feasible_relief"] = max(
                0,
                int(latest_eval) - int(bucket["last_near_feasible_relief_eval"]),
            )

    summary = {
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
        "family_mix": {
            bucket_name: dict(phase_buckets[bucket_name]["family_mix"])
            for bucket_name in ("cold_start", "prefeasible", "post_feasible", "unknown")
        },
        "semantic_visibility_rate": (
            0.0 if not rows else float(semantic_visible_count) / float(len(rows))
        ),
        "semantic_candidate_count_avg": (
            0.0 if not rows else float(semantic_candidate_total) / float(len(rows))
        ),
        "semantic_selection_rate": (
            0.0 if not rows else float(semantic_selection_count) / float(len(rows))
        ),
        "semantic_frontier_add_count": int(semantic_frontier_add_count),
        "semantic_feasible_preservation_count": int(semantic_feasible_preservation_count),
        "stable_vs_semantic_pareto_ownership": {
            "stable": int(stable_vs_semantic_pareto_ownership["stable"]),
            "semantic": int(stable_vs_semantic_pareto_ownership["semantic"]),
        },
        "route_family_counts": _route_family_counts(rows),
        "route_family_entropy": route_family_entropy(_route_family_counts(rows)),
        "expand_route_family_counts": _route_family_counts(rows, phase_prefix="post_feasible_expand"),
        "expand_route_family_entropy": route_family_entropy(
            _route_family_counts(rows, phase_prefix="post_feasible_expand")
        ),
        "expand_family_outcomes": expand_family_outcomes,
    }
    if artifact_context is None:
        return summary
    summary["aggregate"].update(
        {
            "first_feasible_eval": artifact_context.get("first_feasible_eval"),
            "rows_before_first_feasible": sum(
                1 for row in rows if _is_before_first_feasible(row.evaluation_index, artifact_context.get("first_feasible_eval"))
            ),
            "rows_after_first_feasible": sum(
                1
                for row in rows
                if _is_after_or_at_first_feasible(row.evaluation_index, artifact_context.get("first_feasible_eval"))
            ),
        }
    )
    return summary


def _new_phase_bucket() -> dict[str, Any]:
    return {
        "decision_count": 0,
        "fallback_count": 0,
        "llm_valid_count": 0,
        "forced_reset_count": 0,
        "max_speculative_family_streak": 0,
        "max_same_operator_streak": 0,
        "max_same_family_streak": 0,
        "max_stable_family_monopoly_streak": 0,
        "max_stable_role_monopoly_streak": 0,
        "reset_window_count": 0,
        "frontier_add_count": 0,
        "feasible_regression_count": 0,
        "feasible_preservation_count": 0,
        "evaluations_since_frontier_add": None,
        "max_dominant_violation_persistence_streak": 0,
        "near_feasible_relief_count": 0,
        "last_near_feasible_relief_eval": None,
        "evaluations_since_last_near_feasible_relief": None,
        "entry_convert_window_count": 0,
        "supported_entry_candidate_share_total": 0.0,
        "supported_entry_candidate_share_count": 0,
        "reason_code_counts": Counter(),
        "family_mix": Counter(),
        "reset_family_counts": Counter(),
    }


def _finalize_phase_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    reset_window_count = int(bucket["reset_window_count"])
    reset_family_counts = Counter(bucket["reset_family_counts"])
    finalized = {
        "decision_count": int(bucket["decision_count"]),
        "fallback_count": int(bucket["fallback_count"]),
        "llm_valid_count": int(bucket["llm_valid_count"]),
        "forced_reset_count": int(bucket["forced_reset_count"]),
        "max_speculative_family_streak": int(bucket["max_speculative_family_streak"]),
        "max_same_operator_streak": int(bucket["max_same_operator_streak"]),
        "max_same_family_streak": int(bucket["max_same_family_streak"]),
        "max_stable_family_monopoly_streak": int(bucket["max_stable_family_monopoly_streak"]),
        "max_stable_role_monopoly_streak": int(bucket["max_stable_role_monopoly_streak"]),
        "reset_window_count": reset_window_count,
        "global_explore_share_during_reset": (
            0.0 if reset_window_count <= 0 else float(reset_family_counts.get("global_explore", 0)) / float(reset_window_count)
        ),
        "local_refine_share_during_reset": (
            0.0 if reset_window_count <= 0 else float(reset_family_counts.get("local_refine", 0)) / float(reset_window_count)
        ),
        "native_baseline_share_during_reset": (
            0.0 if reset_window_count <= 0 else float(reset_family_counts.get("native_baseline", 0)) / float(reset_window_count)
        ),
        "frontier_add_count": int(bucket["frontier_add_count"]),
        "feasible_regression_count": int(bucket["feasible_regression_count"]),
        "feasible_preservation_count": int(bucket["feasible_preservation_count"]),
        "evaluations_since_frontier_add": (
            None
            if bucket["evaluations_since_frontier_add"] is None
            else int(bucket["evaluations_since_frontier_add"])
        ),
        "reason_code_counts": dict(bucket["reason_code_counts"]),
        "family_mix": dict(bucket["family_mix"]),
    }
    if int(bucket["entry_convert_window_count"]) > 0 or int(bucket["near_feasible_relief_count"]) > 0:
        finalized["max_dominant_violation_persistence_streak"] = int(
            bucket["max_dominant_violation_persistence_streak"]
        )
        finalized["near_feasible_relief_count"] = int(bucket["near_feasible_relief_count"])
        finalized["entry_convert_window_count"] = int(bucket["entry_convert_window_count"])
        finalized["evaluations_since_last_near_feasible_relief"] = (
            None
            if bucket["evaluations_since_last_near_feasible_relief"] is None
            else int(bucket["evaluations_since_last_near_feasible_relief"])
        )
        if int(bucket["supported_entry_candidate_share_count"]) > 0:
            finalized["supported_entry_candidate_share"] = float(
                bucket["supported_entry_candidate_share_total"]
            ) / float(bucket["supported_entry_candidate_share_count"])
    return finalized


def _phase_bucket(
    phase: str,
    *,
    first_feasible_eval: int | None,
    evaluation_index: int,
) -> str:
    normalized = phase.strip().lower()
    if normalized == "cold_start":
        return "cold_start"
    if normalized.startswith("prefeasible"):
        return "prefeasible"
    if normalized.startswith("post_feasible") or normalized.startswith("feasible"):
        return "post_feasible"
    if _is_before_first_feasible(evaluation_index, first_feasible_eval):
        return "prefeasible"
    if _is_after_or_at_first_feasible(evaluation_index, first_feasible_eval):
        return "post_feasible"
    return "unknown"


def _policy_phase(row: ControllerTraceRow) -> str:
    for key in ("policy_phase", "guardrail_policy_phase"):
        value = row.metadata.get(key)
        if value:
            return str(value)
    if row.phase:
        return str(row.phase)
    return "unknown"


def _reason_codes(values: Any) -> list[str]:
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return [str(value) for value in values]
    if values:
        return [str(values)]
    return []


def _supported_entry_candidate_share(
    row: ControllerTraceRow,
    *,
    entry_metrics: Mapping[str, Any] | None = None,
) -> float | None:
    if row.metadata.get("supported_entry_candidate_share") is not None:
        return float(row.metadata["supported_entry_candidate_share"])
    if row.metadata.get("supported_entry_candidate_count") is None:
        if entry_metrics is None or entry_metrics.get("supported_entry_candidate_share") is None:
            return None
        return float(entry_metrics["supported_entry_candidate_share"])
    candidate_count = len(tuple(row.candidate_operator_ids))
    if candidate_count <= 0:
        return 0.0
    return float(row.metadata["supported_entry_candidate_count"]) / float(candidate_count)


def _effective_candidate_operator_ids(row: ControllerTraceRow) -> tuple[str, ...]:
    candidate_ids = tuple(str(operator_id) for operator_id in row.candidate_operator_ids)
    filtered_operator_ids = {
        str(operator_id)
        for operator_id in row.metadata.get("guardrail_filtered_operator_ids", [])
    }
    if not filtered_operator_ids:
        return candidate_ids
    effective_ids = tuple(operator_id for operator_id in candidate_ids if operator_id not in filtered_operator_ids)
    return candidate_ids if not effective_ids else effective_ids


def _route_family_counts(
    rows: Sequence[ControllerTraceRow],
    *,
    phase_prefix: str | None = None,
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if phase_prefix is not None and not _policy_phase(row).startswith(phase_prefix):
            continue
        counter[operator_route_family(row.selected_operator_id)] += 1
    return dict(counter)


def _operator_family(operator_id: str) -> str:
    try:
        return get_operator_behavior_profile(operator_id).family
    except KeyError:
        normalized = str(operator_id)
        if normalized.startswith("native_"):
            return "native_baseline"
        return "unknown"


def _operator_role(operator_id: str) -> str:
    try:
        return get_operator_behavior_profile(operator_id).role
    except KeyError:
        return "unknown"


def _operator_is_stable(operator_id: str) -> bool:
    try:
        return get_operator_behavior_profile(operator_id).exploration_class == "stable"
    except KeyError:
        return str(operator_id).startswith("native_")


def _load_artifact_context(optimization_result_path: str | Path | None) -> dict[str, Any] | None:
    if optimization_result_path is None:
        return None
    payload = json.loads(Path(optimization_result_path).read_text(encoding="utf-8"))
    pareto_evaluation_indices = [
        int(row.get("evaluation_index", 0))
        for row in payload.get("pareto_front", [])
        if isinstance(row, Mapping) and row.get("evaluation_index") is not None
    ]
    history = sorted(
        [
            dict(row)
            for row in payload.get("history", [])
            if isinstance(row, Mapping) and "evaluation_index" in row
        ],
        key=lambda row: int(row.get("evaluation_index", 0)),
    )
    optimizer_history = [row for row in history if _counts_toward_optimizer_progress(row)]
    first_feasible_eval = payload.get("aggregate_metrics", {}).get("first_feasible_eval")
    if first_feasible_eval is None:
        feasible_evals = [
            int(row.get("evaluation_index", 0))
            for row in optimizer_history
            if bool(row.get("feasible", False))
        ]
        first_feasible_eval = None if not feasible_evals else min(feasible_evals)
    if first_feasible_eval is not None:
        first_feasible_eval = int(first_feasible_eval)

    prior_feasible_records: list[Mapping[str, Any]] = []
    evaluation_metrics: dict[int, dict[str, bool]] = {}
    entry_metrics: dict[int, dict[str, Any]] = {}
    last_frontier_add_eval: int | None = None
    best_prefeasible_violation = float("inf")
    for row in history:
        evaluation_index = int(row.get("evaluation_index", 0))
        feasible = bool(row.get("feasible", False))
        counts_toward_progress = _counts_toward_optimizer_progress(row)
        row_total_violation = total_violation(row)
        metrics = {
            "frontier_add": False,
            "feasible_regression": False,
            "feasible_preservation": False,
        }
        if counts_toward_progress and first_feasible_eval is not None and evaluation_index >= first_feasible_eval:
            if feasible:
                if _is_frontier_add(row, prior_feasible_records):
                    metrics["frontier_add"] = True
                    last_frontier_add_eval = evaluation_index
                else:
                    metrics["feasible_preservation"] = True
            else:
                metrics["feasible_regression"] = True
        evaluation_metrics[evaluation_index] = metrics
        entry_convert_active = (
            counts_toward_progress
            and
            not feasible
            and (
                row_total_violation <= 1.0
                or best_prefeasible_violation <= 1.0
            )
        )
        near_feasible_relief = (
            counts_toward_progress
            and
            not feasible
            and row_total_violation < best_prefeasible_violation
            and (
                row_total_violation <= 1.0
                or best_prefeasible_violation <= 1.0
            )
        )
        entry_metrics[evaluation_index] = {
            "entry_convert_active": entry_convert_active,
            "dominant_violation_family": dominant_violation_family(row),
            "near_feasible_relief": near_feasible_relief,
        }
        if counts_toward_progress and not feasible:
            best_prefeasible_violation = min(best_prefeasible_violation, row_total_violation)
        if counts_toward_progress and feasible:
            prior_feasible_records.append(row)

    return {
        "first_feasible_eval": first_feasible_eval,
        "evaluation_metrics": evaluation_metrics,
        "entry_metrics": entry_metrics,
        "last_frontier_add_eval": last_frontier_add_eval,
        "pareto_evaluation_indices": pareto_evaluation_indices,
    }


def _is_frontier_add(candidate: Mapping[str, Any], prior_feasible_records: Sequence[Mapping[str, Any]]) -> bool:
    candidate_tuple = _objective_tuple(candidate)
    if candidate_tuple is None:
        return False
    for record in prior_feasible_records:
        incumbent_tuple = _objective_tuple(record)
        if incumbent_tuple is None:
            continue
        if incumbent_tuple == candidate_tuple:
            return False
        if _dominates(incumbent_tuple, candidate_tuple):
            return False
    return True


def _objective_tuple(record: Mapping[str, Any]) -> tuple[float, ...] | None:
    objective_values = record.get("objective_values")
    if not isinstance(objective_values, Mapping) or not objective_values:
        return None
    items: list[tuple[str, float]] = []
    for objective_id, value in objective_values.items():
        objective_name = str(objective_id).lower()
        numeric_value = float(value)
        minimized_value = -numeric_value if "maximize" in objective_name else numeric_value
        items.append((str(objective_id), minimized_value))
    items.sort(key=lambda item: item[0])
    return tuple(value for _, value in items)


def _dominates(left: Sequence[float], right: Sequence[float]) -> bool:
    return all(lv <= rv for lv, rv in zip(left, right, strict=True)) and any(
        lv < rv for lv, rv in zip(left, right, strict=True)
    )


def _is_before_first_feasible(evaluation_index: int, first_feasible_eval: int | None) -> bool:
    return first_feasible_eval is not None and int(evaluation_index) < int(first_feasible_eval)


def _is_after_or_at_first_feasible(evaluation_index: int, first_feasible_eval: int | None) -> bool:
    return first_feasible_eval is not None and int(evaluation_index) >= int(first_feasible_eval)


def _counts_toward_optimizer_progress(record: Mapping[str, Any]) -> bool:
    return str(record.get("source", "")).strip().lower() != "baseline"


def _summarize_llm_traces(
    *,
    llm_request_trace_path: str | Path | None,
    llm_response_trace_path: str | Path | None,
) -> dict[str, Any] | None:
    if llm_request_trace_path is None and llm_response_trace_path is None:
        return None
    request_rows = [] if llm_request_trace_path is None else _load_materialized_request_rows(llm_request_trace_path)
    response_rows = [] if llm_response_trace_path is None else _load_materialized_response_rows(llm_response_trace_path)
    elapsed_values = []
    for row in response_rows:
        if not isinstance(row, Mapping):
            continue
        if row.get("latency_ms") is not None:
            elapsed_values.append(float(row.get("latency_ms", 0.0)) / 1000.0)
            continue
        if row.get("elapsed_seconds") is not None:
            elapsed_values.append(float(row.get("elapsed_seconds", 0.0)))
    expand_budget_status_counts: Counter[str] = Counter()
    expand_budget_throttled_operator_counts: Counter[str] = Counter()
    expand_budget_throttled_route_family_counts: Counter[str] = Counter()
    route_family_mode_counts: Counter[str] = Counter()
    semantic_trial_mode_counts: Counter[str] = Counter()
    visible_route_family_counts: Counter[str] = Counter()
    filtered_route_family_counts: Counter[str] = Counter()
    expand_request_count = 0
    for row in request_rows:
        direct_route_family_mode = str(row.get("route_family_mode", "")).strip()
        direct_semantic_trial_mode = str(row.get("semantic_trial_mode", "")).strip()
        if direct_route_family_mode:
            route_family_mode_counts[direct_route_family_mode] += 1
        if direct_semantic_trial_mode:
            semantic_trial_mode_counts[direct_semantic_trial_mode] += 1
        for route_family in row.get("visible_route_families", []):
            normalized_route_family = str(route_family).strip()
            if normalized_route_family:
                visible_route_family_counts[normalized_route_family] += 1
        for route_family in row.get("filtered_route_families", []):
            normalized_route_family = str(route_family).strip()
            if normalized_route_family:
                filtered_route_family_counts[normalized_route_family] += 1
        metadata = _request_prompt_metadata(row)
        if not metadata:
            continue
        decision_axes = metadata.get("decision_axes", {})
        if isinstance(decision_axes, Mapping):
            route_family_mode = str(decision_axes.get("route_family_mode", "")).strip()
            semantic_trial_mode = str(decision_axes.get("semantic_trial_mode", "")).strip()
            if route_family_mode and not direct_route_family_mode:
                route_family_mode_counts[route_family_mode] += 1
            if semantic_trial_mode and not direct_semantic_trial_mode:
                semantic_trial_mode_counts[semantic_trial_mode] += 1
        prompt_panels = metadata.get("prompt_panels", {})
        if not isinstance(prompt_panels, Mapping):
            continue
        regime_panel = prompt_panels.get("regime_panel", {})
        if not isinstance(regime_panel, Mapping):
            regime_panel = {}
        phase = str(row.get("policy_phase") or regime_panel.get("phase", "")).strip()
        if not phase.startswith("post_feasible_expand"):
            continue
        operator_panel = prompt_panels.get("operator_panel", {})
        if not isinstance(operator_panel, Mapping):
            continue
        expand_request_count += 1
        for operator_id, operator_row in operator_panel.items():
            if not isinstance(operator_row, Mapping):
                continue
            budget_status = str(operator_row.get("expand_budget_status", "")).strip()
            if not budget_status:
                continue
            expand_budget_status_counts[budget_status] += 1
            if budget_status == "throttled":
                normalized_operator_id = str(operator_id)
                expand_budget_throttled_operator_counts[normalized_operator_id] += 1
                expand_budget_throttled_route_family_counts[operator_route_family(normalized_operator_id)] += 1
    return {
        "request_count": len(request_rows),
        "response_count": len(response_rows),
        "fallback_count": sum(
            1 for row in response_rows if isinstance(row, Mapping) and bool(row.get("fallback_used", False))
        ),
        "expand_request_count": int(expand_request_count),
        "expand_budget_status_counts": dict(expand_budget_status_counts),
        "expand_budget_throttled_operator_counts": dict(expand_budget_throttled_operator_counts),
        "expand_budget_throttled_route_family_counts": dict(expand_budget_throttled_route_family_counts),
        "route_family_mode_counts": dict(route_family_mode_counts),
        "semantic_trial_mode_counts": dict(semantic_trial_mode_counts),
        "visible_route_family_counts": dict(visible_route_family_counts),
        "filtered_route_family_counts": dict(filtered_route_family_counts),
        "elapsed_seconds_avg": (
            0.0 if not elapsed_values else sum(elapsed_values) / float(len(elapsed_values))
        ),
        "request_trace_path": None if llm_request_trace_path is None else str(Path(llm_request_trace_path)),
        "response_trace_path": None if llm_response_trace_path is None else str(Path(llm_response_trace_path)),
    }


def _request_prompt_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    user_prompt = row.get("user_prompt")
    if not isinstance(user_prompt, str) or not user_prompt.strip():
        return {}
    try:
        payload = json.loads(user_prompt)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, Mapping):
        return {}
    metadata = payload.get("metadata", {})
    return dict(metadata) if isinstance(metadata, Mapping) else {}


def _load_controller_trace_rows(path: str | Path) -> list[ControllerTraceRow]:
    rows: list[ControllerTraceRow] = []
    for raw_row in _load_jsonl_rows(path):
        payload = dict(raw_row)
        metadata = dict(payload.get("metadata", {}))
        for key in (
            "fallback_used",
            "policy_phase",
            "guardrail_policy_phase",
            "guardrail_reason_codes",
            "guardrail_policy_reset_active",
            "guardrail_filtered_operator_ids",
        ):
            if key in payload and key not in metadata:
                metadata[key] = payload[key]
        generation_index, evaluation_index = _controller_trace_indices(payload)
        rows.append(
            ControllerTraceRow(
                generation_index=generation_index,
                evaluation_index=evaluation_index,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=tuple(
                    str(value)
                    for value in payload.get("candidate_operator_ids", payload.get("operator_pool_snapshot", []))
                ),
                selected_operator_id=str(
                    payload.get("selected_operator_id") or payload.get("operator_selected") or ""
                ),
                phase=str(payload.get("phase", "")),
                rationale=str(payload.get("rationale", "")),
                metadata=metadata,
            )
        )
    return rows


def _controller_trace_indices(payload: Mapping[str, Any]) -> tuple[int, int]:
    generation_index = payload.get("generation_index")
    evaluation_index = payload.get("evaluation_index")
    if generation_index is not None and evaluation_index is not None:
        return int(generation_index), int(evaluation_index)

    decision_id = str(payload.get("decision_id", "")).strip()
    match = re.search(r"g(?P<generation>\d+)-e(?P<evaluation>\d+)", decision_id)
    if match:
        return int(match.group("generation")), int(match.group("evaluation"))

    return (
        0 if generation_index is None else int(generation_index),
        0 if evaluation_index is None else int(evaluation_index),
    )


def _load_materialized_request_rows(path: str | Path) -> list[dict[str, Any]]:
    trace_path = Path(path)
    return materialize_request_trace_rows(_trace_bundle_root(trace_path), _load_jsonl_rows(trace_path))


def _load_materialized_response_rows(path: str | Path) -> list[dict[str, Any]]:
    trace_path = Path(path)
    return materialize_response_trace_rows(_trace_bundle_root(trace_path), _load_jsonl_rows(trace_path))


def _trace_bundle_root(trace_path: Path) -> Path:
    return trace_path.parent.parent if trace_path.parent.name == "traces" else trace_path.parent


def _load_jsonl_rows(path: str | Path) -> list[dict[str, Any]]:
    return [dict(row) for row in load_jsonl_rows(Path(path))]
