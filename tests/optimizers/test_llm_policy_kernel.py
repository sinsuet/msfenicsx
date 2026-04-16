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


def _post_feasible_recover_peak_balance_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=102,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 42,
                "evaluations_used": 101,
                "evaluations_remaining": 100,
                "feasible_rate": 1.0,
                "first_feasible_eval": 21,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 8,
                "recent_frontier_stagnation_count": 10,
                "last_progress_eval": 94,
                "objective_stagnation": {
                    "temperature_max": {
                        "best_value": 307.0,
                        "evaluations_since_improvement": 12,
                        "stagnant": True,
                    },
                    "gradient_rms": {
                        "best_value": 10.8,
                        "evaluations_since_improvement": 1,
                        "stagnant": False,
                    },
                },
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_recover",
                    "preservation_pressure": "high",
                    "frontier_pressure": "high",
                    "objective_balance": {
                        "stagnant_objectives": ["temperature_max"],
                        "improving_objectives": ["gradient_rms"],
                        "balance_pressure": "high",
                        "preferred_effect": "peak_improve",
                    },
                }
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 20,
                    "recent_selection_count": 2,
                    "proposal_count": 20,
                    "feasible_preservation_count": 8,
                },
                "local_refine": {
                    "selection_count": 18,
                    "recent_selection_count": 3,
                    "proposal_count": 18,
                    "feasible_preservation_count": 6,
                },
                "slide_sink": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
                "repair_sink_budget": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
            },
        },
    )


def _post_feasible_expand_peak_balance_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=132,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 58,
                "evaluations_used": 131,
                "evaluations_remaining": 70,
                "feasible_rate": 1.0,
                "first_feasible_eval": 21,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 5,
                "recent_frontier_stagnation_count": 6,
                "last_progress_eval": 126,
                "objective_stagnation": {
                    "temperature_max": {
                        "best_value": 306.6,
                        "evaluations_since_improvement": 10,
                        "stagnant": True,
                    },
                    "gradient_rms": {
                        "best_value": 11.2,
                        "evaluations_since_improvement": 1,
                        "stagnant": False,
                    },
                },
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "preservation_pressure": "medium",
                    "frontier_pressure": "high",
                    "objective_balance": {
                        "stagnant_objectives": ["temperature_max"],
                        "improving_objectives": ["gradient_rms"],
                        "balance_pressure": "high",
                        "preferred_effect": "peak_improve",
                    },
                }
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 28,
                    "recent_selection_count": 3,
                    "proposal_count": 28,
                    "feasible_preservation_count": 10,
                    "feasible_regression_count": 3,
                    "pareto_contribution_count": 4,
                },
                "local_refine": {
                    "selection_count": 26,
                    "recent_selection_count": 4,
                    "proposal_count": 26,
                    "feasible_preservation_count": 9,
                    "feasible_regression_count": 2,
                    "pareto_contribution_count": 3,
                },
                "slide_sink": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
                "repair_sink_budget": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
            },
        },
    )


def _post_feasible_expand_peak_balance_support_only_slide_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=132,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 58,
                "evaluations_used": 131,
                "evaluations_remaining": 70,
                "feasible_rate": 1.0,
                "first_feasible_eval": 21,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 5,
                "recent_frontier_stagnation_count": 6,
                "last_progress_eval": 126,
                "objective_stagnation": {
                    "temperature_max": {
                        "best_value": 306.6,
                        "evaluations_since_improvement": 10,
                        "stagnant": True,
                    },
                    "gradient_rms": {
                        "best_value": 11.2,
                        "evaluations_since_improvement": 1,
                        "stagnant": False,
                    },
                },
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "preservation_pressure": "medium",
                    "frontier_pressure": "high",
                    "objective_balance": {
                        "stagnant_objectives": ["temperature_max"],
                        "improving_objectives": ["gradient_rms"],
                        "balance_pressure": "high",
                        "preferred_effect": "peak_improve",
                    },
                }
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 28,
                    "recent_selection_count": 3,
                    "proposal_count": 28,
                    "feasible_preservation_count": 10,
                    "feasible_regression_count": 3,
                    "pareto_contribution_count": 4,
                },
                "local_refine": {
                    "selection_count": 26,
                    "recent_selection_count": 4,
                    "proposal_count": 26,
                    "feasible_preservation_count": 9,
                    "feasible_regression_count": 2,
                    "pareto_contribution_count": 3,
                },
                "slide_sink": {
                    "selection_count": 4,
                    "recent_selection_count": 3,
                    "proposal_count": 4,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
                "repair_sink_budget": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
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
    assert "post_feasible_expand_frontier_bias" in policy.reason_codes
    assert "move_hottest_cluster_toward_sink" not in policy.allowed_operator_ids
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
    assert "post_feasible_recover_preserve_bias" in policy.reason_codes
    assert policy.allowed_operator_ids == ("native_sbx_pm", "local_refine")


def test_post_feasible_recover_peak_balance_keeps_peak_escape_candidates() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_peak_balance_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "slide_sink",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
    )

    assert policy.phase == "post_feasible_recover"
    assert "post_feasible_recover_preserve_bias" in policy.reason_codes
    assert "slide_sink" in policy.allowed_operator_ids
    assert "move_hottest_cluster_toward_sink" in policy.allowed_operator_ids


def test_post_feasible_expand_peak_balance_keeps_peak_escape_candidates() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_peak_balance_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "slide_sink",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert "post_feasible_expand_frontier_bias" in policy.reason_codes
    assert "slide_sink" in policy.allowed_operator_ids
    assert "move_hottest_cluster_toward_sink" in policy.allowed_operator_ids


def test_post_feasible_expand_peak_balance_does_not_upgrade_support_only_slide_sink() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_peak_balance_support_only_slide_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "slide_sink",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
    )

    assert policy.candidate_annotations["slide_sink"]["evidence_level"] == "speculative"
    assert policy.candidate_annotations["slide_sink"]["post_feasible_role"] == "risky_expand"
    assert "slide_sink" in policy.allowed_operator_ids
