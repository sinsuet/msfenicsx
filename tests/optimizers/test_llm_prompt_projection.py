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

    payload = prompt_projection.build_prompt_projection(
        _prefeasible_state(),
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        original_candidate_operator_ids=("native_sbx_pm", "local_refine", "repair_sink_budget"),
        policy_snapshot=_policy_snapshot("prefeasible_stagnation"),
        guardrail=None,
    )

    assert "prompt_panels" in payload
    assert "frontier_evidence" not in payload["prompt_panels"]["operator_panel"]["local_refine"]
    assert payload["prompt_panels"]["run_panel"]["peak_temperature"] == pytest.approx(349.4)
    assert payload["prompt_panels"]["regime_panel"]["sink_budget_utilization"] == pytest.approx(0.96)
    assert payload["phase_policy"]["phase"] == "prefeasible_stagnation"


def test_post_feasible_prompt_projection_keeps_frontier_and_regression_fields() -> None:
    prompt_projection = _prompt_projection_module()

    payload = prompt_projection.build_prompt_projection(
        _post_feasible_state(),
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "local_refine", "repair_sink_budget"),
        policy_snapshot=_policy_snapshot("post_feasible_expand"),
        guardrail=None,
    )

    assert payload["prompt_panels"]["run_panel"]["temperature_gradient_rms"] == pytest.approx(8.7)
    assert payload["prompt_panels"]["regime_panel"]["phase"] == "post_feasible_expand"
    assert payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]["frontier_evidence"] == "positive"
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
