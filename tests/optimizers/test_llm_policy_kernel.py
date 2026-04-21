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


def _post_feasible_expand_route_overuse_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=96,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 28,
                "evaluations_used": 95,
                "evaluations_remaining": 34,
                "feasible_rate": 0.41,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 4,
                "last_progress_eval": 92,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 88 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "local_refine",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 11,
                    "recent_selection_count": 0,
                    "proposal_count": 11,
                    "feasible_preservation_count": 3,
                },
                "local_refine": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "feasible_preservation_count": 4,
                },
                "spread_hottest_cluster": {
                    "selection_count": 17,
                    "recent_selection_count": 5,
                    "proposal_count": 17,
                    "pareto_contribution_count": 1,
                    "feasible_regression_count": 4,
                },
                "reduce_local_congestion": {
                    "selection_count": 5,
                    "recent_selection_count": 0,
                    "proposal_count": 5,
                    "pareto_contribution_count": 2,
                },
            },
        },
    )


def _recover_exit_ready_state() -> ControllerState:
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
                "decision_index": 31,
                "evaluations_used": 101,
                "evaluations_remaining": 28,
                "feasible_rate": 0.44,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 1,
                "recent_frontier_stagnation_count": 2,
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 0,
                "stable_preservation_streak": 3,
                "new_dominant_violation_family": False,
            },
            "archive_state": {
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 3,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 14,
                    "recent_selection_count": 1,
                    "proposal_count": 14,
                    "feasible_preservation_count": 5,
                },
                "local_refine": {
                    "selection_count": 16,
                    "recent_selection_count": 2,
                    "proposal_count": 16,
                    "feasible_preservation_count": 6,
                },
                "slide_sink": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                    "feasible_preservation_count": 1,
                },
            },
        },
    )


def _recover_pressure_cooled_state_with_old_family_switch() -> ControllerState:
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
                "decision_index": 31,
                "evaluations_used": 101,
                "evaluations_remaining": 28,
                "feasible_rate": 0.44,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 1,
                "recent_frontier_stagnation_count": 0,
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 1,
                "stable_preservation_streak": 0,
                "new_dominant_violation_family": True,
                "recent_violation_family_switch_count": 0,
                "recover_pressure_level": "low",
                "recover_exit_ready": True,
            },
            "archive_state": {
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 2,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 14,
                    "recent_selection_count": 1,
                    "proposal_count": 14,
                    "feasible_preservation_count": 5,
                },
                "local_refine": {
                    "selection_count": 16,
                    "recent_selection_count": 2,
                    "proposal_count": 16,
                    "feasible_preservation_count": 6,
                },
                "slide_sink": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                    "feasible_preservation_count": 1,
                },
            },
        },
    )


def _post_feasible_expand_family_rebalance_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=10,
        evaluation_index=112,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 39,
                "evaluations_used": 111,
                "evaluations_remaining": 18,
                "feasible_rate": 0.53,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 5,
                "last_progress_eval": 108,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 104 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "local_refine",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 14,
                    "recent_selection_count": 0,
                    "proposal_count": 14,
                    "feasible_preservation_count": 4,
                },
                "local_refine": {
                    "selection_count": 18,
                    "recent_selection_count": 1,
                    "proposal_count": 18,
                    "feasible_preservation_count": 5,
                },
                "spread_hottest_cluster": {
                    "selection_count": 22,
                    "recent_selection_count": 5,
                    "proposal_count": 22,
                    "pareto_contribution_count": 1,
                    "feasible_regression_count": 4,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 6,
                    "recent_selection_count": 0,
                    "proposal_count": 6,
                    "pareto_contribution_count": 2,
                    "post_feasible_avg_objective_delta": -0.15,
                },
                "reduce_local_congestion": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                },
            },
        },
    )


