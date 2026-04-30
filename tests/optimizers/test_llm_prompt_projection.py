from __future__ import annotations

import importlib

import pytest

from optimizers.operator_pool.policy_kernel import PolicySnapshot
from optimizers.operator_pool.state import ControllerState


def _prompt_projection_module():
    try:
        return importlib.import_module("optimizers.operator_pool.prompt_projection")
    except ModuleNotFoundError as exc:  # pragma: no cover
        pytest.fail(f"Missing prompt projection module: {exc}")


def _policy_snapshot(phase: str) -> PolicySnapshot:
    return PolicySnapshot(
        phase=phase,
        allowed_operator_ids=("native_sbx_pm", "local_refine", "repair_sink_budget"),
        suppressed_operator_ids=(),
        reset_active=phase.startswith("prefeasible"),
        reason_codes=(),
        candidate_annotations={
            "native_sbx_pm": {"operator_family": "native_baseline"},
            "local_refine": {"operator_family": "local_refine"},
            "repair_sink_budget": {"operator_family": "speculative_custom"},
        },
    )


def _prefeasible_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=48,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "run_state": {
                "decision_index": 17,
                "evaluations_used": 47,
                "evaluations_remaining": 82,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
                "peak_temperature": 349.4,
                "temperature_gradient_rms": 10.8,
            },
            "domain_regime": {
                "phase": "near_feasible",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.96,
            },
            "archive_state": {
                "best_feasible": None,
                "best_near_feasible": {"evaluation_index": 43, "total_violation": 0.11},
                "pareto_size": 0,
                "recent_frontier_add_count": 2,
                "evaluations_since_frontier_add": 0,
                "recent_feasible_regression_count": 3,
                "recent_feasible_preservation_count": 1,
            },
            "progress_state": {
                "phase": "prefeasible_stagnation",
                "first_feasible_found": False,
                "evaluations_since_first_feasible": None,
                "recent_no_progress_count": 8,
                "recent_frontier_stagnation_count": 0,
                "post_feasible_mode": None,
            },
            "operator_summary": {
                "native_sbx_pm": {"selection_count": 15, "recent_selection_count": 5, "proposal_count": 15},
                "local_refine": {
                    "selection_count": 11,
                    "recent_selection_count": 3,
                    "proposal_count": 11,
                    "post_feasible_avg_objective_delta": -0.18,
                    "post_feasible_avg_violation_delta": 0.07,
                },
            },
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 47,
                    "evaluations_remaining": 82,
                    "feasible_rate": 0.0,
                    "first_feasible_eval": None,
                    "peak_temperature": 349.4,
                    "temperature_gradient_rms": 10.8,
                },
                "regime_panel": {
                    "phase": "prefeasible_stagnation",
                    "dominant_violation_family": "thermal_limit",
                    "sink_budget_utilization": 0.96,
                },
                "parent_panel": {
                    "closest_to_feasible_parent": {"evaluation_index": 43, "feasible": False},
                    "strongest_feasible_parent": None,
                },
                "operator_panel": {
                    "native_sbx_pm": {
                        "entry_fit": "supported",
                        "preserve_fit": "supported",
                        "expand_fit": "supported",
                        "frontier_evidence": "limited",
                    },
                    "local_refine": {
                        "entry_fit": "supported",
                        "preserve_fit": "supported",
                        "expand_fit": "supported",
                        "frontier_evidence": "limited",
                    },
                },
            },
        },
    )


