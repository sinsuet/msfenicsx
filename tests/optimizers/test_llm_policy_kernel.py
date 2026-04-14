from __future__ import annotations

import importlib

import pytest

from optimizers.operator_pool.state import ControllerState


def _policy_kernel_module():
    try:
        return importlib.import_module("optimizers.operator_pool.policy_kernel")
    except ModuleNotFoundError as exc:  # pragma: no cover
        pytest.fail(f"Missing reusable policy kernel module: {exc}")


def _cold_start_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=1,
        evaluation_index=18,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 0,
                "evaluations_used": 17,
                "evaluations_remaining": 112,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
            },
            "recent_decisions": [],
            "operator_summary": {},
        },
    )


def _prefeasible_family_collapse_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=81,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 23,
                "evaluations_used": 80,
                "evaluations_remaining": 49,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 73 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "move_hottest_cluster_toward_sink",
                        "spread_hottest_cluster",
                        "move_hottest_cluster_toward_sink",
                        "spread_hottest_cluster",
                        "move_hottest_cluster_toward_sink",
                        "spread_hottest_cluster",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {"selection_count": 3, "recent_selection_count": 0, "proposal_count": 3},
                "local_refine": {"selection_count": 4, "recent_selection_count": 0, "proposal_count": 4},
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 18,
                    "recent_selection_count": 3,
                    "proposal_count": 18,
                },
                "spread_hottest_cluster": {
                    "selection_count": 12,
                    "recent_selection_count": 3,
                    "proposal_count": 12,
                },
            },
        },
    )


def _prefeasible_reset_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=64,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 19,
                "evaluations_used": 63,
                "evaluations_remaining": 66,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
            },
            "progress_state": {
                "phase": "prefeasible_stagnation",
                "recent_no_progress_count": 6,
                "last_progress_eval": 49,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 56 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "move_hottest_cluster_toward_sink",
                        "repair_sink_budget",
                        "spread_hottest_cluster",
                        "repair_sink_budget",
                        "move_hottest_cluster_toward_sink",
                        "spread_hottest_cluster",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {"selection_count": 5, "recent_selection_count": 0, "proposal_count": 5},
                "global_explore": {"selection_count": 3, "recent_selection_count": 0, "proposal_count": 3},
                "local_refine": {"selection_count": 4, "recent_selection_count": 0, "proposal_count": 4},
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 7,
                    "recent_selection_count": 2,
                    "proposal_count": 7,
                },
                "repair_sink_budget": {
                    "selection_count": 14,
                    "recent_selection_count": 2,
                    "proposal_count": 14,
                },
            },
        },
    )


def _post_feasible_expand_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=78,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 18,
                "evaluations_used": 77,
                "evaluations_remaining": 52,
                "feasible_rate": 0.15,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 3,
                "last_progress_eval": 75,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 9,
                    "recent_selection_count": 1,
                    "proposal_count": 9,
                    "feasible_preservation_count": 3,
                },
                "local_refine": {
                    "selection_count": 6,
                    "recent_selection_count": 1,
                    "proposal_count": 6,
                    "feasible_entry_count": 1,
                    "feasible_preservation_count": 2,
                },
                "repair_sink_budget": {
                    "selection_count": 5,
                    "recent_selection_count": 0,
                    "proposal_count": 5,
                    "pareto_contribution_count": 2,
                    "post_feasible_avg_objective_delta": -0.35,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
            },
        },
    )


def _post_feasible_recover_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=78,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 18,
                "evaluations_used": 77,
                "evaluations_remaining": 52,
                "feasible_rate": 0.15,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 1,
                "last_progress_eval": 75,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 9,
                    "recent_selection_count": 1,
                    "proposal_count": 9,
                    "feasible_preservation_count": 3,
                },
                "local_refine": {
                    "selection_count": 6,
                    "recent_selection_count": 1,
                    "proposal_count": 6,
                    "feasible_entry_count": 1,
                    "feasible_preservation_count": 2,
                },
                "repair_sink_budget": {
                    "selection_count": 5,
                    "recent_selection_count": 0,
                    "proposal_count": 5,
                    "feasible_regression_count": 1,
                },
            },
        },
    )


def test_cold_start_bootstraps_only_stable_semantic_families() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _cold_start_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
        ),
    )

    assert policy.phase == "cold_start"
    assert policy.allowed_operator_ids == ("native_sbx_pm", "global_explore", "local_refine")
    assert "cold_start_stable_bootstrap" in policy.reason_codes


def test_prefeasible_family_collapse_suppresses_overused_semantic_custom_family() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _prefeasible_family_collapse_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "spread_hottest_cluster",
        ),
    )

    assert "prefeasible_speculative_family_collapse" in policy.reason_codes
    assert "move_hottest_cluster_toward_sink" not in policy.allowed_operator_ids
    assert "spread_hottest_cluster" not in policy.allowed_operator_ids


def test_prefeasible_reset_biases_back_to_stable_semantic_roles() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _prefeasible_reset_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
    )

    assert policy.reset_active is True
    assert "prefeasible_forced_reset" in policy.reason_codes
    assert policy.allowed_operator_ids == ("native_sbx_pm", "global_explore", "local_refine")


def test_post_feasible_expand_filters_out_risky_semantic_expanders() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "repair_sink_budget",
            "move_hottest_cluster_toward_sink",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert "move_hottest_cluster_toward_sink" in policy.allowed_operator_ids
    assert "repair_sink_budget" in policy.allowed_operator_ids
    assert policy.candidate_annotations["repair_sink_budget"]["post_feasible_role"] == "supported_expand"


def test_post_feasible_recover_keeps_only_trusted_preserve_roles() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "repair_sink_budget",
        ),
    )

    assert policy.phase == "post_feasible_recover"
    assert "native_sbx_pm" in policy.allowed_operator_ids
    assert "local_refine" in policy.allowed_operator_ids
    assert "repair_sink_budget" in policy.allowed_operator_ids