def _post_feasible_expand_family_dominance_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=10,
        evaluation_index=118,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 45,
                "evaluations_used": 117,
                "evaluations_remaining": 12,
                "feasible_rate": 0.56,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 6,
                "last_progress_eval": 114,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 110 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "spread_hottest_cluster",
                        "local_refine",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 15,
                    "recent_selection_count": 0,
                    "proposal_count": 15,
                    "feasible_preservation_count": 4,
                },
                "local_refine": {
                    "selection_count": 19,
                    "recent_selection_count": 1,
                    "proposal_count": 19,
                    "feasible_preservation_count": 5,
                },
                "spread_hottest_cluster": {
                    "selection_count": 24,
                    "recent_selection_count": 5,
                    "proposal_count": 24,
                    "pareto_contribution_count": 4,
                    "feasible_regression_count": 1,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 6,
                    "recent_selection_count": 0,
                    "proposal_count": 6,
                    "pareto_contribution_count": 2,
                    "post_feasible_avg_objective_delta": -0.15,
                },
                "reduce_local_congestion": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                },
            },
        },
    )


def _post_feasible_expand_budget_throttle_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=11,
        evaluation_index=121,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 47,
                "evaluations_used": 120,
                "evaluations_remaining": 8,
                "feasible_rate": 0.58,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 4,
                "last_progress_eval": 117,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 114 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "spread_hottest_cluster",
                        "local_refine",
                        "smooth_high_gradient_band",
                        "native_sbx_pm",
                        "spread_hottest_cluster",
                        "local_refine",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 15,
                    "recent_selection_count": 1,
                    "proposal_count": 15,
                    "feasible_preservation_count": 4,
                },
                "local_refine": {
                    "selection_count": 18,
                    "recent_selection_count": 2,
                    "proposal_count": 18,
                    "feasible_preservation_count": 5,
                },
                "spread_hottest_cluster": {
                    "selection_count": 9,
                    "recent_selection_count": 2,
                    "proposal_count": 9,
                    "pareto_contribution_count": 1,
                    "feasible_regression_count": 1,
                    "recent_expand_selection_count": 2,
                    "recent_expand_feasible_preservation_count": 0,
                    "recent_expand_feasible_regression_count": 2,
                    "recent_expand_frontier_add_count": 0,
                },
                "smooth_high_gradient_band": {
                    "selection_count": 7,
                    "recent_selection_count": 1,
                    "proposal_count": 7,
                    "pareto_contribution_count": 1,
                    "post_feasible_avg_objective_delta": -0.22,
                    "recent_expand_selection_count": 1,
                    "recent_expand_feasible_preservation_count": 1,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 1,
                },
            },
        },
    )


def _post_feasible_recover_semantic_monopoly_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=62,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 49,
                "evaluations_used": 61,
                "evaluations_remaining": 12,
                "feasible_rate": 0.75,
                "first_feasible_eval": 3,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 1,
                "recent_frontier_stagnation_count": 2,
                "last_progress_eval": 60,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "feasible_preservation_count": 3,
                    "feasible_regression_count": 1,
                },
                "global_explore": {
                    "selection_count": 9,
                    "recent_selection_count": 1,
                    "proposal_count": 9,
                    "feasible_preservation_count": 1,
                    "feasible_regression_count": 1,
                },
                "local_refine": {
                    "selection_count": 24,
                    "recent_selection_count": 6,
                    "proposal_count": 24,
                    "feasible_preservation_count": 5,
                    "feasible_regression_count": 1,
                },
                "smooth_high_gradient_band": {
                    "selection_count": 8,
                    "recent_selection_count": 2,
                    "proposal_count": 8,
                    "feasible_preservation_count": 2,
                    "pareto_contribution_count": 1,
                    "post_feasible_avg_objective_delta": -0.42,
                },
                "spread_hottest_cluster": {
                    "selection_count": 6,
                    "recent_selection_count": 0,
                    "proposal_count": 6,
                },
                "reduce_local_congestion": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                },
            },
        },
    )


