from __future__ import annotations

import importlib

import pytest

from optimizers.operator_pool.state import ControllerState


def _policy_kernel_module():
    try:
        return importlib.import_module("optimizers.operator_pool.policy_kernel")
    except ModuleNotFoundError as exc:  # pragma: no cover
        pytest.fail(f"Missing reusable policy kernel module: {exc}")


def _assert_snapshot_preserves_support(snapshot, candidate_operator_ids: tuple[str, ...]) -> None:
    assert snapshot.allowed_operator_ids == candidate_operator_ids
    assert snapshot.suppressed_operator_ids == ()
    assert set(snapshot.candidate_annotations) == set(candidate_operator_ids)


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


def _prefeasible_convert_budget_tight_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=33,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 8,
                "evaluations_used": 32,
                "evaluations_remaining": 97,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
            },
            "progress_state": {
                "phase": "prefeasible_stagnation",
                "prefeasible_mode": "convert",
                "first_feasible_found": False,
                "recent_no_progress_count": 4,
                "evaluations_since_near_feasible_improvement": 4,
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 3,
            },
            "domain_regime": {
                "phase": "near_feasible",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.98,
            },
            "prompt_panels": {
                "spatial_panel": {
                    "sink_budget_bucket": "full_sink",
                    "hotspot_inside_sink_window": False,
                },
                "regime_panel": {
                    "phase": "prefeasible_convert",
                    "entry_pressure": "high",
                    "preservation_pressure": "low",
                    "frontier_pressure": "low",
                    "objective_balance": {
                        "balance_pressure": "medium",
                        "preferred_effect": "peak_improve",
                        "stagnant_objectives": ["temperature_max"],
                        "improving_objectives": [],
                    },
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                },
                "global_explore": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                },
                "local_refine": {
                    "selection_count": 4,
                    "recent_selection_count": 1,
                    "proposal_count": 4,
                },
                "repair_sink_budget": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
            },
        },
    )


def _prefeasible_convert_visibility_floor_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=65,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 35,
                "evaluations_used": 64,
                "evaluations_remaining": 135,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
            },
            "progress_state": {
                "phase": "prefeasible_stagnation",
                "prefeasible_mode": "convert",
                "first_feasible_found": False,
                "recent_no_progress_count": 5,
                "evaluations_since_near_feasible_improvement": 5,
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 3,
            },
            "prompt_panels": {
                "spatial_panel": {
                    "sink_budget_bucket": "full_sink",
                    "hotspot_inside_sink_window": False,
                },
                "retrieval_panel": {
                    "positive_match_families": ["hotspot_spread", "sink_retarget"],
                    "visibility_floor_families": ["hotspot_spread", "sink_retarget"],
                    "positive_matches": [
                        {
                            "operator_id": "slide_sink",
                            "route_family": "sink_retarget",
                            "similarity_score": 6,
                        },
                        {
                            "operator_id": "spread_hottest_cluster",
                            "route_family": "hotspot_spread",
                            "similarity_score": 6,
                        },
                    ],
                    "route_family_credit": {
                        "positive_families": ["hotspot_spread"],
                        "negative_families": ["sink_retarget", "stable_global", "stable_local"],
                        "handoff_families": [],
                    },
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 59 + idx,
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
                "native_sbx_pm": {
                    "selection_count": 5,
                    "recent_selection_count": 0,
                    "proposal_count": 5,
                },
                "global_explore": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                },
                "local_refine": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 7,
                    "recent_selection_count": 2,
                    "proposal_count": 7,
                },
                "spread_hottest_cluster": {
                    "selection_count": 6,
                    "recent_selection_count": 2,
                    "proposal_count": 6,
                },
                "repair_sink_budget": {
                    "selection_count": 14,
                    "recent_selection_count": 2,
                    "proposal_count": 14,
                },
                "slide_sink": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
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
def test_policy_snapshot_preserves_cold_start_candidate_support() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "sink_shift",
        "sink_resize",
    )

    snapshot = policy_kernel.build_policy_snapshot(_cold_start_state(), candidates)

    _assert_snapshot_preserves_support(snapshot, candidates)
    assert "cold_start_stable_bootstrap" not in snapshot.reason_codes


def test_policy_snapshot_preserves_prefeasible_candidate_support() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "move_hottest_cluster_toward_sink",
        "spread_hottest_cluster",
    )

    snapshot = policy_kernel.build_policy_snapshot(_prefeasible_family_collapse_state(), candidates)

    _assert_snapshot_preserves_support(snapshot, candidates)
    assert "prefeasible_speculative_family_collapse" in snapshot.reason_codes


def test_policy_snapshot_preserves_post_feasible_candidate_support() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "local_refine",
        "hotspot_pull_toward_sink",
        "hotspot_spread",
        "sink_retarget",
    )

    snapshot = policy_kernel.build_policy_snapshot(_post_feasible_expand_state(), candidates)

    _assert_snapshot_preserves_support(snapshot, candidates)
    assert snapshot.phase.startswith("post_feasible")


def test_policy_snapshot_demotes_expand_when_pde_feasible_rate_is_low_and_recover_pressure_high() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "sink_shift",
        "sink_resize",
        "component_block_translate_2_4",
    )
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=84,
        parent_count=2,
        vector_size=32,
        metadata={
            "run_state": {
                "first_feasible_eval": 14,
                "feasible_rate": 0.32,
            },
            "archive_state": {
                "pareto_size": 1,
                "recent_feasible_regression_count": 1,
                "recent_feasible_preservation_count": 0,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "first_feasible_found": True,
                "post_feasible_mode": "expand",
                "preserve_dwell_remaining": 0,
                "recent_frontier_stagnation_count": 12,
                "recover_reentry_pressure": "high",
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 5,
                "diversity_deficit_level": "high",
            },
            "operator_summary": {},
            "recent_decisions": [],
        },
    )

    snapshot = policy_kernel.build_policy_snapshot(state, candidates)

    assert snapshot.phase == "post_feasible_recover"
    _assert_snapshot_preserves_support(snapshot, candidates)
    assert "post_feasible_expand_low_pde_feasibility_recover" in snapshot.reason_codes


def _objective_balance_state(*, preferred_effect: str) -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=90,
        parent_count=2,
        vector_size=32,
        metadata={
            "prompt_panels": {
                "regime_panel": {
                    "objective_balance": {
                        "balance_pressure": "high",
                        "preferred_effect": preferred_effect,
                        "stagnant_objectives": ["temperature_max", "gradient_rms"],
                        "improving_objectives": [],
                    }
                },
                "spatial_panel": {
                    "nearest_neighbor_gap_min": 0.05,
                    "hottest_cluster_compactness": 0.09,
                    "hotspot_inside_sink_window": False,
                },
            }
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


def _recover_release_ready_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=103,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 32,
                "evaluations_used": 102,
                "evaluations_remaining": 27,
                "feasible_rate": 0.45,
                "first_feasible_eval": 49,
            },
            "archive_state": {
                "recent_feasible_regression_count": 2,
                "recent_feasible_preservation_count": 1,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recover_exit_ready": False,
                "recover_release_ready": True,
                "recover_pressure_level": "medium",
                "preserve_dwell_count": 1,
                "preserve_dwell_remaining": 0,
                "recover_reentry_pressure": "medium",
                "recent_no_progress_count": 1,
                "recent_frontier_stagnation_count": 1,
                "last_progress_eval": 101,
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
                "global_explore": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                    "feasible_preservation_count": 1,
                },
            },
        },
    )


def _preserve_dwell_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=103,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 32,
                "evaluations_used": 102,
                "evaluations_remaining": 27,
                "feasible_rate": 0.45,
                "first_feasible_eval": 49,
            },
            "archive_state": {
                "recent_feasible_regression_count": 1,
                "recent_feasible_preservation_count": 1,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recover_exit_ready": False,
                "recover_pressure_level": "medium",
                "preserve_dwell_count": 1,
                "preserve_dwell_remaining": 2,
                "recover_reentry_pressure": "medium",
                "recent_no_progress_count": 1,
                "recent_frontier_stagnation_count": 1,
                "last_progress_eval": 101,
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
            },
        },
    )