def _post_feasible_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=79,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 23,
                "evaluations_used": 78,
                "evaluations_remaining": 51,
                "feasible_rate": 0.19,
                "first_feasible_eval": 52,
                "peak_temperature": 344.8,
                "temperature_gradient_rms": 8.7,
            },
            "domain_regime": {
                "phase": "feasible_refine",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.91,
            },
            "archive_state": {
                "best_feasible": {"evaluation_index": 73, "total_violation": 0.0},
                "best_near_feasible": {"evaluation_index": 46, "total_violation": 0.08},
                "pareto_size": 3,
                "recent_frontier_add_count": 2,
                "evaluations_since_frontier_add": 4,
                "recent_feasible_regression_count": 1,
                "recent_feasible_preservation_count": 2,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "first_feasible_found": True,
                "evaluations_since_first_feasible": 27,
                "recent_no_progress_count": 3,
                "recent_frontier_stagnation_count": 4,
                "post_feasible_mode": "expand",
            },
            "operator_summary": {
                "native_sbx_pm": {"selection_count": 12, "recent_selection_count": 1, "proposal_count": 12},
                "repair_sink_budget": {
                    "selection_count": 7,
                    "recent_selection_count": 2,
                    "proposal_count": 7,
                    "post_feasible_avg_objective_delta": -0.34,
                    "post_feasible_avg_violation_delta": 0.02,
                },
            },
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 78,
                    "evaluations_remaining": 51,
                    "feasible_rate": 0.19,
                    "first_feasible_eval": 52,
                    "peak_temperature": 344.8,
                    "temperature_gradient_rms": 8.7,
                },
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "sink_budget_utilization": 0.91,
                },
                "parent_panel": {
                    "closest_to_feasible_parent": None,
                    "strongest_feasible_parent": {"evaluation_index": 73, "feasible": True},
                },
                "spatial_panel": {
                    "hotspot_to_sink_offset": 0.17,
                    "hotspot_inside_sink_window": False,
                    "local_congestion_pair": {
                        "component_ids": ["c13", "c14"],
                        "gap": 0.04,
                    },
                    "nearest_neighbor_gap_min": 0.04,
                    "sink_budget_bucket": "available",
                },
                "operator_panel": {
                    "native_sbx_pm": {
                        "entry_fit": "supported",
                        "preserve_fit": "supported",
                        "expand_fit": "supported",
                        "frontier_evidence": "positive",
                    },
                    "repair_sink_budget": {
                        "entry_fit": "supported",
                        "preserve_fit": "trusted",
                        "expand_fit": "trusted",
                        "frontier_evidence": "positive",
                        "post_feasible_avg_objective_delta": -0.34,
                        "applicability": "medium",
                        "expected_peak_effect": "neutral",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "spatial_match_reason": "sink span is already feasible and close to current pressure.",
                    },
                },
            },
        },
    )


def test_prefeasible_prompt_projection_omits_post_feasible_frontier_fields() -> None:
    prompt_projection = _prompt_projection_module()
    state = _prefeasible_state()
    state.metadata["prompt_panels"]["operator_panel"]["local_refine"].update(
        {
            "pde_attempt_count": 6,
            "pde_feasible_count": 1,
            "pde_feasible_rate": 1.0 / 6.0,
            "cheap_skip_count": 2,
            "cheap_skip_rate": 0.25,
            "thermal_infeasible_count": 4,
        }
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        original_candidate_operator_ids=("native_sbx_pm", "local_refine", "repair_sink_budget"),
        policy_snapshot=_policy_snapshot("prefeasible_stagnation"),
        guardrail=None,
    )

    assert "prompt_panels" in payload
    assert "frontier_evidence" not in payload["prompt_panels"]["operator_panel"]["local_refine"]
    assert payload["prompt_panels"]["operator_panel"]["local_refine"]["pde_attempt_count"] == 6
    assert payload["prompt_panels"]["operator_panel"]["local_refine"]["pde_feasible_rate"] == pytest.approx(1.0 / 6.0)
    assert payload["prompt_panels"]["operator_panel"]["local_refine"]["cheap_skip_rate"] == pytest.approx(0.25)
    assert payload["prompt_panels"]["operator_panel"]["local_refine"]["thermal_infeasible_count"] == 4
    assert payload["prompt_panels"]["run_panel"]["peak_temperature"] == pytest.approx(349.4)
    assert payload["prompt_panels"]["regime_panel"]["sink_budget_utilization"] == pytest.approx(0.96)
    assert payload["phase_policy"]["phase"] == "prefeasible_stagnation"


