"""Experiment-level compact summaries for LLM-guided union runs."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.operator_pool.route_families import route_family_counts, route_family_entropy
from optimizers.operator_pool.semantic_tasks import semantic_task_counts, semantic_task_entropy
from optimizers.llm_ranker_diagnostics import build_ranker_trace_diagnostics
from optimizers.run_telemetry import load_jsonl_rows
from optimizers.traces.llm_trace_io import (
    iter_mode_seed_roots,
    materialize_request_trace_rows,
    materialize_response_trace_rows,
    resolve_seed_trace_path,
)


def build_mode_llm_summaries(mode_root: str | Path) -> dict[str, str]:
    root = Path(mode_root)
    summaries_root = root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    request_rows: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    controller_rows: list[dict[str, Any]] = []

    for seed_root in iter_mode_seed_roots(root):
        request_trace_path = resolve_seed_trace_path(seed_root, "llm_request_trace.jsonl")
        if request_trace_path.exists():
            request_rows.extend(
                materialize_request_trace_rows(seed_root, load_jsonl_rows(request_trace_path))
            )
        response_trace_path = resolve_seed_trace_path(seed_root, "llm_response_trace.jsonl")
        if response_trace_path.exists():
            response_rows.extend(
                materialize_response_trace_rows(seed_root, load_jsonl_rows(response_trace_path))
            )
        controller_rows.extend(_load_controller_rows(seed_root))

    payloads = {
        "llm_runtime_summary": build_llm_runtime_summary(
            request_rows=request_rows,
            response_rows=response_rows,
            controller_rows=controller_rows,
        ),
        "llm_prompt_summary": build_llm_prompt_summary(request_rows=request_rows),
        "llm_decision_summary": build_llm_decision_summary(
            controller_rows=controller_rows,
            response_rows=response_rows,
        ),
    }
    written: dict[str, str] = {}
    for summary_name, payload in payloads.items():
        output_path = summaries_root / f"{summary_name}.json"
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written[summary_name] = str(output_path.relative_to(root).as_posix())
    return written

def build_llm_runtime_summary(
    *,
    request_rows: Sequence[Mapping[str, Any]],
    response_rows: Sequence[Mapping[str, Any]],
    controller_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    providers = _sorted_unique(
        list(_values(request_rows, "provider"))
        + list(_values(response_rows, "provider"))
    )
    models = _sorted_unique(
        list(_values(request_rows, "model"))
        + list(_values(response_rows, "model"))
    )
    capability_profiles = _sorted_unique(
        list(_values(request_rows, "capability_profile"))
        + list(_values(response_rows, "capability_profile"))
    )
    performance_profiles = _sorted_unique(
        list(_values(request_rows, "performance_profile"))
        + list(_values(response_rows, "performance_profile"))
    )
    elapsed_values = [
        float(row.get("latency_ms", 0.0)) / 1000.0
        for row in response_rows
        if row.get("latency_ms") is not None
    ]
    request_count = int(len(request_rows))
    elapsed_total = float(sum(elapsed_values))
    fallback_count = sum(
        1
        for row in controller_rows
        if bool(
            row.get("fallback_used", False)
            or dict(row.get("metadata", {})).get("fallback_used", False)
        )
    )
    return {
        "provider": providers[0] if len(providers) == 1 else providers,
        "model": models[0] if len(models) == 1 else models,
        "capability_profile": capability_profiles[0] if len(capability_profiles) == 1 else capability_profiles,
        "performance_profile": performance_profiles[0] if len(performance_profiles) == 1 else performance_profiles,
        "request_count": request_count,
        "response_count": int(len(response_rows)),
        "fallback_count": int(fallback_count),
        "retry_count": int(sum(int(row.get("retries", 0)) for row in response_rows)),
        "elapsed_seconds_total": elapsed_total,
        "elapsed_seconds_avg": float(elapsed_total / float(max(1, request_count))),
        "elapsed_seconds_max": float(
            max(elapsed_values + [0.0])
        ),
    }


def build_llm_decision_summary(
    *,
    controller_rows: Sequence[Mapping[str, Any]],
    response_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_controller_rows = [
        {
            **dict(row),
            "selected_operator_id": str(
                row.get("selected_operator_id") or row.get("operator_selected") or ""
            ),
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
        if bool(
            row.get("fallback_used", False)
            or dict(row.get("metadata", {})).get("fallback_used", False)
        )
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
    all_semantic_task_counts = semantic_task_counts(normalized_controller_rows)
    expand_semantic_counts = semantic_task_counts(normalized_controller_rows, phase="post_feasible_expand")
    ranker_diagnostics = build_ranker_trace_diagnostics(response_rows)
    semantic_task_by_phase: dict[str, dict[str, int]] = {}
    for row in normalized_controller_rows:
        phase = str(row.get("policy_phase") or row.get("phase", "")).strip()
        if not phase:
            continue
        task_counts = semantic_task_counts([row])
        if task_counts:
            semantic_task_by_phase.setdefault(phase, Counter()).update(task_counts)
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
        "semantic_task_counts": all_semantic_task_counts,
        "semantic_task_entropy": semantic_task_entropy(all_semantic_task_counts),
        "expand_semantic_task_counts": expand_semantic_counts,
        "expand_semantic_task_entropy": semantic_task_entropy(expand_semantic_counts),
        "semantic_task_by_phase": {phase: dict(counts) for phase, counts in semantic_task_by_phase.items()},
        "ranker_diagnostics": ranker_diagnostics,
    }


def build_llm_prompt_summary(
    *,
    request_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_sizes: list[int] = []
    policy_phase_counts: Counter[str] = Counter()
    dominant_counts = Counter(
        str(dict(row.get("guardrail", {})).get("dominant_operator_id", ""))
        for row in request_rows
        if row.get("guardrail")
    )
    for row in request_rows:
        candidate_operator_ids = row.get("candidate_operator_ids")
        if isinstance(candidate_operator_ids, Sequence) and not isinstance(candidate_operator_ids, (str, bytes)):
            candidate_sizes.append(len(list(candidate_operator_ids)))
        elif row.get("effective_candidate_pool_size") is not None:
            candidate_sizes.append(int(row.get("effective_candidate_pool_size", 0)))
        else:
            metadata = _request_prompt_metadata(row)
            guardrail = metadata.get("decision_guardrail", {}) if isinstance(metadata, Mapping) else {}
            if isinstance(guardrail, Mapping):
                effective_ids = guardrail.get("effective_candidate_operator_ids", [])
                if isinstance(effective_ids, Sequence) and not isinstance(effective_ids, (str, bytes)):
                    candidate_sizes.append(len(list(effective_ids)))

        policy_phase = str(row.get("policy_phase", "")).strip()
        if not policy_phase:
            metadata = _request_prompt_metadata(row)
            prompt_panels = metadata.get("prompt_panels", {}) if isinstance(metadata, Mapping) else {}
            if isinstance(prompt_panels, Mapping):
                regime_panel = prompt_panels.get("regime_panel", {})
                if isinstance(regime_panel, Mapping):
                    policy_phase = str(regime_panel.get("phase", "")).strip()
        if policy_phase:
            policy_phase_counts[policy_phase] += 1
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


def build_seed_llm_runtime_summary(
    seed_root: str | Path,
    *,
    scenario_id: str,
    method_id: str,
    mode: str,
    llm_profile: str,
    run_wall_seconds: float,
    optimizer_wall_seconds: float,
) -> dict[str, Any]:
    root = Path(seed_root)
    seed = _seed_from_root(root)
    request_rows = load_jsonl_rows(root / "traces" / "llm_request_trace.jsonl")
    response_rows = load_jsonl_rows(root / "traces" / "llm_response_trace.jsonl")
    controller_rows = _load_controller_rows(root)
    latencies = [
        float(row["latency_ms"]) / 1000.0
        for row in response_rows
        if row.get("latency_ms") is not None
    ]
    prompt_total = sum(_usage_int(row, "prompt_tokens") for row in response_rows)
    completion_total = sum(_usage_int(row, "completion_tokens") for row in response_rows)
    total_total = sum(_usage_int(row, "total_tokens") for row in response_rows)
    return {
        "scenario_id": scenario_id,
        "method_id": method_id,
        "mode": mode,
        "llm_profile": llm_profile,
        "seed": seed,
        "provider": _single_or_list(
            _sorted_unique(list(_values(request_rows, "provider")) + list(_values(response_rows, "provider")))
        ),
        "model": _single_or_list(
            _sorted_unique(list(_values(request_rows, "model")) + list(_values(response_rows, "model")))
        ),
        "remote_endpoint_label": _remote_endpoint_label(llm_profile),
        "run_wall_seconds": float(run_wall_seconds),
        "optimizer_wall_seconds": float(optimizer_wall_seconds),
        "llm_request_count": len(request_rows),
        "llm_response_count": len(response_rows),
        "llm_retry_count": int(sum(int(row.get("retries", 0)) for row in response_rows)),
        "llm_fallback_count": int(
            sum(1 for row in controller_rows if row.get("fallback_used") or dict(row.get("metadata", {})).get("fallback_used"))
        ),
        "llm_latency_seconds_total": float(sum(latencies)),
        "llm_latency_seconds_mean": _mean(latencies),
        "llm_latency_seconds_median": _percentile(latencies, 50),
        "llm_latency_seconds_p95": _percentile(latencies, 95),
        "llm_latency_seconds_max": max(latencies) if latencies else 0.0,
        "tokens_prompt_total": int(prompt_total),
        "tokens_completion_total": int(completion_total),
        "tokens_total": int(total_total),
        "tokens_total_per_request_mean": float(total_total / max(1, len(response_rows))),
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


def _load_controller_rows(seed_root: Path) -> list[dict[str, Any]]:
    trace_path = resolve_seed_trace_path(seed_root, "controller_trace.jsonl")
    if trace_path.exists():
        return [dict(row) for row in load_jsonl_rows(trace_path)]
    return []


def _usage_int(row: Mapping[str, Any], key: str) -> int:
    usage = row.get("usage")
    if isinstance(usage, Mapping) and usage.get(key) is not None:
        return int(usage[key])
    if row.get(key) is not None:
        return int(row[key])
    return 0


def _seed_from_root(root: Path) -> int:
    name = root.name
    if name.startswith("seed-"):
        return int(name.split("-", 1)[1])
    return 0


def _mean(values: Sequence[float]) -> float:
    return 0.0 if not values else float(sum(values) / len(values))


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * float(percentile) / 100.0
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = rank - lower_index
    return float(round(ordered[lower_index] * (1.0 - fraction) + ordered[upper_index] * fraction, 12))


def _single_or_list(values: Sequence[str]) -> str | list[str]:
    return values[0] if len(values) == 1 else list(values)


def _remote_endpoint_label(llm_profile: str) -> str:
    labels = {
        "default": "DEEPSEEK_PROXY_BASE_URL",
        "gpt": "GPT_PROXY_BASE_URL",
        "qwen3_6_plus": "QWEN_PROXY_BASE_URL",
        "glm_5": "QWEN_PROXY_BASE_URL",
        "minimax_m2_5": "QWEN_PROXY_BASE_URL",
        "deepseek_v4_flash": "DEEPSEEK_PROXY_BASE_URL",
        "mimo_v2_5": "MIMO_BASE_URL",
    }
    return labels.get(str(llm_profile), f"{llm_profile}_profile")