def _post_feasible_preserve_diversity_deficit_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=104,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 33,
                "evaluations_used": 103,
                "evaluations_remaining": 26,
                "feasible_rate": 0.46,
                "first_feasible_eval": 49,
            },
            "archive_state": {
                "pareto_size": 2,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 6,
                "recent_feasible_regression_count": 1,
                "recent_feasible_preservation_count": 1,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "preserve",
                "recover_exit_ready": True,
                "recover_release_ready": True,
                "recover_pressure_level": "low",
                "preserve_dwell_count": 3,
                "preserve_dwell_remaining": 0,
                "recover_reentry_pressure": "low",
                "recent_no_progress_count": 3,
                "recent_frontier_stagnation_count": 6,
                "last_progress_eval": 101,
                "diversity_deficit_level": "medium",
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
                    "feasible_preservation_count": 2,
                },
                "spread_hottest_cluster": {
                    "selection_count": 8,
                    "recent_selection_count": 2,
                    "proposal_count": 8,
                    "pareto_contribution_count": 1,
                    "recent_expand_selection_count": 1,
                    "recent_expand_feasible_preservation_count": 1,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
                "reduce_local_congestion": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                    "pareto_contribution_count": 1,
                    "recent_expand_selection_count": 1,
                    "recent_expand_feasible_preservation_count": 1,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
            },
        },
    )


def _post_feasible_recover_direct_expand_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=162,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 58,
                "evaluations_used": 161,
                "evaluations_remaining": 40,
                "feasible_rate": 1.0,
                "first_feasible_eval": 21,
            },
            "archive_state": {
                "pareto_size": 2,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 7,
                "recent_feasible_regression_count": 3,
                "recent_feasible_preservation_count": 0,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recover_exit_ready": False,
                "recover_release_ready": False,
                "recover_pressure_level": "high",
                "preserve_dwell_count": 0,
                "preserve_dwell_remaining": 0,
                "recover_reentry_pressure": "high",
                "recent_no_progress_count": 7,
                "recent_frontier_stagnation_count": 7,
                "last_progress_eval": 154,
                "diversity_deficit_level": "medium",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_recover",
                    "preservation_pressure": "high",
                    "frontier_pressure": "medium",
                    "recover_exit_ready": False,
                    "recover_release_ready": False,
                    "recover_reentry_pressure": "high",
                    "diversity_deficit_level": "medium",
                },
                "retrieval_panel": {
                    "positive_match_families": ["stable_local"],
                    "visibility_floor_families": ["stable_local"],
                    "positive_matches": [
                        {
                            "operator_id": "local_refine",
                            "route_family": "stable_local",
                            "similarity_score": 6,
                        }
                    ],
                    "route_family_credit": {
                        "positive_families": [],
                        "negative_families": ["stable_local", "sink_retarget"],
                        "handoff_families": [],
                    },
                },
                "operator_panel": {
                    "native_sbx_pm": {
                        "applicability": "medium",
                        "expected_peak_effect": "neutral",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                    "local_refine": {
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                    "spread_hottest_cluster": {
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "medium",
                        "recent_regression_risk": "medium",
                    },
                    "reduce_local_congestion": {
                        "applicability": "high",
                        "expected_peak_effect": "neutral",
                        "expected_gradient_effect": "improve",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 10,
                    "recent_selection_count": 1,
                    "proposal_count": 10,
                    "feasible_preservation_count": 3,
                },
                "local_refine": {
                    "selection_count": 12,
                    "recent_selection_count": 2,
                    "proposal_count": 12,
                    "feasible_preservation_count": 4,
                },
                "spread_hottest_cluster": {
                    "selection_count": 8,
                    "recent_selection_count": 1,
                    "proposal_count": 8,
                    "pareto_contribution_count": 1,
                },
                "reduce_local_congestion": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                    "pareto_contribution_count": 1,
                },
            },
        },
    )


def _post_feasible_preserve_frontier_pressure_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=104,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 33,
                "evaluations_used": 103,
                "evaluations_remaining": 26,
                "feasible_rate": 0.46,
                "first_feasible_eval": 49,
            },
            "archive_state": {
                "pareto_size": 1,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 6,
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 3,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "preserve",
                "recover_exit_ready": False,
                "recover_pressure_level": "low",
                "preserve_dwell_count": 3,
                "preserve_dwell_remaining": 0,
                "recover_reentry_pressure": "low",
                "recent_no_progress_count": 3,
                "recent_frontier_stagnation_count": 6,
                "last_progress_eval": 101,
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
                "spread_hottest_cluster": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
            },
        },
    )


def _post_feasible_preserve_unproven_assisted_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=10,
        evaluation_index=198,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 168,
                "evaluations_used": 197,
                "evaluations_remaining": 3,
                "feasible_rate": 0.27,
                "first_feasible_eval": 13,
            },
            "archive_state": {
                "pareto_size": 2,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 140,
                "recent_feasible_regression_count": 2,
                "recent_feasible_preservation_count": 0,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "preserve",
                "preserve_dwell_remaining": 1,
                "recover_release_ready": True,
                "recover_exit_ready": True,
                "recent_no_progress_count": 76,
                "recent_frontier_stagnation_count": 76,
                "diversity_deficit_level": "medium",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_preserve",
                    "preservation_pressure": "high",
                    "frontier_pressure": "medium",
                    "objective_balance": {
                        "balance_pressure": "high",
                        "preferred_effect": "gradient_improve",
                        "stagnant_objectives": ["gradient_rms"],
                        "improving_objectives": ["temperature_max"],
                    },
                },
                "spatial_panel": {
                    "nearest_neighbor_gap_min": 0.107,
                    "hottest_cluster_compactness": 0.27,
                    "hotspot_inside_sink_window": True,
                },
                "retrieval_panel": {
                    "positive_match_families": ["stable_local", "stable_global"],
                    "visibility_floor_families": ["stable_local", "stable_global"],
                    "positive_matches": [
                        {
                            "operator_id": "component_jitter_1",
                            "route_family": "stable_local",
                            "similarity_score": 6,
                        },
                        {
                            "operator_id": "component_relocate_1",
                            "route_family": "stable_global",
                            "similarity_score": 6,
                        },
                    ],
                    "route_family_credit": {
                        "positive_families": ["stable_local", "stable_global"],
                        "negative_families": [],
                        "handoff_families": ["stable_local"],
                    },
                },
            },
            "operator_summary": {
                "vector_sbx_pm": {
                    "selection_count": 26,
                    "recent_selection_count": 0,
                    "proposal_count": 26,
                    "feasible_entry_count": 4,
                    "feasible_regression_count": 6,
                    "post_feasible_success_count": 7,
                    "post_feasible_selection_count": 15,
                },
                "component_jitter_1": {
                    "selection_count": 34,
                    "recent_selection_count": 0,
                    "proposal_count": 34,
                    "feasible_entry_count": 1,
                    "feasible_preservation_count": 4,
                    "feasible_regression_count": 1,
                    "pareto_contribution_count": 3,
                    "post_feasible_success_count": 13,
                    "post_feasible_selection_count": 34,
                },
                "component_relocate_1": {
                    "selection_count": 15,
                    "recent_selection_count": 0,
                    "proposal_count": 15,
                    "feasible_entry_count": 1,
                    "feasible_preservation_count": 1,
                    "feasible_regression_count": 4,
                    "post_feasible_success_count": 7,
                    "post_feasible_selection_count": 15,
                },
                "hotspot_spread": {
                    "selection_count": 40,
                    "recent_selection_count": 10,
                    "proposal_count": 40,
                    "post_feasible_success_count": 5,
                    "post_feasible_selection_count": 39,
                    "post_feasible_thermal_infeasible_count": 34,
                },
                "gradient_band_smooth": {
                    "selection_count": 0,
                    "recent_selection_count": 0,
                    "proposal_count": 0,
                },
                "congestion_relief": {
                    "selection_count": 20,
                    "recent_selection_count": 7,
                    "proposal_count": 20,
                    "post_feasible_success_count": 2,
                    "post_feasible_selection_count": 20,
                    "post_feasible_thermal_infeasible_count": 18,
                },
                "layout_rebalance": {
                    "selection_count": 41,
                    "recent_selection_count": 7,
                    "proposal_count": 41,
                    "post_feasible_success_count": 8,
                    "post_feasible_selection_count": 41,
                    "post_feasible_thermal_infeasible_count": 33,
                },
            },
        },
    )