def _post_feasible_recover_gradient_escape_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=88,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 63,
                "evaluations_used": 87,
                "evaluations_remaining": 40,
                "feasible_rate": 0.64,
                "first_feasible_eval": 12,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 3,
                "last_progress_eval": 85,
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_recover",
                    "preservation_pressure": "high",
                    "frontier_pressure": "medium",
                    "objective_balance": {
                        "balance_pressure": "high",
                        "preferred_effect": "gradient_improve",
                        "stagnant_objectives": ["gradient_rms"],
                        "improving_objectives": [],
                    },
                },
                "spatial_panel": {
                    "hotspot_inside_sink_window": False,
                    "nearest_neighbor_gap_min": 0.04,
                    "hottest_cluster_compactness": 0.11,
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 18,
                    "recent_selection_count": 2,
                    "proposal_count": 18,
                    "feasible_preservation_count": 5,
                    "feasible_regression_count": 1,
                },
                "global_explore": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "feasible_preservation_count": 2,
                    "feasible_regression_count": 1,
                },
                "local_refine": {
                    "selection_count": 22,
                    "recent_selection_count": 4,
                    "proposal_count": 22,
                    "feasible_preservation_count": 6,
                    "feasible_regression_count": 1,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                    "feasible_regression_count": 1,
                },
                "smooth_high_gradient_band": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
                "reduce_local_congestion": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
            },
        },
    )


def _post_feasible_recover_positive_budget_credit_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=94,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 27,
                "evaluations_used": 93,
                "evaluations_remaining": 36,
                "feasible_rate": 0.41,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recover_pressure_level": "medium",
                "recover_exit_ready": False,
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 1,
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_recover",
                    "preservation_pressure": "high",
                    "frontier_pressure": "medium",
                },
                "retrieval_panel": {
                    "route_family_credit": {
                        "positive_families": ["budget_guard"],
                        "negative_families": [],
                    }
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 14,
                    "recent_selection_count": 1,
                    "proposal_count": 14,
                    "feasible_preservation_count": 5,
                },
                "local_refine": {
                    "selection_count": 16,
                    "recent_selection_count": 2,
                    "proposal_count": 16,
                    "feasible_preservation_count": 6,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 7,
                    "recent_selection_count": 2,
                    "proposal_count": 7,
                    "pareto_contribution_count": 2,
                    "post_feasible_avg_objective_delta": -0.2,
                },
                "repair_sink_budget": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
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


def test_post_feasible_expand_marks_overused_route_family_for_cooldown() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_route_overuse_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "reduce_local_congestion",
        ),
    )

    route_budget = policy.candidate_annotations["spread_hottest_cluster"]["route_budget_state"]
    assert route_budget["cooldown_active"] is True


def test_recover_exit_ready_state_demotes_recover_phase_back_to_preserve() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _recover_exit_ready_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "slide_sink",
        ),
    )

    assert policy.phase == "post_feasible_preserve"


def test_recover_pressure_cools_even_when_an_old_family_switch_exists() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _recover_pressure_cooled_state_with_old_family_switch(),
        (
            "native_sbx_pm",
            "local_refine",
            "slide_sink",
        ),
    )

    assert policy.phase == "post_feasible_preserve"


def test_post_feasible_expand_rebalances_away_from_cooled_route_family() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_family_rebalance_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "move_hottest_cluster_toward_sink",
            "reduce_local_congestion",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert "spread_hottest_cluster" not in policy.allowed_operator_ids
    assert "move_hottest_cluster_toward_sink" in policy.allowed_operator_ids
    assert "reduce_local_congestion" in policy.allowed_operator_ids


def test_post_feasible_expand_caps_recently_dominant_route_family_even_without_cooldown() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_family_dominance_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "move_hottest_cluster_toward_sink",
            "reduce_local_congestion",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert "spread_hottest_cluster" not in policy.allowed_operator_ids
    assert "move_hottest_cluster_toward_sink" in policy.allowed_operator_ids