def test_post_feasible_prompt_projection_keeps_frontier_and_regression_fields() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    state.metadata["prompt_panels"]["operator_panel"]["repair_sink_budget"].update(
        {
            "post_feasible_pde_attempt_count": 8,
            "post_feasible_pde_feasible_count": 3,
            "post_feasible_pde_feasible_rate": 0.375,
            "post_feasible_cheap_skip_count": 2,
            "post_feasible_cheap_skip_rate": 0.2,
            "post_feasible_thermal_infeasible_count": 4,
        }
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "local_refine", "repair_sink_budget"),
        policy_snapshot=_policy_snapshot("post_feasible_expand"),
        guardrail=None,
    )

    assert payload["prompt_panels"]["run_panel"]["temperature_gradient_rms"] == pytest.approx(8.7)
    assert payload["prompt_panels"]["regime_panel"]["phase"] == "post_feasible_expand"
    assert payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]["frontier_evidence"] == "positive"
    assert payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]["post_feasible_pde_attempt_count"] == 8
    assert payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]["post_feasible_pde_feasible_rate"] == pytest.approx(0.375)
    assert payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]["post_feasible_cheap_skip_rate"] == pytest.approx(0.2)
    assert payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]["post_feasible_thermal_infeasible_count"] == 4
    assert payload["phase_policy"]["phase"] == "post_feasible_expand"


def test_post_feasible_prompt_projection_keeps_spatial_panel_and_operator_applicability() -> None:
    prompt_projection = _prompt_projection_module()

    payload = prompt_projection.build_prompt_projection(
        _post_feasible_state(),
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "local_refine", "repair_sink_budget"),
        policy_snapshot=_policy_snapshot("post_feasible_expand"),
        guardrail=None,
    )

    assert "spatial_panel" in payload["prompt_panels"]
    assert payload["prompt_panels"]["spatial_panel"]["hotspot_inside_sink_window"] is False
    assert payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]["applicability"] == "medium"
    assert "local_congestion_pair" not in payload["prompt_panels"]["spatial_panel"]
    assert "spatial_match_reason" not in payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]