def _post_feasible_expand_diversity_floor_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=110,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 36,
                "evaluations_used": 109,
                "evaluations_remaining": 20,
                "feasible_rate": 0.47,
                "first_feasible_eval": 49,
            },
            "archive_state": {
                "pareto_size": 1,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 8,
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 4,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 4,
                "recent_frontier_stagnation_count": 8,
                "last_progress_eval": 106,
                "expand_saturation_count": 8,
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
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
                "reduce_local_congestion": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
                "rebalance_layout": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
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


def _post_feasible_expand_low_success_gradient_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=10,
        evaluation_index=194,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 160,
                "evaluations_used": 193,
                "evaluations_remaining": 7,
                "feasible_rate": 0.36,
                "first_feasible_eval": 13,
            },
            "archive_state": {
                "pareto_size": 1,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 28,
                "recent_feasible_regression_count": 2,
                "recent_feasible_preservation_count": 1,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 18,
                "recent_frontier_stagnation_count": 18,
                "diversity_deficit_level": "medium",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "preservation_pressure": "medium",
                    "frontier_pressure": "medium",
                    "objective_balance": {
                        "balance_pressure": "high",
                        "preferred_effect": "gradient_improve",
                        "stagnant_objectives": ["gradient_rms"],
                        "improving_objectives": ["temperature_max"],
                    },
                },
                "spatial_panel": {
                    "nearest_neighbor_gap_min": 0.08,
                    "hottest_cluster_compactness": 0.10,
                    "hotspot_inside_sink_window": True,
                },
            },
            "operator_summary": {
                "vector_sbx_pm": {
                    "selection_count": 34,
                    "recent_selection_count": 2,
                    "proposal_count": 34,
                    "feasible_preservation_count": 5,
                    "post_feasible_success_count": 5,
                    "post_feasible_selection_count": 19,
                },
                "component_jitter_1": {
                    "selection_count": 12,
                    "recent_selection_count": 0,
                    "proposal_count": 12,
                    "feasible_preservation_count": 4,
                    "post_feasible_success_count": 9,
                    "post_feasible_selection_count": 12,
                },
                "gradient_band_smooth": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                    "recent_expand_selection_count": 0,
                },
                "congestion_relief": {
                    "selection_count": 26,
                    "recent_selection_count": 6,
                    "proposal_count": 26,
                    "recent_expand_selection_count": 10,
                    "recent_expand_feasible_preservation_count": 0,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 0,
                    "post_feasible_success_count": 6,
                    "post_feasible_selection_count": 26,
                    "post_feasible_thermal_infeasible_count": 20,
                },
                "sink_retarget": {
                    "selection_count": 20,
                    "recent_selection_count": 4,
                    "proposal_count": 20,
                    "post_feasible_success_count": 14,
                    "post_feasible_selection_count": 20,
                },
            },
        },
    )


def _post_feasible_expand_gradient_sink_route_dominance_state() -> ControllerState:
    state = _post_feasible_expand_low_success_gradient_state()
    state.metadata["recent_decisions"] = [
        {
            "evaluation_index": 180 + idx,
            "selected_operator_id": operator_id,
            "fallback_used": False,
            "llm_valid": True,
        }
        for idx, operator_id in enumerate(
            (
                "sink_retarget",
                "sink_retarget",
                "sink_retarget",
                "sink_retarget",
                "congestion_relief",
                "vector_sbx_pm",
            )
        )
    ]
    state.metadata["operator_summary"]["sink_retarget"].update(
        {
            "recent_expand_selection_count": 6,
            "recent_expand_feasible_preservation_count": 4,
            "recent_expand_feasible_regression_count": 0,
            "recent_expand_frontier_add_count": 0,
        }
    )
    return state


def _post_feasible_expand_generation_probe_budget_state() -> ControllerState:
    state = _post_feasible_expand_low_success_gradient_state()
    state.metadata["recent_decisions"] = [
        {
            "evaluation_index": 180 + idx,
            "selected_operator_id": operator_id,
            "fallback_used": False,
            "llm_valid": True,
            "generation_local": True,
        }
        for idx, operator_id in enumerate(
            (
                "hotspot_spread",
                "hotspot_pull_toward_sink",
                "congestion_relief",
                "layout_rebalance",
            )
        )
    ]
    state.metadata["generation_local_memory"] = {
        "accepted_count": 4,
        "target_offsprings": 20,
        "accepted_share": 0.2,
        "dominant_operator_id": "hotspot_spread",
        "dominant_operator_count": 1,
        "dominant_operator_share": 0.25,
        "operator_counts": {
            "hotspot_spread": {"accepted_count": 1, "accepted_share": 0.25},
            "hotspot_pull_toward_sink": {"accepted_count": 1, "accepted_share": 0.25},
            "congestion_relief": {"accepted_count": 1, "accepted_share": 0.25},
            "layout_rebalance": {"accepted_count": 1, "accepted_share": 0.25},
        },
        "route_family_counts": {
            "hotspot_spread": {"accepted_count": 1, "accepted_share": 0.25},
            "sink_retarget": {"accepted_count": 1, "accepted_share": 0.25},
            "congestion_relief": {"accepted_count": 1, "accepted_share": 0.25},
            "layout_rebalance": {"accepted_count": 1, "accepted_share": 0.25},
        },
        "uncredited_custom_count": 4,
    }
    return state


def _post_feasible_expand_peak_budget_fill_probe_state() -> ControllerState:
    state = _post_feasible_expand_generation_probe_budget_state()
    state.metadata["run_state"].update(
        {
            "sink_budget_utilization": 0.965,
            "objective_extremes": {
                "min_peak_temperature": {
                    "evaluation_index": 102,
                    "sink_span": 0.3088,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.99,
                        "minimize_temperature_gradient_rms": 15.61,
                    },
                },
                "min_temperature_gradient_rms": {
                    "evaluation_index": 102,
                    "sink_span": 0.3088,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.99,
                        "minimize_temperature_gradient_rms": 15.61,
                    },
                },
            },
        }
    )
    state.metadata["archive_state"].update(
        {
            "pareto_size": 1,
            "recent_frontier_add_count": 0,
            "evaluations_since_frontier_add": 18,
        }
    )
    state.metadata["progress_state"].update(
        {
            "diversity_deficit_level": "high",
            "recent_frontier_stagnation_count": 18,
        }
    )
    state.metadata["prompt_panels"]["run_panel"] = {
        "pareto_size": 1,
        "sink_budget_utilization": 0.965,
        "objective_extremes": state.metadata["run_state"]["objective_extremes"],
    }
    state.metadata["prompt_panels"]["regime_panel"]["objective_balance"] = {
        "balance_pressure": "high",
        "preferred_effect": "peak_improve",
        "stagnant_objectives": ["temperature_max"],
        "improving_objectives": ["gradient_rms"],
        "balance_reason": "frontier_endpoint_peak_budget_fill",
    }
    return state


def _post_feasible_expand_generation_route_probe_budget_state() -> ControllerState:
    state = _post_feasible_expand_low_success_gradient_state()
    state.metadata["recent_decisions"] = [
        {
            "evaluation_index": 180 + idx,
            "selected_operator_id": operator_id,
            "fallback_used": False,
            "llm_valid": True,
            "generation_local": True,
        }
        for idx, operator_id in enumerate(
            (
                "gradient_band_smooth",
                "congestion_relief",
                "gradient_band_smooth",
            )
        )
    ]
    state.metadata["generation_local_memory"] = {
        "accepted_count": 3,
        "target_offsprings": 20,
        "accepted_share": 0.15,
        "operator_counts": {
            "gradient_band_smooth": {"accepted_count": 2, "accepted_share": 2.0 / 3.0},
            "congestion_relief": {"accepted_count": 1, "accepted_share": 1.0 / 3.0},
        },
        "route_family_counts": {
            "congestion_relief": {"accepted_count": 3, "accepted_share": 1.0},
        },
        "uncredited_custom_count": 3,
    }
    return state


def _post_feasible_expand_generation_probe_budget_with_credit_state() -> ControllerState:
    state = _post_feasible_expand_generation_probe_budget_state()
    state.metadata["operator_summary"]["sink_retarget"].update(
        {
            "pareto_contribution_count": 1,
            "recent_expand_selection_count": 4,
            "recent_expand_feasible_preservation_count": 1,
            "recent_expand_feasible_regression_count": 0,
            "recent_expand_frontier_add_count": 1,
            "post_feasible_success_count": 3,
            "post_feasible_selection_count": 4,
        }
    )
    return state


