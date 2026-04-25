"""Reproducible audit helpers for staged benchmark/controller analysis."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.operator_pool.route_families import operator_route_family


def compare_history_prefix_by_mode(
    mode_roots: Mapping[str, str | Path],
    *,
    prefix_rows: int = 21,
) -> dict[str, Any]:
    histories_by_mode = {
        str(mode): _load_history(Path(root) / "optimization_result.json")
        for mode, root in mode_roots.items()
    }
    shared_prefix_rows: list[dict[str, Any]] = []
    first_divergence_history_row: int | None = None

    for history_row in range(1, prefix_rows + 1):
        by_mode: dict[str, dict[str, Any] | None] = {}
        fingerprints: dict[str, str | None] = {}
        for mode, history in histories_by_mode.items():
            payload = None if history_row > len(history) else _normalize_history_row(history[history_row - 1])
            by_mode[mode] = payload
            fingerprints[mode] = None if payload is None else json.dumps(payload, ensure_ascii=True, sort_keys=True)
        unique_fingerprints = {value for value in fingerprints.values()}
        matches_all_modes = len(unique_fingerprints) == 1
        if not matches_all_modes and first_divergence_history_row is None:
            first_divergence_history_row = history_row
        shared_prefix_rows.append(
            {
                "history_row": history_row,
                "matches_all_modes": matches_all_modes,
                "by_mode": by_mode,
            }
        )

    return {
        "shared_prefix_identical": first_divergence_history_row is None,
        "first_divergence_history_row": first_divergence_history_row,
        "shared_prefix_rows": shared_prefix_rows,
        "first_feasible_eval_by_mode": {
            mode: _first_feasible_eval(history)
            for mode, history in histories_by_mode.items()
        },
    }


def summarize_unique_llm_decisions(controller_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    ordered_unique_rows: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for row in controller_rows:
        decision_id = _decision_id_from_row(row)
        if decision_id in seen:
            continue
        seen.add(decision_id)
        ordered_unique_rows.append(row)

    policy_phase_counts: Counter[str] = Counter(_policy_phase_from_row(row) for row in ordered_unique_rows)
    first_decision_id = None if not ordered_unique_rows else _decision_id_from_row(ordered_unique_rows[0])
    last_decision_id = None if not ordered_unique_rows else _decision_id_from_row(ordered_unique_rows[-1])
    return {
        "raw_row_count": len(controller_rows),
        "unique_decision_count": len(ordered_unique_rows),
        "duplicate_row_count": max(0, len(controller_rows) - len(ordered_unique_rows)),
        "policy_phase_counts": dict(policy_phase_counts),
        "first_decision_id": first_decision_id,
        "last_decision_id": last_decision_id,
    }


def summarize_llm_prompt_surface(
    request_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    route_family_mode_counts: Counter[str] = Counter()
    semantic_trial_mode_counts: Counter[str] = Counter()
    visible_route_family_counts: Counter[str] = Counter()
    filtered_route_family_counts: Counter[str] = Counter()
    effective_pool_sizes: list[int] = []
    original_pool_sizes: list[int] = []
    gradient_request_count = 0
    gradient_with_congestion_relief_visible_count = 0

    resolved_run_root = None if run_root is None else Path(run_root)
    for row in request_rows:
        direct_route_family_mode = str(row.get("route_family_mode", "")).strip()
        direct_semantic_trial_mode = str(row.get("semantic_trial_mode", "")).strip()
        direct_visible_route_families = {
            str(route_family).strip()
            for route_family in row.get("visible_route_families", [])
            if str(route_family).strip()
        }
        direct_filtered_route_families = {
            str(route_family).strip()
            for route_family in row.get("filtered_route_families", [])
            if str(route_family).strip()
        }
        direct_original_pool_size = row.get("original_candidate_pool_size")
        direct_effective_pool_size = row.get("effective_candidate_pool_size")
        direct_preferred_effect = str(row.get("preferred_effect", "")).strip()
        metadata = _request_metadata_from_row(row, run_root=resolved_run_root)
        if not metadata:
            metadata = {}
        decision_axes = metadata.get("decision_axes", {})
        if not isinstance(decision_axes, Mapping):
            decision_axes = {}
        route_family_mode = direct_route_family_mode or str(decision_axes.get("route_family_mode", "")).strip() or "none"
        semantic_trial_mode = (
            direct_semantic_trial_mode or str(decision_axes.get("semantic_trial_mode", "")).strip() or "none"
        )
        route_family_mode_counts[route_family_mode] += 1
        semantic_trial_mode_counts[semantic_trial_mode] += 1

        guardrail = metadata.get("decision_guardrail", {})
        if not isinstance(guardrail, Mapping):
            guardrail = {}
        original_ids = _operator_id_list(
            guardrail.get("original_candidate_operator_ids", metadata.get("original_candidate_operator_ids", []))
        )
        filtered_ids = _operator_id_list(guardrail.get("filtered_operator_ids", []))
        effective_ids = _operator_id_list(guardrail.get("effective_candidate_operator_ids", []))
        if not effective_ids:
            effective_ids = [operator_id for operator_id in original_ids if operator_id not in set(filtered_ids)]
        original_pool_sizes.append(
            int(direct_original_pool_size) if direct_original_pool_size is not None else len(original_ids)
        )
        effective_pool_sizes.append(
            int(direct_effective_pool_size) if direct_effective_pool_size is not None else len(effective_ids)
        )

        visible_route_families = direct_visible_route_families or {
            operator_route_family(operator_id) for operator_id in effective_ids
        }
        filtered_route_families = direct_filtered_route_families or {
            operator_route_family(operator_id) for operator_id in filtered_ids
        }
        for route_family in visible_route_families:
            visible_route_family_counts[route_family] += 1
        for route_family in filtered_route_families:
            filtered_route_family_counts[route_family] += 1

        regime_panel = metadata.get("prompt_panels", {})
        if not isinstance(regime_panel, Mapping):
            regime_panel = {}
        objective_balance = regime_panel.get("regime_panel", {})
        if not isinstance(objective_balance, Mapping):
            objective_balance = {}
        objective_balance = objective_balance.get("objective_balance", {})
        if not isinstance(objective_balance, Mapping):
            objective_balance = {}
        preferred_effect = direct_preferred_effect or str(objective_balance.get("preferred_effect", "")).strip()
        if preferred_effect == "gradient_improve":
            gradient_request_count += 1
            if "congestion_relief" in visible_route_families:
                gradient_with_congestion_relief_visible_count += 1

    return {
        "request_count": len(request_rows),
        "original_pool_size": _size_summary(original_pool_sizes),
        "effective_pool_size": _size_summary(effective_pool_sizes),
        "route_family_mode_counts": dict(route_family_mode_counts),
        "semantic_trial_mode_counts": dict(semantic_trial_mode_counts),
        "visible_route_family_counts": dict(visible_route_family_counts),
        "filtered_route_family_counts": dict(filtered_route_family_counts),
        "gradient_improve": {
            "request_count": gradient_request_count,
            "with_congestion_relief_visible_count": gradient_with_congestion_relief_visible_count,
            "with_congestion_relief_visible_share": (
                0.0
                if gradient_request_count <= 0
                else float(gradient_with_congestion_relief_visible_count) / float(gradient_request_count)
            ),
        },
    }


def summarize_prompt_contract_mismatches(
    request_rows: Sequence[Mapping[str, Any]],
    *,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    resolved_run_root = None if run_root is None else Path(run_root)
    phase_mismatch_count = 0
    phase_mismatch_examples: list[dict[str, Any]] = []
    phase_mismatch_example_phases: set[str] = set()
    hidden_positive_match_requests = 0
    hidden_positive_match_family_counts: Counter[str] = Counter()
    hidden_positive_credit_requests = 0
    hidden_positive_credit_family_counts: Counter[str] = Counter()
    recover_pool_sizes: list[int] = []

    for row in request_rows:
        metadata = _request_metadata_from_row(row, run_root=resolved_run_root)
        prompt_panels = metadata.get("prompt_panels", {})
        if not isinstance(prompt_panels, Mapping):
            prompt_panels = {}
        regime_panel = prompt_panels.get("regime_panel", {})
        if not isinstance(regime_panel, Mapping):
            regime_panel = {}
        retrieval_panel = prompt_panels.get("retrieval_panel", {})
        if not isinstance(retrieval_panel, Mapping):
            retrieval_panel = {}

        policy_phase = _policy_phase_from_request_row(row, regime_panel=regime_panel)
        retrieval_query = retrieval_panel.get("query_regime", {})
        if not isinstance(retrieval_query, Mapping):
            retrieval_query = {}
        retrieval_phase = str(retrieval_query.get("phase", "")).strip()
        phase_fallbacks = _string_list(retrieval_query.get("phase_fallbacks", []))

        if policy_phase == "post_feasible_recover":
            recover_pool_sizes.append(_effective_pool_size_from_request_row(row, metadata))

        if policy_phase and retrieval_phase and retrieval_phase != policy_phase:
            phase_mismatch_count += 1
            example = {
                "decision_id": _decision_id_from_row(row),
                "policy_phase": policy_phase,
                "regime_phase": str(regime_panel.get("phase", "")).strip(),
                "retrieval_phase": retrieval_phase,
                "phase_fallbacks": phase_fallbacks,
            }
            if policy_phase not in phase_mismatch_example_phases or len(phase_mismatch_examples) < 8:
                phase_mismatch_examples.append(example)
                phase_mismatch_example_phases.add(policy_phase)

        visible_route_families = _visible_route_families_from_request_row(row, metadata)
        positive_match_route_families = _positive_match_route_families_from_retrieval_panel(retrieval_panel)
        hidden_positive_match_route_families = sorted(positive_match_route_families - visible_route_families)
        if hidden_positive_match_route_families:
            hidden_positive_match_requests += 1
            for route_family in hidden_positive_match_route_families:
                hidden_positive_match_family_counts[route_family] += 1

        positive_credit_route_families = _positive_credit_route_families_from_retrieval_panel(retrieval_panel)
        hidden_positive_credit_route_families = sorted(positive_credit_route_families - visible_route_families)
        if hidden_positive_credit_route_families:
            hidden_positive_credit_requests += 1
            for route_family in hidden_positive_credit_route_families:
                hidden_positive_credit_family_counts[route_family] += 1

    return {
        "phase_mismatch_count": int(phase_mismatch_count),
        "phase_mismatch_examples": phase_mismatch_examples,
        "hidden_positive_match_requests": int(hidden_positive_match_requests),
        "hidden_positive_match_family_counts": dict(sorted(hidden_positive_match_family_counts.items())),
        "hidden_positive_credit_requests": int(hidden_positive_credit_requests),
        "hidden_positive_credit_family_counts": dict(sorted(hidden_positive_credit_family_counts.items())),
        "recover_pool_size_summary": _pool_size_summary(recover_pool_sizes),
    }


def summarize_prompt_chain_progress(
    request_rows: Sequence[Mapping[str, Any]],
    *,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    resolved_run_root = None if run_root is None else Path(run_root)
    phase_counts: Counter[str] = Counter()
    convert_route_family_mode_counts: Counter[str] = Counter()
    convert_semantic_trial_mode_counts: Counter[str] = Counter()
    hidden_positive_credit_family_counts: Counter[str] = Counter()
    recover_pool_sizes: list[int] = []

    for row in request_rows:
        metadata = _request_metadata_from_row(row, run_root=resolved_run_root)
        prompt_panels = metadata.get("prompt_panels", {})
        if not isinstance(prompt_panels, Mapping):
            prompt_panels = {}
        regime_panel = prompt_panels.get("regime_panel", {})
        if not isinstance(regime_panel, Mapping):
            regime_panel = {}
        retrieval_panel = prompt_panels.get("retrieval_panel", {})
        if not isinstance(retrieval_panel, Mapping):
            retrieval_panel = {}

        policy_phase = _policy_phase_from_request_row(row, regime_panel=regime_panel)
        phase_counts[policy_phase] += 1

        if policy_phase == "prefeasible_convert":
            convert_route_family_mode = str(row.get("route_family_mode", "")).strip() or "none"
            convert_semantic_trial_mode = str(row.get("semantic_trial_mode", "")).strip() or "none"
            convert_route_family_mode_counts[convert_route_family_mode] += 1
            convert_semantic_trial_mode_counts[convert_semantic_trial_mode] += 1

        if policy_phase == "post_feasible_recover":
            recover_pool_sizes.append(_effective_pool_size_from_request_row(row, metadata))

        visible_route_families = _visible_route_families_from_request_row(row, metadata)
        positive_route_families = _positive_route_families_from_retrieval_panel(retrieval_panel)
        for route_family in sorted(positive_route_families - visible_route_families):
            hidden_positive_credit_family_counts[route_family] += 1

    return {
        "phase_counts": dict(phase_counts),
        "convert_route_family_mode_counts": dict(convert_route_family_mode_counts),
        "convert_semantic_trial_mode_counts": dict(convert_semantic_trial_mode_counts),
        "recover_pool_size_summary": _pool_size_summary(recover_pool_sizes),
        "hidden_positive_credit_family_counts": dict(sorted(hidden_positive_credit_family_counts.items())),
    }


def _load_history(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        dict(row)
        for row in payload.get("history", [])
        if isinstance(row, Mapping)
    ]


def _normalize_history_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "evaluation_index": None if row.get("evaluation_index") is None else int(row["evaluation_index"]),
        "source": str(row.get("source", "")),
        "feasible": bool(row.get("feasible", False)),
        "decision_vector": _normalized_mapping(row.get("decision_vector")),
        "objective_values": _normalized_mapping(row.get("objective_values")),
        "constraint_values": _normalized_mapping(row.get("constraint_values")),
        "failure_reason": row.get("failure_reason"),
    }


def _normalized_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, bool):
            normalized[str(key)] = item
        elif isinstance(item, int | float):
            normalized[str(key)] = float(item)
        else:
            normalized[str(key)] = item
    return normalized


def _first_feasible_eval(history: list[Mapping[str, Any]]) -> int | None:
    feasible_rows = [
        int(row["evaluation_index"])
        for row in history
        if str(row.get("source", "")).strip().lower() != "baseline"
        and bool(row.get("feasible", False))
        and row.get("evaluation_index") is not None
    ]
    return None if not feasible_rows else min(feasible_rows)


def _decision_id_from_row(row: Mapping[str, Any]) -> str:
    value = str(row.get("decision_id", "")).strip()
    if value:
        return value
    evaluation_index = int(row.get("evaluation_index", -1))
    decision_index = int(row.get("decision_index", row.get("attempt_index", 0)))
    return f"eval:{evaluation_index}:decision:{decision_index}"


def _policy_phase_from_row(row: Mapping[str, Any]) -> str:
    for key in ("policy_phase", "guardrail_policy_phase", "phase"):
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return "unknown"


def _policy_phase_from_request_row(
    row: Mapping[str, Any],
    *,
    regime_panel: Mapping[str, Any],
) -> str:
    policy_phase = _policy_phase_from_row(row)
    if policy_phase != "unknown":
        return policy_phase
    regime_phase = str(regime_panel.get("phase", "")).strip()
    return regime_phase or "unknown"


def _request_metadata_from_row(
    row: Mapping[str, Any],
    *,
    run_root: Path | None,
) -> dict[str, Any]:
    metadata = row.get("metadata")
    if isinstance(metadata, Mapping):
        return dict(metadata)
    user_prompt = row.get("user_prompt")
    if isinstance(user_prompt, str) and user_prompt.strip():
        try:
            payload = json.loads(user_prompt)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, Mapping) and isinstance(payload.get("metadata"), Mapping):
            return dict(payload["metadata"])
    prompt_ref = str(row.get("prompt_ref", "")).strip()
    if prompt_ref and run_root is not None:
        prompt_path = run_root / prompt_ref
        if prompt_path.exists():
            return _metadata_from_prompt_markdown(prompt_path)
    return {}


def _metadata_from_prompt_markdown(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    marker = "# User"
    if marker not in content:
        return {}
    user_block = content.split(marker, 1)[1].strip()
    if user_block.startswith("#"):
        return {}
    try:
        payload = json.loads(user_block)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, Mapping):
        return {}
    metadata = payload.get("metadata", {})
    return dict(metadata) if isinstance(metadata, Mapping) else {}


def _operator_id_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if str(item).strip()]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _effective_pool_size_from_request_row(
    row: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> int:
    direct_size = row.get("effective_candidate_pool_size")
    if direct_size is not None:
        return int(direct_size)
    guardrail = metadata.get("decision_guardrail", {})
    if isinstance(guardrail, Mapping):
        effective_candidate_operator_ids = _operator_id_list(guardrail.get("effective_candidate_operator_ids", []))
        if effective_candidate_operator_ids:
            return len(effective_candidate_operator_ids)
    return len(_operator_id_list(metadata.get("candidate_operator_ids", [])))


def _visible_route_families_from_request_row(
    row: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> set[str]:
    direct_visible = {value for value in _string_list(row.get("visible_route_families", [])) if value}
    if direct_visible:
        return direct_visible
    guardrail = metadata.get("decision_guardrail", {})
    if isinstance(guardrail, Mapping):
        effective_candidate_operator_ids = _operator_id_list(guardrail.get("effective_candidate_operator_ids", []))
        if effective_candidate_operator_ids:
            return {
                operator_route_family(operator_id)
                for operator_id in effective_candidate_operator_ids
                if operator_route_family(operator_id)
            }
    candidate_operator_ids = _operator_id_list(metadata.get("candidate_operator_ids", []))
    return {
        operator_route_family(operator_id)
        for operator_id in candidate_operator_ids
        if operator_route_family(operator_id)
    }


def _positive_route_families_from_retrieval_panel(retrieval_panel: Mapping[str, Any]) -> set[str]:
    positive_credit_route_families = _positive_credit_route_families_from_retrieval_panel(retrieval_panel)
    if positive_credit_route_families:
        return positive_credit_route_families
    return _positive_match_route_families_from_retrieval_panel(retrieval_panel)


def _positive_credit_route_families_from_retrieval_panel(retrieval_panel: Mapping[str, Any]) -> set[str]:
    route_family_credit = retrieval_panel.get("route_family_credit", {})
    if isinstance(route_family_credit, Mapping):
        return {
            value
            for value in _string_list(route_family_credit.get("positive_families", []))
            if value
        }
    return set()


def _positive_match_route_families_from_retrieval_panel(retrieval_panel: Mapping[str, Any]) -> set[str]:
    positive_matches = retrieval_panel.get("positive_matches", [])
    if not isinstance(positive_matches, list | tuple):
        return set()
    return {
        str(match.get("route_family", "")).strip()
        for match in positive_matches
        if isinstance(match, Mapping) and str(match.get("route_family", "")).strip()
    }


def _pool_size_summary(values: Sequence[int]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0, "max": 0, "avg": 0.0}
    return {
        "count": int(len(values)),
        "min": int(min(values)),
        "max": int(max(values)),
        "avg": float(sum(values) / len(values)),
    }


def _size_summary(values: list[int]) -> dict[str, int]:
    if not values:
        return {"min": 0, "max": 0}
    return {"min": min(values), "max": max(values)}
