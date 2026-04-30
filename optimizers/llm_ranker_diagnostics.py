"""Diagnostics for semantic ranked-pick LLM response traces."""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


def build_ranker_trace_diagnostics(response_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ranked_rows = [dict(row) for row in response_rows if _is_ranked_pick_response(row)]
    selected_rank_counts: Counter[str] = Counter()
    override_reason_counts: Counter[str] = Counter()
    cap_reason_counts: Counter[str] = Counter()
    invalid_response_count = 0
    invalid_attempt_count = 0
    invalid_field_count = 0

    for row in ranked_rows:
        selected_rank = row.get("selected_rank")
        if selected_rank is not None:
            selected_rank_counts[str(int(selected_rank))] += 1
        override_reason = str(row.get("ranker_override_reason", "")).strip()
        if override_reason:
            override_reason_counts[override_reason] += 1
        cap_reasons = row.get("ranker_cap_reasons", {})
        if isinstance(cap_reasons, Mapping):
            for reason in cap_reasons.values():
                normalized_reason = str(reason).strip()
                if normalized_reason:
                    cap_reason_counts[normalized_reason] += 1

        row_invalid_attempts = 0
        row_invalid_fields = 0
        attempt_trace = row.get("attempt_trace", [])
        if isinstance(attempt_trace, Sequence) and not isinstance(attempt_trace, (str, bytes)):
            for attempt in attempt_trace:
                if not isinstance(attempt, Mapping):
                    continue
                attempt_invalid_fields = _invalid_rank_field_count_from_attempt(attempt)
                if attempt_invalid_fields > 0 or _attempt_error_is_rank_contract_violation(attempt):
                    row_invalid_attempts += 1
                row_invalid_fields += attempt_invalid_fields
        if row_invalid_attempts > 0:
            invalid_response_count += 1
            invalid_attempt_count += row_invalid_attempts
            invalid_field_count += row_invalid_fields

    return {
        "ranked_response_count": int(len(ranked_rows)),
        "selected_rank_counts": dict(sorted(selected_rank_counts.items(), key=lambda item: int(item[0]))),
        "override_reason_counts": dict(override_reason_counts),
        "cap_reason_counts": dict(cap_reason_counts),
        "contract_invalid_response_count": int(invalid_response_count),
        "contract_invalid_attempt_count": int(invalid_attempt_count),
        "contract_invalid_field_count": int(invalid_field_count),
    }


def _is_ranked_pick_response(row: Mapping[str, Any]) -> bool:
    return (
        str(row.get("selection_strategy", "")).strip() == "semantic_ranked_pick"
        or row.get("selected_rank") is not None
        or isinstance(row.get("llm_ranked_operators"), Sequence)
        or isinstance(row.get("ranker_ranked_operator_rows"), Sequence)
    )


def _invalid_rank_field_count_from_attempt(attempt: Mapping[str, Any]) -> int:
    raw_text = attempt.get("raw_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        return 0
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, Mapping):
        return 0
    ranked = payload.get("ranked_operators")
    if not isinstance(ranked, Sequence) or isinstance(ranked, (str, bytes)):
        return 0
    invalid_count = 0
    for entry in ranked:
        if not isinstance(entry, Mapping):
            continue
        for field_name in ("score", "risk", "confidence"):
            if _rank_numeric_field_is_invalid(entry.get(field_name)):
                invalid_count += 1
    return invalid_count


def _rank_numeric_field_is_invalid(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return True
    numeric = float(value)
    return not math.isfinite(numeric) or numeric < 0.0 or numeric > 1.0


def _attempt_error_is_rank_contract_violation(attempt: Mapping[str, Any]) -> bool:
    error = str(attempt.get("error", "")).lower()
    if not error:
        return False
    return (
        "ranked_operators entry" in error
        and ("0.0" in error or "1.0" in error or "json number" in error)
    )