def _post_feasible_expand_peak_improved_gradient_polish_state() -> ControllerState:
    state = _post_feasible_expand_low_success_gradient_state()
    state.metadata["archive_state"].update(
        {
            "pareto_size": 1,
            "recent_frontier_add_count": 0,
            "evaluations_since_frontier_add": 34,
        }
    )
    state.metadata["progress_state"].update(
        {
            "recent_frontier_stagnation_count": 34,
            "post_feasible_mode": "expand",
        }
    )
    state.metadata["prompt_panels"]["regime_panel"]["objective_balance"] = {
        "balance_pressure": "high",
        "preferred_effect": "gradient_improve",
        "stagnant_objectives": ["gradient_rms"],
        "improving_objectives": ["temperature_max"],
    }
    state.metadata["operator_summary"]["vector_sbx_pm"].update(
        {
            "post_feasible_success_count": 10,
            "post_feasible_selection_count": 19,
        }
    )
    state.metadata["recent_decisions"] = [
        {
            "evaluation_index": 180 + idx,
            "selected_operator_id": operator_id,
            "fallback_used": False,
            "llm_valid": True,
        }
        for idx, operator_id in enumerate(
            (
                "vector_sbx_pm",
                "component_swap_2",
                "vector_sbx_pm",
                "component_swap_2",
                "vector_sbx_pm",
                "component_swap_2",
            )
        )
    ]
    state.metadata["operator_summary"]["component_swap_2"] = {
        "selection_count": 64,
        "recent_selection_count": 5,
        "proposal_count": 64,
        "feasible_preservation_count": 20,
        "pareto_contribution_count": 1,
        "frontier_novelty_count": 1,
        "post_feasible_success_count": 42,
        "post_feasible_selection_count": 64,
    }
    state.metadata["operator_summary"]["component_relocate_1"] = {
        "selection_count": 8,
        "recent_selection_count": 0,
        "proposal_count": 8,
        "feasible_preservation_count": 2,
        "post_feasible_success_count": 2,
        "post_feasible_selection_count": 8,
    }
    return state


def _post_feasible_expand_peak_improved_uncredited_broad_state() -> ControllerState:
    state = _post_feasible_expand_peak_improved_gradient_polish_state()
    state.metadata["operator_summary"]["component_swap_2"].update(
        {
            "pareto_contribution_count": 0,
            "frontier_novelty_count": 0,
            "recent_expand_frontier_add_count": 0,
            "post_feasible_avg_objective_delta": 0.12,
        }
    )
    return state


def _post_feasible_expand_peak_improved_without_polish_alternative_state() -> ControllerState:
    state = _post_feasible_expand_peak_improved_gradient_polish_state()
    state.metadata["operator_summary"].pop("component_jitter_1", None)
    state.metadata["operator_summary"].pop("component_relocate_1", None)
    return state


def _post_feasible_preserve_plateau_sink_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=10,
        evaluation_index=190,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 151,
                "evaluations_used": 189,
                "evaluations_remaining": 11,
                "feasible_rate": 0.41,
                "first_feasible_eval": 23,
            },
            "archive_state": {
                "pareto_size": 2,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 38,
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 4,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "preserve",
                "preserve_dwell_count": 8,
                "preserve_dwell_remaining": 1,
                "recent_no_progress_count": 24,
                "recent_frontier_stagnation_count": 24,
                "diversity_deficit_level": "medium",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_preserve",
                    "preservation_pressure": "high",
                    "frontier_pressure": "medium",
                    "objective_balance": {
                        "balance_pressure": "high",
                        "preferred_effect": "gradient_improve",
                        "stagnant_objectives": ["gradient_rms"],
                        "improving_objectives": ["temperature_max"],
                    },
                },
                "spatial_panel": {
                    "nearest_neighbor_gap_min": 0.08,
                    "hottest_cluster_compactness": 0.10,
                    "hotspot_inside_sink_window": True,
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 180 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "sink_shift",
                        "sink_shift",
                        "anchored_component_jitter",
                        "sink_shift",
                        "vector_sbx_pm",
                        "sink_shift",
                        "anchored_component_jitter",
                        "sink_shift",
                    )
                )
            ],
            "operator_summary": {
                "vector_sbx_pm": {
                    "selection_count": 29,
                    "recent_selection_count": 1,
                    "proposal_count": 29,
                    "feasible_preservation_count": 4,
                    "feasible_regression_count": 6,
                    "pareto_contribution_count": 1,
                    "frontier_novelty_count": 1,
                    "post_feasible_success_count": 9,
                    "post_feasible_selection_count": 29,
                },
                "component_jitter_1": {
                    "selection_count": 10,
                    "recent_selection_count": 0,
                    "proposal_count": 10,
                    "feasible_preservation_count": 3,
                    "post_feasible_success_count": 5,
                    "post_feasible_selection_count": 10,
                },
                "component_swap_2": {
                    "selection_count": 9,
                    "recent_selection_count": 0,
                    "proposal_count": 9,
                    "feasible_preservation_count": 5,
                    "pareto_contribution_count": 1,
                    "frontier_novelty_count": 1,
                    "post_feasible_success_count": 5,
                    "post_feasible_selection_count": 9,
                },
                "sink_shift": {
                    "selection_count": 45,
                    "recent_selection_count": 5,
                    "proposal_count": 45,
                    "feasible_preservation_count": 34,
                    "feasible_regression_count": 0,
                    "post_feasible_success_count": 40,
                    "post_feasible_selection_count": 45,
                    "post_feasible_avg_objective_delta": 0.06,
                },
                "anchored_component_jitter": {
                    "selection_count": 16,
                    "recent_selection_count": 2,
                    "proposal_count": 16,
                    "feasible_regression_count": 10,
                    "post_feasible_success_count": 3,
                    "post_feasible_selection_count": 16,
                    "post_feasible_thermal_infeasible_count": 12,
                },
                "sink_resize": {
                    "selection_count": 6,
                    "recent_selection_count": 0,
                    "proposal_count": 6,
                    "feasible_preservation_count": 2,
                    "post_feasible_success_count": 3,
                    "post_feasible_selection_count": 6,
                },
            },
        },
    )


def _post_feasible_preserve_low_success_stable_without_alternative_state() -> ControllerState:
    state = _post_feasible_preserve_plateau_sink_state()
    state.metadata["recent_decisions"] = []
    return state


def _post_feasible_preserve_sink_retarget_plateau_state() -> ControllerState:
    state = _post_feasible_preserve_plateau_sink_state()
    state.metadata["prompt_panels"]["regime_panel"]["objective_balance"] = {
        "balance_pressure": "high",
        "preferred_effect": "peak_improve",
        "stagnant_objectives": ["temperature_max"],
        "improving_objectives": ["gradient_rms"],
    }
    state.metadata["recent_decisions"] = [
        {
            "evaluation_index": 180 + idx,
            "selected_operator_id": operator_id,
            "fallback_used": False,
            "llm_valid": True,
        }
        for idx, operator_id in enumerate(
            (
                "sink_retarget",
                "sink_retarget",
                "vector_sbx_pm",
                "sink_retarget",
                "sink_retarget",
                "sink_retarget",
                "component_jitter_1",
                "sink_retarget",
            )
        )
    ]
    state.metadata["operator_summary"]["sink_retarget"] = {
        "selection_count": 32,
        "recent_selection_count": 6,
        "proposal_count": 32,
        "feasible_preservation_count": 18,
        "feasible_regression_count": 0,
        "pareto_contribution_count": 0,
        "frontier_novelty_count": 0,
        "post_feasible_success_count": 22,
        "post_feasible_selection_count": 32,
        "post_feasible_avg_objective_delta": 0.04,
    }
    return state