def test_prompt_projection_compacts_large_parent_retrieval_and_annotation_payloads() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    state.metadata["prompt_panels"]["parent_panel"] = {
        "closest_to_feasible_parent": {
            "evaluation_index": 71,
            "feasible": False,
            "total_violation": 0.08,
            "dominant_violation": {"constraint_id": "layout_spacing", "violation": 0.08},
            "decision_vector": {f"x{i:02d}": i / 100 for i in range(32)},
        },
        "strongest_feasible_parent": {
            "evaluation_index": 73,
            "feasible": True,
            "total_violation": 0.0,
            "decision_vector": {f"x{i:02d}": i / 200 for i in range(32)},
        },
    }
    state.metadata["prompt_panels"]["retrieval_panel"] = {
        "query_regime": {
            "phase": "post_feasible_recover",
            "phase_fallbacks": ["post_feasible_preserve"],
            "dominant_violation_family": "thermal_limit",
            "sink_budget_bucket": "full_sink",
        },
        "positive_match_families": ["stable_local", "sink_retarget"],
        "negative_match_families": ["stable_global"],
        "visibility_floor_families": ["stable_local"],
        "stable_local_handoff_active": True,
        "route_family_credit": {
            "positive_families": ["stable_local"],
            "negative_families": ["stable_global"],
            "handoff_families": ["stable_local"],
        },
        "positive_matches": [
            {
                "operator_id": "repair_sink_budget",
                "route_family": "sink_retarget",
                "similarity_score": 9,
                "regime": {"phase": "post_feasible_expand", "sink_budget_bucket": "full_sink"},
                "evidence": {
                    "avg_objective_delta": -0.2,
                    "avg_total_violation_delta": -0.1,
                    "frontier_add_count": 2,
                    "feasible_regression_count": 0,
                    "penalty_event_count": 0,
                },
            },
            {
                "operator_id": "native_sbx_pm",
                "route_family": "stable_local",
                "similarity_score": 8,
                "regime": {"phase": "post_feasible_expand"},
                "evidence": {"frontier_add_count": 1, "feasible_regression_count": 0},
            },
            {
                "operator_id": "local_refine",
                "route_family": "stable_local",
                "similarity_score": 7,
                "regime": {"phase": "post_feasible_expand"},
                "evidence": {"frontier_add_count": 1, "feasible_regression_count": 0},
            },
        ],
        "negative_matches": [
            {
                "operator_id": "local_refine",
                "route_family": "stable_local",
                "similarity_score": 6,
                "regime": {"phase": "post_feasible_recover"},
                "evidence": {"frontier_add_count": 0, "feasible_regression_count": 2, "penalty_event_count": 1},
            },
            {
                "operator_id": "repair_sink_budget",
                "route_family": "sink_retarget",
                "similarity_score": 5,
                "regime": {"phase": "post_feasible_recover"},
                "evidence": {"frontier_add_count": 0, "feasible_regression_count": 1},
            },
        ],
        "matched_episodes": [
            {"operator_id": f"op{i}", "route_family": "stable_local", "similarity_score": i, "evidence": {}}
            for i in range(5)
        ],
    }
    policy_snapshot = PolicySnapshot(
        phase="post_feasible_expand",
        allowed_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=("post_feasible_expand_route_rebalance",),
        candidate_annotations={
            "native_sbx_pm": {
                "operator_family": "native_baseline",
                "role": "native_baseline",
                "evidence_level": "trusted",
                "post_feasible_role": "fragile_preserve",
                "avg_near_feasible_violation_delta": -1.0,
                "post_feasible_avg_objective_delta": -0.2,
                "recent_entry_helpful_regimes": ["thermal_limit"],
                "route_budget_state": {
                    "cooldown_active": False,
                    "recent_family_count": 18,
                    "recent_family_share": 0.9,
                },
                "expand_budget_state": {
                    "expand_budget_status": "preferred",
                    "recent_expand_frontier_add_count": 2,
                },
            },
            "repair_sink_budget": {
                "operator_family": "primitive_sink",
                "role": "sink_resize",
                "evidence_level": "speculative",
                "post_feasible_role": "risky_expand",
                "route_budget_state": {"cooldown_active": True, "recent_family_share": 0.8},
            },
        },
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    parent_panel = payload["prompt_panels"]["parent_panel"]
    assert "decision_vector" not in parent_panel["closest_to_feasible_parent"]
    assert "decision_vector" not in parent_panel["strongest_feasible_parent"]
    retrieval_panel = payload["prompt_panels"]["retrieval_panel"]
    assert len(retrieval_panel["positive_matches"]) == 2
    assert len(retrieval_panel["negative_matches"]) == 1
    assert "matched_episodes" not in retrieval_panel
    first_positive = retrieval_panel["positive_matches"][0]
    assert set(first_positive) == {"operator_id", "route_family", "similarity_score", "evidence"}
    assert set(first_positive["evidence"]) == {"frontier_add_count", "feasible_regression_count", "penalty_event_count"}
    operator_row = payload["prompt_panels"]["operator_panel"]["native_sbx_pm"]
    assert operator_row["role"] == "native_baseline"
    assert operator_row["expand_budget_status"] == "preferred"
    assert "route_cooldown_active" not in operator_row
    assert "recent_expand_frontier_add_count" not in operator_row
    assert payload["phase_policy"]["candidate_annotations"] == {}


def test_post_feasible_operator_panel_projects_compact_decision_rows() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    state.metadata["prompt_panels"]["operator_panel"]["repair_sink_budget"].update(
        {
            "dominant_violation_relief": "supported",
            "dominant_violation_relief_count": 4,
            "entry_evidence_level": "trusted",
            "evidence_level": "trusted",
            "feasible_entry_count": 3,
            "feasible_preservation_count": 8,
            "feasible_regression_count": 1,
            "operator_family": "primitive_sink",
            "pareto_contribution_count": 2,
            "post_feasible_role": "trusted_preserve",
            "recent_expand_feasible_preservation_count": 4,
            "recent_expand_feasible_regression_count": 1,
            "recent_expand_frontier_add_count": 2,
            "role": "sink_resize",
            "route_cooldown_active": False,
        }
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        policy_snapshot=_policy_snapshot("post_feasible_expand"),
        guardrail=None,
    )

    row = payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]
    assert row == {
        "applicability": "medium",
        "entry_fit": "supported",
        "preserve_fit": "trusted",
        "expand_fit": "trusted",
        "frontier_evidence": "positive",
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
        "expected_feasibility_risk": "low",
        "role": "sink_resize",
        "post_feasible_role": "trusted_preserve",
    }


