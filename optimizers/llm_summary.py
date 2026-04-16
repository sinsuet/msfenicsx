"""Experiment-level compact summaries for LLM-guided union runs."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.operator_pool.route_families import route_family_counts, route_family_entropy
from optimizers.run_telemetry import load_jsonl_rows


def build_mode_llm_summaries(mode_root: str | Path) -> dict[str, str]:
    root = Path(mode_root)
    summaries_root = root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    metrics_rows: list[dict[str, Any]] = []
    request_rows: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    reflection_rows: list[dict[str, Any]] = []
    controller_rows: list[dict[str, Any]] = []

    for seed_root in _iter_seed_roots(root):
        if (seed_root / "llm_metrics.json").exists():
            metrics_rows.append(_load_json(seed_root / "llm_metrics.json"))
        if (seed_root / "llm_request_trace.jsonl").exists():
            request_rows.extend(load_jsonl_rows(seed_root / "llm_request_trace.jsonl"))
        if (seed_root / "llm_response_trace.jsonl").exists():
            response_rows.extend(load_jsonl_rows(seed_root / "llm_response_trace.jsonl"))
        if (seed_root / "llm_reflection_trace.jsonl").exists():
            reflection_rows.extend(load_jsonl_rows(seed_root / "llm_reflection_trace.jsonl"))
        if (seed_root / "controller_trace.json").exists():
            controller_rows.extend(_load_json(seed_root / "controller_trace.json"))

    payloads = {
        "llm_runtime_summary": build_llm_runtime_summary(
            metrics_rows=metrics_rows,
            request_rows=request_rows,
            response_rows=response_rows,
            reflection_rows=reflection_rows,
        ),
        "llm_prompt_summary": build_llm_prompt_summary(request_rows=request_rows),
        "llm_decision_summary": build_llm_decision_summary(
            controller_rows=controller_rows,
            response_rows=response_rows,
        ),
        "llm_reflection_summary": build_llm_reflection_summary(reflection_rows=reflection_rows),
    }
    written: dict[str, str] = {}
    for summary_name, payload in payloads.items():
        output_path = summaries_root / f"{summary_name}.json"
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written[summary_name] = str(output_path.relative_to(root).as_posix())
    return written

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
    normalized_controller_rows = [
        {
            **dict(row),
            "policy_phase": str(
                dict(row.get("metadata", {})).get("policy_phase")
                or dict(row.get("metadata", {})).get("guardrail_policy_phase")
                or row.get("phase", "")
            ),
        }
        for row in controller_rows
    ]
    operator_counts = Counter(
        str(row.get("selected_operator_id", ""))
        for row in normalized_controller_rows
        if row.get("selected_operator_id")
    )
    phase_counts = Counter(
        str(row.get("phase", ""))
        for row in normalized_controller_rows
        if row.get("phase")
    )
    fallback_count = sum(
        1
        for row in normalized_controller_rows
        if bool(dict(row.get("metadata", {})).get("fallback_used", False))
    )
    guardrail_reason_counts: Counter[str] = Counter()
    for row in normalized_controller_rows:
        metadata = dict(row.get("metadata", {}))
        raw_values = metadata.get("guardrail_reason_codes", [])
        if isinstance(raw_values, Sequence) and not isinstance(raw_values, (str, bytes)):
            for value in raw_values:
                guardrail_reason_counts[str(value)] += 1
        elif raw_values:
            guardrail_reason_counts[str(raw_values)] += 1
    all_route_family_counts = route_family_counts(normalized_controller_rows)
    expand_route_counts = route_family_counts(normalized_controller_rows, phase="post_feasible_expand")
    return {
        "decision_count": int(len(normalized_controller_rows)),
        "response_row_count": int(len(response_rows)),
        "fallback_selection_count": int(fallback_count),
        "llm_valid_selection_count": int(len(normalized_controller_rows) - fallback_count),
        "operator_counts": dict(operator_counts),
        "phase_counts": dict(phase_counts),
        "guardrail_reason_counts": dict(guardrail_reason_counts),
        "route_family_counts": all_route_family_counts,
        "route_family_entropy": route_family_entropy(all_route_family_counts),
        "expand_route_family_counts": expand_route_counts,
        "expand_route_family_entropy": route_family_entropy(expand_route_counts),
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


def _iter_seed_roots(mode_root: Path) -> list[Path]:
    seeds_root = mode_root / "seeds"
    if not seeds_root.exists():
        return []
    return sorted(
        [path for path in seeds_root.iterdir() if path.is_dir() and path.name.startswith("seed-")],
        key=lambda path: int(path.name.removeprefix("seed-")),
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