def _post_feasible_preserve_peak_budget_fill_plateau_state() -> ControllerState:
    state = _post_feasible_preserve_plateau_sink_state()
    state.metadata["run_state"].update(
        {
            "sink_budget_utilization": 0.965,
            "objective_extremes": {
                "min_peak_temperature": {
                    "evaluation_index": 153,
                    "sink_span": 0.3088,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.63,
                        "minimize_temperature_gradient_rms": 15.46,
                    },
                },
                "min_temperature_gradient_rms": {
                    "evaluation_index": 153,
                    "sink_span": 0.3088,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.63,
                        "minimize_temperature_gradient_rms": 15.46,
                    },
                },
            },
        }
    )
    state.metadata["archive_state"]["pareto_size"] = 1
    state.metadata["progress_state"]["diversity_deficit_level"] = "high"
    state.metadata["prompt_panels"]["run_panel"] = {
        "pareto_size": 1,
        "sink_budget_utilization": 0.965,
        "objective_extremes": state.metadata["run_state"]["objective_extremes"],
    }
    state.metadata["prompt_panels"]["regime_panel"]["objective_balance"] = {
        "balance_pressure": "high",
        "preferred_effect": "peak_improve",
        "stagnant_objectives": ["temperature_max"],
        "improving_objectives": ["gradient_rms"],
        "balance_reason": "frontier_endpoint_peak_budget_fill",
    }
    state.metadata["recent_decisions"] = [
        {
            "evaluation_index": 180 + idx,
            "selected_operator_id": operator_id,
            "fallback_used": False,
            "llm_valid": True,
        }
        for idx, operator_id in enumerate(
            (
                "sink_resize",
                "sink_shift",
                "sink_resize",
                "sink_shift",
                "sink_resize",
                "sink_shift",
                "sink_resize",
                "sink_shift",
            )
        )
    ]
    return state


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


def _post_feasible_recover_positive_stable_local_credit_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=95,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 28,
                "evaluations_used": 94,
                "evaluations_remaining": 35,
                "feasible_rate": 0.42,
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
                        "positive_families": ["stable_local"],
                        "negative_families": ["stable_local"],
                        "handoff_families": ["stable_local"],
                    },
                    "stable_local_handoff_active": True,
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 14,
                    "recent_selection_count": 1,
                    "proposal_count": 14,
                    "feasible_preservation_count": 5,
                    "feasible_regression_count": 1,
                },
                "global_explore": {
                    "selection_count": 9,
                    "recent_selection_count": 1,
                    "proposal_count": 9,
                    "feasible_preservation_count": 2,
                },
                "local_refine": {
                    "selection_count": 16,
                    "recent_selection_count": 2,
                    "proposal_count": 16,
                    "feasible_preservation_count": 6,
                    "feasible_regression_count": 1,
                },
            },
        },
    )


def _post_feasible_recover_visibility_floor_state() -> ControllerState:
    state = _post_feasible_recover_positive_stable_local_credit_state()
    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    retrieval_panel["route_family_credit"] = {
        "positive_families": [],
        "negative_families": ["stable_local"],
        "handoff_families": [],
    }
    retrieval_panel["stable_local_handoff_active"] = False
    retrieval_panel["positive_matches"] = [
        {
            "operator_id": "local_refine",
            "route_family": "stable_local",
            "similarity_score": 6,
        }
    ]
    retrieval_panel["positive_match_families"] = ["stable_local"]
    retrieval_panel["visibility_floor_families"] = ["stable_local"]
    return state


def _post_feasible_expand_visibility_floor_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=7,
        evaluation_index=122,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 90,
                "evaluations_used": 121,
                "evaluations_remaining": 14,
                "feasible_rate": 0.16,
                "first_feasible_eval": 42,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 4,
                "recent_frontier_stagnation_count": 6,
                "diversity_deficit_level": "high",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "preservation_pressure": "high",
                    "frontier_pressure": "medium",
                    "recover_release_ready": False,
                    "recover_reentry_pressure": "high",
                    "diversity_deficit_level": "high",
                    "objective_balance": {
                        "balance_pressure": "medium",
                        "preferred_effect": "balanced",
                        "stagnant_objectives": ["temperature_max", "gradient_rms"],
                        "improving_objectives": [],
                    },
                },
                "spatial_panel": {
                    "nearest_neighbor_gap_min": 0.06,
                    "hottest_cluster_compactness": 0.09,
                    "hotspot_inside_sink_window": True,
                },
                "retrieval_panel": {
                    "positive_match_families": ["congestion_relief", "sink_retarget", "stable_local"],
                    "visibility_floor_families": ["congestion_relief", "sink_retarget", "stable_local"],
                    "positive_matches": [
                        {
                            "operator_id": "reduce_local_congestion",
                            "route_family": "congestion_relief",
                            "similarity_score": 5,
                        },
                        {
                            "operator_id": "move_hottest_cluster_toward_sink",
                            "route_family": "sink_retarget",
                            "similarity_score": 5,
                        },
                        {
                            "operator_id": "local_refine",
                            "route_family": "stable_local",
                            "similarity_score": 5,
                        },
                    ],
                    "route_family_credit": {
                        "positive_families": [],
                        "negative_families": ["congestion_relief", "sink_retarget", "stable_local"],
                        "handoff_families": ["stable_local"],
                    },
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 116 + idx,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for idx, operator_id in enumerate(
                    (
                        "reduce_local_congestion",
                        "reduce_local_congestion",
                        "reduce_local_congestion",
                        "reduce_local_congestion",
                        "reduce_local_congestion",
                        "rebalance_layout",
                    )
                )
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 15,
                    "proposal_count": 15,
                    "feasible_preservation_count": 1,
                    "feasible_regression_count": 5,
                    "pareto_contribution_count": 1,
                },
                "global_explore": {
                    "selection_count": 5,
                    "proposal_count": 5,
                },
                "local_refine": {
                    "selection_count": 18,
                    "proposal_count": 18,
                    "feasible_preservation_count": 1,
                    "feasible_regression_count": 4,
                    "pareto_contribution_count": 1,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 7,
                    "proposal_count": 7,
                    "feasible_regression_count": 1,
                    "pareto_contribution_count": 1,
                    "post_feasible_avg_objective_delta": -0.1,
                },
                "smooth_high_gradient_band": {
                    "selection_count": 6,
                    "proposal_count": 6,
                    "feasible_regression_count": 2,
                    "pareto_contribution_count": 0,
                },
                "reduce_local_congestion": {
                    "selection_count": 9,
                    "proposal_count": 9,
                    "feasible_regression_count": 6,
                    "pareto_contribution_count": 0,
                },
                "rebalance_layout": {
                    "selection_count": 9,
                    "proposal_count": 9,
                    "feasible_regression_count": 2,
                    "pareto_contribution_count": 1,
                    "post_feasible_avg_objective_delta": -0.01,
                },
            },
        },
    )


def test_cold_start_bootstraps_only_stable_semantic_families() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "move_hottest_cluster_toward_sink",
    )

    policy = policy_kernel.build_policy_snapshot(_cold_start_state(), candidates)

    assert policy.phase == "cold_start"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "cold_start_stable_bootstrap" in policy.reason_codes
    assert policy.candidate_annotations["native_sbx_pm"]["prefeasible_role"] == "stable_baseline"
    assert policy.candidate_annotations["global_explore"]["prefeasible_role"] == "stable_global"
    assert policy.candidate_annotations["local_refine"]["prefeasible_role"] == "stable_local"
    assert policy.candidate_annotations["move_hottest_cluster_toward_sink"]["prefeasible_role"] == "speculative_custom"


def test_prefeasible_family_collapse_suppresses_overused_semantic_custom_family() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "local_refine",
        "move_hottest_cluster_toward_sink",
        "spread_hottest_cluster",
    )

    policy = policy_kernel.build_policy_snapshot(_prefeasible_family_collapse_state(), candidates)

    _assert_snapshot_preserves_support(policy, candidates)
    assert "prefeasible_speculative_family_collapse" in policy.reason_codes
    assert policy.candidate_annotations["move_hottest_cluster_toward_sink"]["prefeasible_role"] == "speculative_custom"
    assert policy.candidate_annotations["spread_hottest_cluster"]["prefeasible_role"] == "speculative_custom"


def test_prefeasible_reset_biases_back_to_stable_semantic_roles() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "move_hottest_cluster_toward_sink",
        "repair_sink_budget",
    )

    policy = policy_kernel.build_policy_snapshot(_prefeasible_reset_state(), candidates)

    assert policy.reset_active is True
    _assert_snapshot_preserves_support(policy, candidates)
    assert "prefeasible_forced_reset" in policy.reason_codes
    assert policy.candidate_annotations["native_sbx_pm"]["prefeasible_role"] == "stable_baseline"
    assert policy.candidate_annotations["global_explore"]["prefeasible_role"] == "stable_global"
    assert policy.candidate_annotations["local_refine"]["prefeasible_role"] == "stable_local"


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


