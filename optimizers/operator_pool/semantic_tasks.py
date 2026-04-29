"""Semantic task taxonomy for LLM operator portfolio planning."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from math import log2
from typing import Any

SEMANTIC_TASK_BY_OPERATOR: dict[str, str] = {
    "vector_sbx_pm": "baseline_reset",
    "native_sbx_pm": "baseline_reset",
    "component_relocate_1": "global_layout_expand",
    "component_swap_2": "global_layout_expand",
    "global_explore": "global_layout_expand",
    "component_block_translate_2_4": "semantic_block_move",
    "component_subspace_sbx": "semantic_subspace_recombine",
    "sink_shift": "sink_alignment",
    "slide_sink": "sink_alignment",
    "sink_resize": "sink_budget_shape",
    "repair_sink_budget": "sink_budget_shape",
    "component_jitter_1": "local_polish",
    "anchored_component_jitter": "local_polish",
    "local_refine": "local_polish",
    "hotspot_pull_toward_sink": "sink_alignment",
    "sink_retarget": "sink_alignment",
    "move_hottest_cluster_toward_sink": "sink_alignment",
    "hotspot_spread": "semantic_block_move",
    "gradient_band_smooth": "local_polish",
    "congestion_relief": "local_polish",
    "layout_rebalance": "global_layout_expand",
    "spread_hottest_cluster": "semantic_block_move",
    "smooth_high_gradient_band": "local_polish",
    "reduce_local_congestion": "local_polish",
    "rebalance_layout": "global_layout_expand",
}

SEMANTIC_TASK_DESCRIPTIONS: dict[str, str] = {
    "baseline_reset": "use the native backbone variation as a fair reset anchor when the guided search narrows too much.",
    "global_layout_expand": "test a broader component arrangement or ordering to open a new layout basin.",
    "semantic_block_move": "move or reshape a compact component cluster to change the hotspot geometry.",
    "semantic_subspace_recombine": "recombine a compact component subspace to diversify local layout structure.",
    "sink_alignment": "shift sink alignment toward a persistent hotspot offset.",
    "sink_budget_shape": "reshape sink span or coverage when budget usage and hotspot coverage need a different window.",
    "local_polish": "make low-risk local component refinements after a useful basin has been found.",
}

_POST_FEASIBLE_TASK_TARGETS: dict[str, tuple[float, float]] = {
    "baseline_reset": (0.05, 0.18),
    "global_layout_expand": (0.12, 0.28),
    "semantic_block_move": (0.08, 0.22),
    "semantic_subspace_recombine": (0.08, 0.25),
    "sink_alignment": (0.05, 0.20),
    "sink_budget_shape": (0.05, 0.18),
    "local_polish": (0.10, 0.30),
}


def semantic_task_for_operator(operator_id: str) -> str:
    return SEMANTIC_TASK_BY_OPERATOR.get(str(operator_id), "unknown")


def semantic_task_description(task_id: str) -> str:
    return SEMANTIC_TASK_DESCRIPTIONS.get(str(task_id), "match the current controller regime.")


def semantic_task_target(task_id: str) -> tuple[float, float]:
    return _POST_FEASIBLE_TASK_TARGETS.get(str(task_id), (0.0, 1.0))


def operators_by_semantic_task(candidate_operator_ids: Sequence[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for operator_id in candidate_operator_ids:
        normalized_operator_id = str(operator_id)
        task_id = semantic_task_for_operator(normalized_operator_id)
        if task_id == "unknown":
            continue
        grouped.setdefault(task_id, []).append(normalized_operator_id)
    return grouped


def semantic_task_counts(rows: Sequence[Mapping[str, Any]], *, phase: str | None = None) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if phase is not None and str(row.get("policy_phase", row.get("phase", ""))).strip() != phase:
            continue
        task_id = str(row.get("selected_semantic_task", "")).strip()
        if not task_id:
            operator_id = str(row.get("selected_operator_id") or row.get("operator_selected") or "").strip()
            if not operator_id:
                continue
            task_id = semantic_task_for_operator(operator_id)
        if task_id and task_id != "unknown":
            counter[task_id] += 1
    return dict(counter)


def semantic_task_entropy(counts: Mapping[str, int]) -> float:
    total = sum(max(int(value), 0) for value in counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in counts.values():
        count = max(int(value), 0)
        if count <= 0:
            continue
        probability = float(count) / float(total)
        entropy -= probability * log2(probability)
    return float(entropy)
