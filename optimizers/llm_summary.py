"""Experiment-level compact summaries for LLM-guided union runs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


def build_llm_runtime_summary(
    *,
    metrics_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    response_rows: Sequence[Mapping[str, Any]],
    reflection_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    reflection_rows = [] if reflection_rows is None else list(reflection_rows)
    providers = _sorted_unique(
        list(_values(metrics_rows, "provider"))
        + list(_values(request_rows, "provider"))
        + list(_values(response_rows, "provider"))
    )
    models = _sorted_unique(
        list(_values(metrics_rows, "model"))
        + list(_values(request_rows, "model"))
        + list(_values(response_rows, "model"))
    )
    capability_profiles = _sorted_unique(
        list(_values(metrics_rows, "capability_profile"))
        + list(_values(request_rows, "capability_profile"))
        + list(_values(response_rows, "capability_profile"))
    )
    performance_profiles = _sorted_unique(
        list(_values(metrics_rows, "performance_profile"))
        + list(_values(request_rows, "performance_profile"))
        + list(_values(response_rows, "performance_profile"))
    )
    elapsed_values = [
        float(row.get("elapsed_seconds", 0.0))
        for row in response_rows
        if row.get("elapsed_seconds") is not None
    ]
    request_count = int(sum(int(row.get("request_count", 0)) for row in metrics_rows) or len(request_rows))
    elapsed_total = float(
        sum(float(row.get("elapsed_seconds_total", 0.0)) for row in metrics_rows)
        or sum(elapsed_values)
    )
    return {
        "provider": providers[0] if len(providers) == 1 else providers,
        "model": models[0] if len(models) == 1 else models,
        "capability_profile": capability_profiles[0] if len(capability_profiles) == 1 else capability_profiles,
        "performance_profile": performance_profiles[0] if len(performance_profiles) == 1 else performance_profiles,
        "request_count": request_count,
        "response_count": int(sum(int(row.get("response_count", 0)) for row in metrics_rows) or len(response_rows)),
        "fallback_count": int(sum(int(row.get("fallback_count", 0)) for row in metrics_rows)),
        "retry_count": int(sum(int(row.get("retry_count", 0)) for row in metrics_rows)),
        "invalid_response_count": int(sum(int(row.get("invalid_response_count", 0)) for row in metrics_rows)),
        "schema_invalid_count": int(sum(int(row.get("schema_invalid_count", 0)) for row in metrics_rows)),
        "semantic_invalid_count": int(sum(int(row.get("semantic_invalid_count", 0)) for row in metrics_rows)),
        "elapsed_seconds_total": elapsed_total,
        "elapsed_seconds_avg": float(elapsed_total / float(max(1, request_count))),
        "elapsed_seconds_max": float(
            max(
                [float(row.get("elapsed_seconds_max", 0.0)) for row in metrics_rows]
                + elapsed_values
                + [0.0]
            )
        ),
        "reflection_trace_present": bool(reflection_rows),
        "reflection_row_count": int(len(reflection_rows)),
    }


def build_llm_decision_summary(
    *,
    controller_rows: Sequence[Mapping[str, Any]],
    response_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    operator_counts = Counter(
        str(row.get("selected_operator_id", ""))
        for row in controller_rows
        if row.get("selected_operator_id")
    )
    phase_counts = Counter(
        str(row.get("phase", ""))
        for row in controller_rows
        if row.get("phase")
    )
    fallback_count = sum(
        1
        for row in controller_rows
        if bool(dict(row.get("metadata", {})).get("fallback_used", False))
    )
    guardrail_reason_counts: Counter[str] = Counter()
    for row in controller_rows:
        metadata = dict(row.get("metadata", {}))
        raw_values = metadata.get("guardrail_reason_codes", [])
        if isinstance(raw_values, Sequence) and not isinstance(raw_values, (str, bytes)):
            for value in raw_values:
                guardrail_reason_counts[str(value)] += 1
        elif raw_values:
            guardrail_reason_counts[str(raw_values)] += 1
    return {
        "decision_count": int(len(controller_rows)),
        "response_row_count": int(len(response_rows)),
        "fallback_selection_count": int(fallback_count),
        "llm_valid_selection_count": int(len(controller_rows) - fallback_count),
        "operator_counts": dict(operator_counts),
        "phase_counts": dict(phase_counts),
        "guardrail_reason_counts": dict(guardrail_reason_counts),
    }


def build_llm_prompt_summary(
    *,
    request_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_sizes = [len(list(row.get("candidate_operator_ids", []))) for row in request_rows]
    policy_phase_counts = Counter(
        str(row.get("policy_phase", ""))
        for row in request_rows
        if row.get("policy_phase")
    )
    dominant_counts = Counter(
        str(dict(row.get("guardrail", {})).get("dominant_operator_id", ""))
        for row in request_rows
        if row.get("guardrail")
    )
    return {
        "request_count": int(len(request_rows)),
        "avg_candidate_operator_count": (
            0.0 if not candidate_sizes else float(sum(candidate_sizes) / float(len(candidate_sizes)))
        ),
        "mean_system_prompt_length": (
            0.0
            if not request_rows
            else float(sum(len(str(row.get("system_prompt", ""))) for row in request_rows) / float(len(request_rows)))
        ),
        "mean_user_prompt_length": (
            0.0
            if not request_rows
            else float(sum(len(str(row.get("user_prompt", ""))) for row in request_rows) / float(len(request_rows)))
        ),
        "policy_phase_counts": dict(policy_phase_counts),
        "guardrail_dominance_counts": {
            key: value
            for key, value in dominant_counts.items()
            if key
        },
    }


def build_llm_reflection_summary(*, reflection_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "row_count": int(len(reflection_rows)),
        "latest_generation_index": (
            None
            if not reflection_rows
            else int(max(int(row.get("generation_index", 0)) for row in reflection_rows))
        ),
    }


def _values(rows: Sequence[Mapping[str, Any]], key: str) -> list[str]:
    values = []
    for row in rows:
        value = row.get(key)
        if value is not None and str(value).strip():
            values.append(str(value))
    return values


def _sorted_unique(values: Sequence[str]) -> list[str]:
    return sorted(dict.fromkeys(str(value) for value in values if str(value).strip()))