def test_balance_escape_candidates_use_active_assisted_operator_ids() -> None:
    policy_kernel = _policy_kernel_module()

    peak_escape = policy_kernel._peak_balance_escape_candidates(
        _objective_balance_state(preferred_effect="peak_improve"),
        "post_feasible_expand",
        ("hotspot_pull_toward_sink", "sink_retarget", "component_jitter_1"),
    )
    gradient_escape = policy_kernel._gradient_balance_escape_candidates(
        _objective_balance_state(preferred_effect="gradient_improve"),
        "post_feasible_expand",
        ("hotspot_spread", "gradient_band_smooth", "congestion_relief", "layout_rebalance"),
    )

    assert peak_escape == ("hotspot_pull_toward_sink", "sink_retarget")
    assert gradient_escape == (
        "hotspot_spread",
        "gradient_band_smooth",
        "congestion_relief",
        "layout_rebalance",
    )


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


def test_detect_search_phase_keeps_preserve_live_during_dwell_window() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _preserve_dwell_state(),
        (
            "native_sbx_pm",
            "local_refine",
        ),
    )

    assert policy.phase == "post_feasible_preserve"


def test_preserve_state_promotes_to_expand_when_frontier_pressure_stays_high() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_frontier_pressure_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
        ),
    )

    assert policy.phase == "post_feasible_expand"


def test_preserve_state_promotes_to_expand_when_diversity_deficit_is_medium_and_regression_is_bounded() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_diversity_deficit_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "reduce_local_congestion",
        ),
    )

    assert policy.phase == "post_feasible_expand"


def test_recover_state_promotes_directly_to_expand_when_release_evidence_is_live_and_diversity_deficit_is_medium() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_direct_expand_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "reduce_local_congestion",
        ),
    )

    assert policy.phase == "post_feasible_expand"


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


def test_detect_search_phase_uses_recover_release_ready_even_when_reentry_pressure_is_medium() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _recover_release_ready_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "global_explore",
        ),
    )

    assert policy.phase == "post_feasible_preserve"


def test_post_feasible_preserve_marks_unproven_assisted_gradient_routes_as_risky() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "hotspot_spread",
        "gradient_band_smooth",
        "congestion_relief",
        "layout_rebalance",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_unproven_assisted_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_preserve"
    _assert_snapshot_preserves_support(policy, candidates)
    assert policy.candidate_annotations["hotspot_spread"]["evidence_level"] == "speculative"
    assert policy.candidate_annotations["hotspot_spread"]["post_feasible_role"] == "risky_expand"


def test_post_feasible_expand_rebalances_away_from_cooled_route_family() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "local_refine",
        "spread_hottest_cluster",
        "move_hottest_cluster_toward_sink",
        "reduce_local_congestion",
    )

    policy = policy_kernel.build_policy_snapshot(_post_feasible_expand_family_rebalance_state(), candidates)

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_expand_route_family_dominance_cap" in policy.reason_codes
    assert "post_feasible_expand_route_rebalance" in policy.reason_codes
    spread_budget = policy.candidate_annotations["spread_hottest_cluster"]["route_budget_state"]
    assert spread_budget["route_family"] == "hotspot_spread"
    assert spread_budget["cooldown_active"] is True
    assert policy.candidate_annotations["move_hottest_cluster_toward_sink"]["post_feasible_role"] == "supported_expand"
    assert policy.candidate_annotations["reduce_local_congestion"]["post_feasible_role"] == "risky_expand"


def test_post_feasible_expand_caps_recently_dominant_route_family_even_without_cooldown() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "local_refine",
        "spread_hottest_cluster",
        "move_hottest_cluster_toward_sink",
        "reduce_local_congestion",
    )

    policy = policy_kernel.build_policy_snapshot(_post_feasible_expand_family_dominance_state(), candidates)

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_expand_route_family_dominance_cap" in policy.reason_codes
    spread_budget = policy.candidate_annotations["spread_hottest_cluster"]["route_budget_state"]
    assert spread_budget["route_family"] == "hotspot_spread"
    assert spread_budget["recent_family_count"] == 5
    assert spread_budget["cooldown_active"] is False
    assert policy.candidate_annotations["move_hottest_cluster_toward_sink"]["post_feasible_role"] == "supported_expand"


