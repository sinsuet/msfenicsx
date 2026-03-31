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
