from __future__ import annotations

import importlib

import pytest

from optimizers.operator_pool.state import ControllerState


def _policy_kernel_module():
    try:
        return importlib.import_module("optimizers.operator_pool.policy_kernel")
    except ModuleNotFoundError as exc:  # pragma: no cover - red phase expectation
        pytest.fail(f"Missing reusable policy kernel module: {exc}")


def _cold_start_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=1,
        evaluation_index=18,
        parent_count=2,
        vector_size=8,
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


def _seed17_like_prefeasible_collapse_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=81,
        parent_count=2,
        vector_size=8,
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
                        "battery_to_warm_zone",
                        "hot_pair_separate",
                        "battery_to_warm_zone",
                        "hot_pair_separate",
                        "battery_to_warm_zone",
                        "hot_pair_separate",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "local_refine": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "battery_to_warm_zone": {
                    "selection_count": 18,
                    "recent_selection_count": 3,
                    "proposal_count": 18,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "hot_pair_separate": {
                    "selection_count": 12,
                    "recent_selection_count": 3,
                    "proposal_count": 12,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
            },
        },
    )


def _prefeasible_no_progress_reset_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=64,
        parent_count=2,
        vector_size=8,
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
                        "battery_to_warm_zone",
                        "hot_pair_to_sink",
                        "battery_to_warm_zone",
                        "hot_pair_separate",
                        "battery_to_warm_zone",
                        "hot_pair_to_sink",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 5,
                    "recent_selection_count": 0,
                    "proposal_count": 5,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "sbx_pm_global": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "local_refine": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "hot_pair_to_sink": {
                    "selection_count": 7,
                    "recent_selection_count": 2,
                    "proposal_count": 7,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "battery_to_warm_zone": {
                    "selection_count": 14,
                    "recent_selection_count": 3,
                    "proposal_count": 14,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
            },
        },
    )


def _seed11_like_prefeasible_reset_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=64,
        parent_count=2,
        vector_size=8,
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
                "recent_no_progress_count": 8,
                "last_progress_eval": 48,
                "prefeasible_reset_window_count": 4,
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
                        "native_sbx_pm",
                        "local_refine",
                        "native_sbx_pm",
                        "local_refine",
                        "native_sbx_pm",
                        "local_refine",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 18,
                    "recent_selection_count": 3,
                    "proposal_count": 18,
                    "recent_family_share": 0.5,
                    "recent_role_share": 0.5,
                },
                "sbx_pm_global": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                    "recent_family_share": 0.0,
                    "recent_role_share": 0.0,
                },
                "local_refine": {
                    "selection_count": 15,
                    "recent_selection_count": 3,
                    "proposal_count": 15,
                    "recent_family_share": 0.5,
                    "recent_role_share": 0.5,
                },
                "hot_pair_to_sink": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
            },
        },
    )


def _post_feasible_recovery_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=7,
        evaluation_index=96,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 32,
                "evaluations_used": 95,
                "evaluations_remaining": 34,
                "feasible_rate": 0.18,
                "first_feasible_eval": 43,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 3,
                "recent_frontier_stagnation_count": 3,
                "last_progress_eval": 92,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 91 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "battery_to_warm_zone",
                        "radiator_expand",
                        "battery_to_warm_zone",
                        "radiator_expand",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 9,
                    "recent_selection_count": 0,
                    "proposal_count": 9,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 2,
                    "feasible_regression_count": 0,
                    "pareto_contribution_count": 0,
                },
                "local_refine": {
                    "selection_count": 7,
                    "recent_selection_count": 0,
                    "proposal_count": 7,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 3,
                    "feasible_regression_count": 0,
                    "pareto_contribution_count": 1,
                },
                "battery_to_warm_zone": {
                    "selection_count": 10,
                    "recent_selection_count": 2,
                    "proposal_count": 10,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                    "feasible_regression_count": 2,
                    "pareto_contribution_count": 0,
                },
                "radiator_expand": {
                    "selection_count": 8,
                    "recent_selection_count": 2,
                    "proposal_count": 8,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                    "feasible_regression_count": 2,
                    "pareto_contribution_count": 0,
                },
            },
        },
    )


def _preentry_post_feasible_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=52,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 15,
                "evaluations_used": 51,
                "evaluations_remaining": 78,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "first_feasible_found": False,
                "evaluations_since_first_feasible": None,
                "recent_no_progress_count": 6,
                "recent_frontier_stagnation_count": 3,
                "post_feasible_mode": "expand",
            },
            "recent_decisions": [
                {
                    "evaluation_index": 47,
                    "selected_operator_id": "native_sbx_pm",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 48,
                    "selected_operator_id": "local_refine",
                    "fallback_used": False,
                    "llm_valid": True,
                },
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "feasible_preservation_count": 1,
                    "pareto_contribution_count": 1,
                },
                "local_refine": {
                    "selection_count": 9,
                    "recent_selection_count": 1,
                    "proposal_count": 9,
                    "feasible_preservation_count": 1,
                    "pareto_contribution_count": 1,
                },
                "radiator_expand": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                    "pareto_contribution_count": 2,
                    "post_feasible_avg_objective_delta": -0.2,
                },
            },
        },
    )