def test_post_feasible_expand_throttles_semantic_route_with_recent_regression_and_no_frontier_credit() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_budget_throttle_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "smooth_high_gradient_band",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert policy.candidate_annotations["spread_hottest_cluster"]["expand_budget_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["smooth_high_gradient_band"]["expand_budget_state"]["budget_status"] == "preferred"
    assert "post_feasible_expand_semantic_budget" in policy.reason_codes
    assert "spread_hottest_cluster" not in policy.allowed_operator_ids
    assert "smooth_high_gradient_band" in policy.allowed_operator_ids


def _post_feasible_expand_saturated_state() -> ControllerState:
    """Expand has been running 30+ evals without a frontier add -- should be demoted."""
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=14,
        evaluation_index=180,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 98,
                "evaluations_used": 179,
                "evaluations_remaining": 77,
                "feasible_rate": 0.78,
                "first_feasible_eval": 3,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 30,
                "recent_frontier_stagnation_count": 30,
                "last_progress_eval": 150,
                "stable_preservation_streak": 5,
                "new_dominant_violation_family": False,
                "expand_saturation_count": 30,
            },
            "archive_state": {
                "pareto_size": 4,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 30,
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 3,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 40,
                    "recent_selection_count": 2,
                    "proposal_count": 40,
                    "feasible_preservation_count": 12,
                },
                "local_refine": {
                    "selection_count": 35,
                    "recent_selection_count": 3,
                    "proposal_count": 35,
                    "feasible_preservation_count": 10,
                },
                "spread_hottest_cluster": {
                    "selection_count": 22,
                    "recent_selection_count": 2,
                    "proposal_count": 22,
                    "pareto_contribution_count": 1,
                    "feasible_preservation_count": 4,
                    "feasible_regression_count": 3,
                    "recent_expand_selection_count": 2,
                    "recent_expand_feasible_preservation_count": 1,
                    "recent_expand_feasible_regression_count": 1,
                    "recent_expand_frontier_add_count": 0,
                },
                "smooth_high_gradient_band": {
                    "selection_count": 15,
                    "recent_selection_count": 1,
                    "proposal_count": 15,
                    "pareto_contribution_count": 1,
                    "feasible_preservation_count": 3,
                    "recent_expand_selection_count": 1,
                    "recent_expand_feasible_preservation_count": 1,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
            },
        },
    )


def _post_feasible_expand_not_saturated_state() -> ControllerState:
    """Expand has only run 10 evals without frontier add -- should stay in expand."""
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=96,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 28,
                "evaluations_used": 95,
                "evaluations_remaining": 34,
                "feasible_rate": 0.41,
                "first_feasible_eval": 49,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 10,
                "recent_frontier_stagnation_count": 10,
                "last_progress_eval": 86,
                "stable_preservation_streak": 2,
                "new_dominant_violation_family": False,
                "expand_saturation_count": 10,
            },
            "archive_state": {
                "pareto_size": 4,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 10,
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 2,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 11,
                    "recent_selection_count": 1,
                    "proposal_count": 11,
                    "feasible_preservation_count": 3,
                },
                "local_refine": {
                    "selection_count": 12,
                    "recent_selection_count": 2,
                    "proposal_count": 12,
                    "feasible_preservation_count": 4,
                },
                "spread_hottest_cluster": {
                    "selection_count": 10,
                    "recent_selection_count": 2,
                    "proposal_count": 10,
                    "pareto_contribution_count": 1,
                    "feasible_regression_count": 1,
                },
            },
        },
    )


def test_post_feasible_expand_saturated_demotes_to_preserve() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_saturated_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "smooth_high_gradient_band",
        ),
    )

    assert policy.phase == "post_feasible_preserve", (
        f"Expected expand saturation to demote to post_feasible_preserve, got {policy.phase}"
    )
    assert "post_feasible_expand_saturation_demotion" in policy.reason_codes


def test_post_feasible_expand_not_saturated_stays_in_expand() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_not_saturated_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert "post_feasible_expand_saturation_demotion" not in policy.reason_codes


def test_post_feasible_recover_retains_stable_floor_when_semantic_preserver_exists() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_semantic_monopoly_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "spread_hottest_cluster",
            "smooth_high_gradient_band",
            "reduce_local_congestion",
        ),
    )

    assert policy.phase == "post_feasible_recover"
    assert policy.allowed_operator_ids == (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "smooth_high_gradient_band",
    )


def test_post_feasible_recover_keeps_gradient_escape_routes_visible_when_gradient_pressure_is_high() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_gradient_escape_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "smooth_high_gradient_band",
            "reduce_local_congestion",
        ),
    )

    assert policy.phase == "post_feasible_recover"
    assert "smooth_high_gradient_band" in policy.allowed_operator_ids
    assert "reduce_local_congestion" in policy.allowed_operator_ids
    assert "post_feasible_recover_gradient_escape_floor" in policy.reason_codes


def test_post_feasible_recover_restores_positive_budget_guard_family_visibility() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_positive_budget_credit_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
    )

    assert "repair_sink_budget" in policy.allowed_operator_ids