def test_post_feasible_expand_throttles_semantic_route_with_recent_regression_and_no_frontier_credit() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "local_refine",
        "spread_hottest_cluster",
        "smooth_high_gradient_band",
    )

    policy = policy_kernel.build_policy_snapshot(_post_feasible_expand_budget_throttle_state(), candidates)

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert policy.candidate_annotations["spread_hottest_cluster"]["expand_budget_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["smooth_high_gradient_band"]["expand_budget_state"]["budget_status"] == "preferred"
    assert "post_feasible_expand_semantic_budget" in policy.reason_codes


def test_post_feasible_expand_throttles_low_success_gradient_route_family() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "gradient_band_smooth",
        "congestion_relief",
        "sink_retarget",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_low_success_gradient_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert policy.candidate_annotations["congestion_relief"]["expand_budget_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["congestion_relief"]["expand_budget_state"]["low_success_cooldown_active"] is True
    assert policy.candidate_annotations["gradient_band_smooth"]["expand_budget_state"]["budget_status"] == "neutral"
    assert policy.candidate_annotations["component_jitter_1"]["expand_budget_state"]["budget_status"] == "preferred"
    assert "post_feasible_expand_semantic_budget" in policy.reason_codes


def test_post_feasible_expand_caps_sink_retarget_when_gradient_pressure_needs_polishing() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "gradient_band_smooth",
        "congestion_relief",
        "sink_retarget",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_gradient_sink_route_dominance_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert policy.candidate_annotations["sink_retarget"]["route_budget_state"]["route_family"] == "sink_retarget"
    assert policy.candidate_annotations["sink_retarget"]["route_budget_state"]["recent_family_count"] == 4
    assert policy.candidate_annotations["sink_retarget"]["expand_budget_state"]["budget_status"] == "preferred"
    assert policy.candidate_annotations["gradient_band_smooth"]["gradient_polish_state"]["budget_status"] == "neutral"
    assert policy.candidate_annotations["component_jitter_1"]["gradient_polish_state"]["budget_status"] == "polish_alternative"
    assert "post_feasible_expand_objective_route_cap" in policy.reason_codes


def test_post_feasible_expand_caps_uncredited_custom_probe_budget_within_generation() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "hotspot_spread",
        "hotspot_pull_toward_sink",
        "gradient_band_smooth",
        "congestion_relief",
        "layout_rebalance",
        "sink_retarget",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_generation_probe_budget_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert policy.candidate_annotations["hotspot_spread"]["generation_probe_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["congestion_relief"]["generation_probe_state"]["custom_total_count"] == 4
    assert "post_feasible_expand_generation_probe_budget" in policy.reason_codes


def test_post_feasible_expand_keeps_credited_custom_when_generation_probe_budget_is_exhausted() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "hotspot_spread",
        "hotspot_pull_toward_sink",
        "gradient_band_smooth",
        "congestion_relief",
        "layout_rebalance",
        "sink_retarget",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_generation_probe_budget_with_credit_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_expand_generation_probe_budget" in policy.reason_codes
    assert policy.candidate_annotations["sink_retarget"]["generation_probe_state"]["budget_status"] == "credited"
    assert policy.candidate_annotations["hotspot_spread"]["generation_probe_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["congestion_relief"]["generation_probe_state"]["budget_status"] == "throttled"


def test_post_feasible_expand_caps_shared_gradient_route_probe_after_small_batch() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "gradient_band_smooth",
        "congestion_relief",
        "sink_retarget",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_generation_route_probe_budget_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_expand_generation_probe_budget" in policy.reason_codes
    assert policy.candidate_annotations["gradient_band_smooth"]["generation_probe_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["congestion_relief"]["generation_probe_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["sink_retarget"]["generation_probe_state"]["budget_status"] == "open_probe"


def test_post_feasible_expand_keeps_peak_budget_fill_route_after_probe_budget() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "sink_resize",
        "hotspot_pull_toward_sink",
        "sink_retarget",
        "congestion_relief",
        "layout_rebalance",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_peak_budget_fill_probe_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_expand_generation_probe_budget" in policy.reason_codes
    assert policy.candidate_annotations["sink_retarget"]["generation_probe_state"]["budget_status"] == "peak_budget_fill"
    assert policy.candidate_annotations["sink_resize"]["generation_probe_state"]["budget_status"] == "peak_budget_fill"
    assert policy.candidate_annotations["congestion_relief"]["generation_probe_state"]["budget_status"] == "throttled"


def test_post_feasible_expand_hands_off_broad_global_after_peak_improved_gradient_stagnation() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_swap_2",
        "component_jitter_1",
        "component_relocate_1",
        "gradient_band_smooth",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_peak_improved_gradient_polish_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_expand_gradient_polish_handoff" in policy.reason_codes
    assert policy.candidate_annotations["component_swap_2"]["gradient_polish_state"]["budget_status"] == "escape_credit"
    assert policy.candidate_annotations["vector_sbx_pm"]["gradient_polish_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["component_jitter_1"]["gradient_polish_state"]["budget_status"] == "polish_alternative"


def test_post_feasible_expand_suppresses_uncredited_broad_global_during_gradient_polish() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_swap_2",
        "component_jitter_1",
        "component_relocate_1",
        "gradient_band_smooth",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_peak_improved_uncredited_broad_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_expand"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_expand_gradient_polish_handoff" in policy.reason_codes
    assert policy.candidate_annotations["component_swap_2"]["gradient_polish_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["vector_sbx_pm"]["gradient_polish_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["component_swap_2"]["gradient_polish_state"]["escape_credit"] is False


def test_post_feasible_preserve_cools_sink_plateau_and_low_success_stable_routes() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "anchored_component_jitter",
        "component_swap_2",
        "sink_shift",
        "sink_resize",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_plateau_sink_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_preserve"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_preserve_plateau_cooldown" in policy.reason_codes
    assert "post_feasible_stable_low_success_cooldown" in policy.reason_codes
    assert policy.candidate_annotations["sink_shift"]["preserve_plateau_state"]["budget_status"] == "throttled"
    assert policy.candidate_annotations["anchored_component_jitter"]["stable_success_state"]["budget_status"] == "throttled"


def test_post_feasible_preserve_cools_assisted_sink_retarget_plateau() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "sink_shift",
        "sink_resize",
        "sink_retarget",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_sink_retarget_plateau_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_preserve"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_preserve_plateau_cooldown" in policy.reason_codes
    assert policy.candidate_annotations["sink_retarget"]["preserve_plateau_state"]["budget_status"] == "throttled"


def test_post_feasible_preserve_keeps_peak_budget_fill_routes_during_plateau() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "component_swap_2",
        "sink_shift",
        "sink_resize",
        "sink_retarget",
    )

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_peak_budget_fill_plateau_state(),
        candidates,
    )

    assert policy.phase == "post_feasible_preserve"
    _assert_snapshot_preserves_support(policy, candidates)
    assert policy.candidate_annotations["sink_resize"]["preserve_plateau_state"]["budget_status"] == "neutral"
    assert policy.candidate_annotations["sink_retarget"]["preserve_plateau_state"]["budget_status"] == "neutral"


def test_post_feasible_preserve_keeps_low_success_stable_route_when_no_alternative_exists() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_low_success_stable_without_alternative_state(),
        ("anchored_component_jitter",),
    )

    assert policy.phase == "post_feasible_preserve"
    assert policy.allowed_operator_ids == ("anchored_component_jitter",)
    assert "post_feasible_stable_low_success_cooldown" not in policy.reason_codes


def test_post_feasible_expand_keeps_broad_global_when_no_polish_alternative_exists() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_peak_improved_without_polish_alternative_state(),
        (
            "vector_sbx_pm",
            "component_swap_2",
            "gradient_band_smooth",
        ),
    )

    assert "post_feasible_expand_gradient_polish_handoff" not in policy.reason_codes
    assert "vector_sbx_pm" in policy.allowed_operator_ids
    assert "component_swap_2" in policy.allowed_operator_ids


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


def _post_feasible_expand_saturated_low_diversity_state() -> ControllerState:
    """Expand saturation should not demote while the Pareto set is still a single point."""
    state = _post_feasible_expand_saturated_state()
    state.metadata["archive_state"]["pareto_size"] = 1
    state.metadata["archive_state"]["recent_feasible_preservation_count"] = 2
    return state


def _post_feasible_expand_saturated_medium_diversity_deficit_state() -> ControllerState:
    state = _post_feasible_expand_saturated_state()
    state.metadata["archive_state"]["pareto_size"] = 2
    state.metadata["archive_state"]["recent_feasible_regression_count"] = 1
    state.metadata["archive_state"]["recent_feasible_preservation_count"] = 1
    state.metadata["progress_state"]["diversity_deficit_level"] = "medium"
    return state


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


def test_post_feasible_expand_saturated_keeps_expand_when_front_is_still_single_point() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_saturated_low_diversity_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "smooth_high_gradient_band",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert "post_feasible_expand_saturation_demotion" not in policy.reason_codes


def test_expand_saturation_does_not_demote_while_diversity_deficit_remains_medium() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_saturated_medium_diversity_deficit_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "smooth_high_gradient_band",
        ),
    )

    assert policy.phase == "post_feasible_expand"


def test_expand_keeps_diversity_floor_for_underused_frontier_family() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_diversity_floor_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "reduce_local_congestion",
            "rebalance_layout",
        ),
    )

    assert any(
        operator_id in policy.allowed_operator_ids
        for operator_id in ("spread_hottest_cluster", "reduce_local_congestion", "rebalance_layout")
    )


def test_post_feasible_recover_retains_stable_floor_when_semantic_preserver_exists() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "move_hottest_cluster_toward_sink",
        "spread_hottest_cluster",
        "smooth_high_gradient_band",
        "reduce_local_congestion",
    )

    policy = policy_kernel.build_policy_snapshot(_post_feasible_recover_semantic_monopoly_state(), candidates)

    assert policy.phase == "post_feasible_recover"
    _assert_snapshot_preserves_support(policy, candidates)
    assert "post_feasible_recover_preserve_bias" in policy.reason_codes
    assert policy.candidate_annotations["native_sbx_pm"]["post_feasible_role"] == "fragile_preserve"
    assert policy.candidate_annotations["global_explore"]["post_feasible_role"] == "fragile_preserve"
    assert policy.candidate_annotations["local_refine"]["post_feasible_role"] == "fragile_preserve"
    assert policy.candidate_annotations["smooth_high_gradient_band"]["post_feasible_role"] == "trusted_preserve"
    assert policy.candidate_annotations["spread_hottest_cluster"]["post_feasible_role"] == "risky_expand"


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


def test_prefeasible_convert_restores_budget_guard_when_sink_budget_is_tight() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _prefeasible_convert_budget_tight_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "repair_sink_budget",
            "move_hottest_cluster_toward_sink",
        ),
    )

    assert policy.phase == "prefeasible_convert"
    assert "repair_sink_budget" in policy.allowed_operator_ids


def test_prefeasible_convert_forced_reset_keeps_required_entry_candidates_visible() -> None:
    policy_kernel = _policy_kernel_module()

    state = _prefeasible_convert_budget_tight_state()
    state.metadata["progress_state"]["recent_no_progress_count"] = 5
    state.metadata["prompt_panels"]["spatial_panel"]["hotspot_inside_sink_window"] = True

    policy = policy_kernel.build_policy_snapshot(
        state,
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "repair_sink_budget",
            "spread_hottest_cluster",
        ),
    )

    assert policy.phase == "prefeasible_convert"
    assert "prefeasible_forced_reset" in policy.reason_codes
    assert "repair_sink_budget" in policy.allowed_operator_ids
    assert "spread_hottest_cluster" in policy.allowed_operator_ids


def test_prefeasible_convert_restores_positive_match_route_floors_after_speculative_reset() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _prefeasible_convert_visibility_floor_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "spread_hottest_cluster",
            "repair_sink_budget",
            "slide_sink",
        ),
    )

    assert policy.phase == "prefeasible_convert"
    assert "prefeasible_speculative_family_collapse" in policy.reason_codes
    assert "prefeasible_forced_reset" in policy.reason_codes
    assert "spread_hottest_cluster" in policy.allowed_operator_ids
    assert "slide_sink" in policy.allowed_operator_ids


def test_recover_handoff_restores_positive_stable_local_family_visibility() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_positive_stable_local_credit_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
        ),
    )

    assert "native_sbx_pm" in policy.allowed_operator_ids
    assert "local_refine" in policy.allowed_operator_ids