def _near_feasible_convert_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=66,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 20,
                "evaluations_used": 65,
                "evaluations_remaining": 64,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
            },
            "progress_state": {
                "phase": "prefeasible_stagnation",
                "prefeasible_mode": "convert",
                "recent_no_progress_count": 5,
                "evaluations_since_near_feasible_improvement": 4,
                "recent_dominant_violation_family": "cold_dominant",
                "recent_dominant_violation_persistence_count": 6,
                "prefeasible_reset_window_count": 3,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 61 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "native_sbx_pm",
                        "local_refine",
                        "native_sbx_pm",
                        "sbx_pm_global",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 19,
                    "recent_selection_count": 2,
                    "proposal_count": 19,
                    "recent_family_share": 0.5,
                    "recent_role_share": 0.5,
                    "feasible_entry_count": 0,
                    "dominant_violation_relief_count": 0,
                },
                "sbx_pm_global": {
                    "selection_count": 4,
                    "recent_selection_count": 1,
                    "proposal_count": 4,
                    "recent_family_share": 0.25,
                    "recent_role_share": 0.25,
                    "feasible_entry_count": 0,
                    "dominant_violation_relief_count": 0,
                },
                "local_refine": {
                    "selection_count": 11,
                    "recent_selection_count": 1,
                    "proposal_count": 11,
                    "recent_family_share": 0.25,
                    "recent_role_share": 0.25,
                    "feasible_entry_count": 0,
                    "dominant_violation_relief_count": 3,
                    "near_feasible_improvement_count": 2,
                },
                "battery_to_warm_zone": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                    "dominant_violation_relief_count": 0,
                },
            },
        },
    )


def test_policy_kernel_marks_cold_start_when_no_feasible_and_no_supported_evidence() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _cold_start_state(),
        ("native_sbx_pm", "battery_to_warm_zone", "local_refine"),
    )

    assert policy.phase == "cold_start"
    assert "native_sbx_pm" in policy.allowed_operator_ids


def test_policy_kernel_blocks_zero_credit_custom_family_collapse() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _seed17_like_prefeasible_collapse_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone", "hot_pair_separate"),
    )

    assert "battery_to_warm_zone" not in policy.allowed_operator_ids
    assert "hot_pair_separate" not in policy.allowed_operator_ids


def test_policy_kernel_enters_forced_reset_after_speculative_no_progress_streak() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _prefeasible_no_progress_reset_state(),
        ("native_sbx_pm", "sbx_pm_global", "local_refine", "hot_pair_to_sink"),
    )

    assert policy.reset_active is True
    assert policy.allowed_operator_ids == ("native_sbx_pm", "sbx_pm_global", "local_refine")


def test_prefeasible_reset_keeps_global_explore_visibility_when_no_feasible_exists() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _seed11_like_prefeasible_reset_state(),
        ("native_sbx_pm", "sbx_pm_global", "local_refine", "hot_pair_to_sink"),
    )

    assert "sbx_pm_global" in policy.allowed_operator_ids
    assert policy.candidate_annotations["sbx_pm_global"]["prefeasible_role"] == "stable_global"


def test_prefeasible_reset_limits_same_role_monopoly_without_custom_operator_patch() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _seed11_like_prefeasible_reset_state(),
        ("native_sbx_pm", "sbx_pm_global", "local_refine", "hot_pair_to_sink"),
    )

    assert policy.candidate_annotations["native_sbx_pm"]["prefeasible_role"] == "stable_baseline"
    assert policy.candidate_annotations["local_refine"]["prefeasible_role"] == "stable_local"


def test_policy_kernel_enters_post_feasible_recover_when_frontier_regresses() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recovery_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone", "radiator_expand"),
    )

    assert policy.phase == "post_feasible_recover"


def test_policy_kernel_limits_unproven_expansion_families_during_post_feasible_recover() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recovery_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone", "radiator_expand"),
    )

    assert policy.allowed_operator_ids == ("native_sbx_pm", "local_refine")
    assert policy.candidate_annotations["local_refine"]["post_feasible_role"] == "trusted_preserve"
    assert policy.candidate_annotations["battery_to_warm_zone"]["post_feasible_role"] == "risky_expand"


def test_policy_kernel_requires_real_feasible_entry_before_post_feasible_modes_activate() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _preentry_post_feasible_state(),
        ("native_sbx_pm", "local_refine", "radiator_expand"),
    )

    assert policy.phase.startswith("prefeasible")
    assert "post_feasible_role" not in policy.candidate_annotations["local_refine"]


def test_policy_kernel_enters_prefeasible_convert_when_near_feasible_progress_stalls() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _near_feasible_convert_state(),
        ("native_sbx_pm", "sbx_pm_global", "local_refine", "battery_to_warm_zone"),
    )

    assert policy.phase == "prefeasible_convert"


def test_prefeasible_convert_shortlist_keeps_stable_roles_and_supported_entry_candidates() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _near_feasible_convert_state(),
        ("native_sbx_pm", "sbx_pm_global", "local_refine", "battery_to_warm_zone"),
    )

    assert "sbx_pm_global" in policy.allowed_operator_ids
    assert policy.candidate_annotations["local_refine"]["prefeasible_role"] == "stable_local"
    assert policy.candidate_annotations["local_refine"]["entry_evidence_level"] in {"supported", "trusted"}