def test_post_feasible_projection_omits_false_and_count_only_annotation_noise() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    policy_snapshot = PolicySnapshot(
        phase="post_feasible_expand",
        allowed_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=(),
        candidate_annotations={
            "repair_sink_budget": {
                "operator_family": "primitive_sink",
                "role": "sink_resize",
                "evidence_level": "trusted",
                "post_feasible_role": "trusted_preserve",
                "feasible_entry_count": 1,
                "feasible_preservation_count": 3,
                "feasible_regression_count": 0,
                "pareto_contribution_count": 1,
                "route_budget_state": {"cooldown_active": False},
                "expand_budget_state": {
                    "expand_budget_status": "preferred",
                    "recent_expand_frontier_add_count": 2,
                    "recent_expand_feasible_preservation_count": 2,
                    "recent_expand_feasible_regression_count": 0,
                },
            }
        },
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    row = payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]
    assert row["expand_budget_status"] == "preferred"
    assert row["role"] == "sink_resize"
    assert row["post_feasible_role"] == "trusted_preserve"
    assert "route_cooldown_active" not in row
    assert "feasible_entry_count" not in row
    assert "feasible_preservation_count" not in row
    assert "feasible_regression_count" not in row
    assert "pareto_contribution_count" not in row
    assert "recent_expand_frontier_add_count" not in row
    assert "recent_expand_feasible_preservation_count" not in row
    assert "recent_expand_feasible_regression_count" not in row


def test_post_feasible_operator_panel_preserves_exposure_fields() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    policy_snapshot = PolicySnapshot(
        phase="post_feasible_expand",
        allowed_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=("post_feasible_bounded_exploration_exposure",),
        candidate_annotations={
            "native_sbx_pm": {"operator_family": "native_baseline"},
            "repair_sink_budget": {
                "operator_family": "primitive_sink",
                "role": "sink_resize",
                "post_feasible_role": "supported_expand",
                "exposure_priority": "sink_underexposed",
                "exposure_status": "local_cleanup_cooldown",
            },
        },
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    row = payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]
    assert row["exposure_priority"] == "sink_underexposed"
    assert row["exposure_status"] == "local_cleanup_cooldown"


def test_post_feasible_operator_panel_preserves_semantic_portfolio_fields() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    state.metadata["prompt_panels"]["semantic_task_panel"] = {
        "active_bottleneck": "sink_misaligned_hotspot",
        "recommended_task_order": ["sink_alignment", "semantic_block_move"],
        "task_operator_candidates": {
            "sink_alignment": ["repair_sink_budget"],
            "semantic_block_move": [],
        },
        "task_rationales": {"sink_alignment": "hotspot offset remains high"},
    }
    policy_snapshot = PolicySnapshot(
        phase="post_feasible_expand",
        allowed_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=("post_feasible_semantic_portfolio_debt",),
        candidate_annotations={
            "repair_sink_budget": {
                "semantic_task": "sink_budget_shape",
                "semantic_task_status": "under_target",
                "operator_portfolio_status": "underexposed",
                "portfolio_priority": "repay_task_debt",
            }
        },
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    assert payload["prompt_panels"]["semantic_task_panel"]["active_bottleneck"] == "sink_misaligned_hotspot"
    row = payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]
    assert row["semantic_task"] == "sink_budget_shape"
    assert row["semantic_task_status"] == "under_target"
    assert row["operator_portfolio_status"] == "underexposed"
    assert row["portfolio_priority"] == "repay_task_debt"