def test_recover_restores_visibility_floor_family_even_when_aggregate_credit_is_not_positive() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_recover_visibility_floor_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
        ),
    )

    assert "local_refine" in policy.allowed_operator_ids




def test_post_feasible_expand_marks_semantic_portfolio_debt_and_saturation() -> None:
    policy_kernel = _policy_kernel_module()
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=120,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 48,
                "evaluations_used": 119,
                "evaluations_remaining": 81,
                "feasible_rate": 0.51,
                "first_feasible_eval": 13,
            },
            "archive_state": {
                "pareto_size": 3,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 12,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 6,
                "recent_frontier_stagnation_count": 6,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 111 + index,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for index, operator_id in enumerate(
                    (
                        "component_subspace_sbx",
                        "sink_shift",
                        "component_subspace_sbx",
                        "sink_shift",
                        "component_subspace_sbx",
                        "sink_shift",
                        "component_subspace_sbx",
                        "component_jitter_1",
                    )
                )
            ],
            "operator_summary": {
                "vector_sbx_pm": {"selection_count": 0, "proposal_count": 0, "pareto_contribution_count": 0},
                "component_block_translate_2_4": {
                    "selection_count": 0,
                    "proposal_count": 0,
                    "pareto_contribution_count": 0,
                },
                "sink_resize": {"selection_count": 0, "proposal_count": 0, "pareto_contribution_count": 0},
                "component_subspace_sbx": {
                    "selection_count": 24,
                    "recent_selection_count": 4,
                    "proposal_count": 24,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
                "sink_shift": {
                    "selection_count": 19,
                    "recent_selection_count": 3,
                    "proposal_count": 19,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
            },
        },
    )

    policy = policy_kernel.build_policy_snapshot(
        state,
        (
            "vector_sbx_pm",
            "component_block_translate_2_4",
            "sink_resize",
            "component_subspace_sbx",
            "sink_shift",
        ),
    )

    assert "post_feasible_semantic_portfolio_debt" in policy.reason_codes
    assert "post_feasible_semantic_portfolio_saturation" in policy.reason_codes
    assert policy.candidate_annotations["vector_sbx_pm"]["portfolio_priority"] == "repay_task_debt"
    assert policy.candidate_annotations["component_block_translate_2_4"]["semantic_task_status"] == "under_target"
    assert policy.candidate_annotations["sink_resize"]["operator_portfolio_status"] == "balanced"
    assert policy.candidate_annotations["sink_resize"]["portfolio_priority"] == "neutral"
    assert policy.candidate_annotations["component_subspace_sbx"]["semantic_task_status"] == "saturated_no_frontier"
    assert policy.candidate_annotations["sink_shift"]["portfolio_priority"] == "avoid_saturated_repeat"


def test_post_feasible_expand_keeps_sink_budget_stabilizer_before_feasible_rate_gate() -> None:
    policy_kernel = _policy_kernel_module()
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=126,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 92,
                "evaluations_used": 125,
                "evaluations_remaining": 75,
                "feasible_rate": 0.42,
                "first_feasible_eval": 14,
                "sink_budget_utilization": 1.0,
            },
            "archive_state": {
                "pareto_size": 2,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 10,
                "recent_feasible_regression_count": 0,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 7,
                "recent_frontier_stagnation_count": 7,
                "diversity_deficit_level": "medium",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "frontier_pressure": "high",
                    "preservation_pressure": "medium",
                },
                "spatial_panel": {
                    "sink_budget_bucket": "full_sink",
                    "hotspot_inside_sink_window": True,
                    "nearest_neighbor_gap_min": 0.08,
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 118 + index,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for index, operator_id in enumerate(
                    (
                        "component_jitter_1",
                        "component_subspace_sbx",
                        "component_relocate_1",
                        "component_jitter_1",
                        "vector_sbx_pm",
                        "component_subspace_sbx",
                        "component_relocate_1",
                        "component_jitter_1",
                    )
                )
            ],
            "operator_summary": {
                "sink_resize": {
                    "selection_count": 44,
                    "recent_selection_count": 0,
                    "proposal_count": 44,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                    "post_feasible_success_count": 18,
                    "post_feasible_selection_count": 44,
                },
                "component_block_translate_2_4": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
                "component_subspace_sbx": {
                    "selection_count": 18,
                    "recent_selection_count": 1,
                    "proposal_count": 18,
                    "pareto_contribution_count": 1,
                    "recent_expand_frontier_add_count": 1,
                },
                "component_jitter_1": {
                    "selection_count": 20,
                    "recent_selection_count": 2,
                    "proposal_count": 20,
                    "pareto_contribution_count": 1,
                    "recent_expand_frontier_add_count": 1,
                },
            },
        },
    )

    policy = policy_kernel.build_policy_snapshot(
        state,
        (
            "sink_resize",
            "component_block_translate_2_4",
            "component_subspace_sbx",
            "component_jitter_1",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert policy.candidate_annotations["sink_resize"]["semantic_task"] == "sink_budget_shape"
    assert policy.candidate_annotations["sink_resize"]["semantic_task_status"] == "under_target"
    assert policy.candidate_annotations["sink_resize"]["portfolio_priority"] == "repay_task_debt"


def test_post_feasible_expand_does_not_repay_sink_budget_debt_without_budget_pressure() -> None:
    policy_kernel = _policy_kernel_module()
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=186,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 150,
                "evaluations_used": 185,
                "evaluations_remaining": 15,
                "feasible_rate": 0.52,
                "first_feasible_eval": 14,
                "sink_budget_utilization": 1.0,
            },
            "archive_state": {
                "pareto_size": 2,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 14,
                "recent_feasible_regression_count": 0,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 8,
                "recent_frontier_stagnation_count": 8,
                "diversity_deficit_level": "medium",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "frontier_pressure": "high",
                    "preservation_pressure": "medium",
                    "objective_balance": {
                        "balance_pressure": "high",
                        "preferred_effect": "gradient_improve",
                        "stagnant_objectives": ["gradient_rms"],
                        "improving_objectives": ["temperature_max"],
                    },
                },
                "spatial_panel": {
                    "sink_budget_bucket": "full_sink",
                    "hotspot_inside_sink_window": True,
                    "nearest_neighbor_gap_min": 0.08,
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 178 + index,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for index, operator_id in enumerate(
                    (
                        "component_jitter_1",
                        "component_subspace_sbx",
                        "component_relocate_1",
                        "component_jitter_1",
                        "vector_sbx_pm",
                        "component_subspace_sbx",
                        "component_relocate_1",
                        "component_jitter_1",
                    )
                )
            ],
            "operator_summary": {
                "sink_resize": {
                    "selection_count": 44,
                    "recent_selection_count": 3,
                    "proposal_count": 44,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                    "post_feasible_success_count": 18,
                    "post_feasible_selection_count": 44,
                },
                "component_block_translate_2_4": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
                "component_subspace_sbx": {
                    "selection_count": 18,
                    "recent_selection_count": 1,
                    "proposal_count": 18,
                    "pareto_contribution_count": 1,
                    "recent_expand_frontier_add_count": 1,
                },
                "component_jitter_1": {
                    "selection_count": 20,
                    "recent_selection_count": 2,
                    "proposal_count": 20,
                    "pareto_contribution_count": 1,
                    "recent_expand_frontier_add_count": 1,
                },
            },
        },
    )

    policy = policy_kernel.build_policy_snapshot(
        state,
        (
            "sink_resize",
            "component_block_translate_2_4",
            "component_subspace_sbx",
            "component_jitter_1",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert policy.candidate_annotations["sink_resize"]["semantic_task"] == "sink_budget_shape"
    assert policy.candidate_annotations["sink_resize"]["semantic_task_status"] == "saturated_no_frontier"
    assert policy.candidate_annotations["sink_resize"]["portfolio_priority"] == "avoid_saturated_repeat"
    assert policy.candidate_annotations["component_block_translate_2_4"]["portfolio_priority"] == "repay_task_debt"


def test_post_feasible_expand_restores_visibility_floor_family_after_route_dominance_cap() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_visibility_floor_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "smooth_high_gradient_band",
            "reduce_local_congestion",
            "rebalance_layout",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert "post_feasible_expand_route_family_dominance_cap" in policy.reason_codes
    assert "reduce_local_congestion" in policy.allowed_operator_ids
