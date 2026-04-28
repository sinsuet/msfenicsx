"""Shared route-family semantics for controller prompting and diagnostics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from math import log2
from typing import Any

from optimizers.operator_pool.operators import get_operator_behavior_profile

ROUTE_FAMILY_BY_OPERATOR: dict[str, str] = {
    "vector_sbx_pm": "stable_local",
    "component_jitter_1": "stable_local",
    "anchored_component_jitter": "stable_local",
    "component_relocate_1": "stable_global",
    "component_swap_2": "stable_global",
    "sink_shift": "stable_local",
    "sink_resize": "stable_local",
    "hotspot_pull_toward_sink": "sink_retarget",
    "hotspot_spread": "hotspot_spread",
    "gradient_band_smooth": "congestion_relief",
    "congestion_relief": "congestion_relief",
    "sink_retarget": "sink_retarget",
    "layout_rebalance": "layout_rebalance",
    # Legacy trace aliases kept for diagnostics and LLM policy fixtures. These
    # ids are not part of the active primitive/assisted registries.
    "move_hottest_cluster_toward_sink": "sink_retarget",
    "spread_hottest_cluster": "hotspot_spread",
    "smooth_high_gradient_band": "congestion_relief",
    "reduce_local_congestion": "congestion_relief",
    "repair_sink_budget": "budget_guard",
    "slide_sink": "sink_retarget",
    "rebalance_layout": "layout_rebalance",
}
STABLE_ROUTE_FAMILIES = frozenset({"stable_local", "stable_global"})


def operator_route_family(operator_id: str) -> str:
    normalized = str(operator_id)
    route_family = ROUTE_FAMILY_BY_OPERATOR.get(normalized)
    if route_family is not None:
        return route_family
    try:
        profile = get_operator_behavior_profile(normalized)
    except KeyError:
        if normalized.startswith("native_"):
            return "stable_local"
        return "unknown"
    if profile.exploration_class == "stable":
        if profile.family == "global_explore":
            return "stable_global"
        return "stable_local"
    return "unknown"


def route_family_counts(
    rows: list[Mapping[str, Any]],
    *,
    phase: str | None = None,
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if phase is not None and str(row.get("policy_phase", "")).strip() != phase:
            continue
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if not operator_id:
            continue
        counter[operator_route_family(operator_id)] += 1
    return dict(counter)


def route_family_entropy(counts: Mapping[str, int]) -> float:
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


def expand_budget_score(
    *,
    recent_expand_feasible_preservation_count: int,
    recent_expand_feasible_regression_count: int,
    recent_expand_frontier_add_count: int,
) -> int:
    return (
        2 * int(recent_expand_frontier_add_count)
        + int(recent_expand_feasible_preservation_count)
        - 2 * int(recent_expand_feasible_regression_count)
    )


def expand_budget_status(
    *,
    route_family: str,
    recent_expand_selection_count: int,
    recent_expand_feasible_preservation_count: int,
    recent_expand_feasible_regression_count: int,
    recent_expand_frontier_add_count: int,
) -> str:
    normalized_route_family = str(route_family)
    if normalized_route_family in STABLE_ROUTE_FAMILIES:
        return "preferred"
    if int(recent_expand_selection_count) <= 0:
        return "neutral"
    if (
        int(recent_expand_frontier_add_count) <= 0
        and int(recent_expand_feasible_regression_count) > int(recent_expand_feasible_preservation_count)
    ):
        return "throttled"
    if (
        int(recent_expand_frontier_add_count) > 0
        or int(recent_expand_feasible_preservation_count) > int(recent_expand_feasible_regression_count)
    ):
        return "preferred"
    return "neutral"


def expand_budget_family_metrics(
    candidate_operator_ids: Sequence[str],
    *,
    summary_by_operator: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    family_metrics: dict[str, dict[str, Any]] = {}
    for operator_id in candidate_operator_ids:
        normalized_operator_id = str(operator_id)
        route_family = operator_route_family(normalized_operator_id)
        operator_summary = summary_by_operator.get(normalized_operator_id, {})
        metrics = family_metrics.setdefault(
            route_family,
            {
                "route_family": route_family,
                "recent_expand_selection_count": 0,
                "recent_expand_feasible_preservation_count": 0,
                "recent_expand_feasible_regression_count": 0,
                "recent_expand_frontier_add_count": 0,
            },
        )
        metrics["recent_expand_selection_count"] += int(operator_summary.get("recent_expand_selection_count", 0))
        metrics["recent_expand_feasible_preservation_count"] += int(
            operator_summary.get("recent_expand_feasible_preservation_count", 0)
        )
        metrics["recent_expand_feasible_regression_count"] += int(
            operator_summary.get("recent_expand_feasible_regression_count", 0)
        )
        metrics["recent_expand_frontier_add_count"] += int(
            operator_summary.get("recent_expand_frontier_add_count", 0)
        )

    for route_family, metrics in family_metrics.items():
        metrics["expand_budget_score"] = int(
            expand_budget_score(
                recent_expand_feasible_preservation_count=int(
                    metrics["recent_expand_feasible_preservation_count"]
                ),
                recent_expand_feasible_regression_count=int(metrics["recent_expand_feasible_regression_count"]),
                recent_expand_frontier_add_count=int(metrics["recent_expand_frontier_add_count"]),
            )
        )
        metrics["expand_budget_status"] = expand_budget_status(
            route_family=route_family,
            recent_expand_selection_count=int(metrics["recent_expand_selection_count"]),
            recent_expand_feasible_preservation_count=int(
                metrics["recent_expand_feasible_preservation_count"]
            ),
            recent_expand_feasible_regression_count=int(metrics["recent_expand_feasible_regression_count"]),
            recent_expand_frontier_add_count=int(metrics["recent_expand_frontier_add_count"]),
        )
        metrics["budget_status"] = str(metrics["expand_budget_status"])
    return family_metrics
