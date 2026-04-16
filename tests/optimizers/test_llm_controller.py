from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from llm.openai_compatible.client import OpenAICompatibleDecision
from optimizers.operator_pool.llm_controller import LLMOperatorController
from optimizers.operator_pool.state import ControllerState


class _FakeLLMClient:
    def __init__(self, decision: OpenAICompatibleDecision | None = None, error: Exception | None = None) -> None:
        self.decision = decision
        self.error = error
        self.last_kwargs: dict[str, object] | None = None

    def request_operator_decision(self, **kwargs) -> OpenAICompatibleDecision:
        self.last_kwargs = dict(kwargs)
        if self.error is not None:
            raise self.error
        assert self.decision is not None
        return self.decision


class _RetryThenSuccessLLMClient:
    def request_operator_decision(self, **kwargs) -> OpenAICompatibleDecision:
        attempt_trace = kwargs.get("attempt_trace")
        if isinstance(attempt_trace, list):
            attempt_trace.extend(
                [
                    {
                        "attempt_index": 1,
                        "valid": False,
                        "error": "Expecting value: line 1 column 1 (char 0)",
                    },
                    {
                        "attempt_index": 2,
                        "valid": True,
                        "selected_operator_id": "local_refine",
                    },
                ]
            )
        return OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="tighten the current layout around the strongest evidence.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )


def _state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=12,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
        },
    )


def _dominance_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=48,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "move_hottest_cluster_toward_sink",
                "local_refine",
            ],
            "recent_decisions": [
                {
                    "evaluation_index": 40 + index,
                    "selected_operator_id": (
                        "move_hottest_cluster_toward_sink" if index < 6 else "local_refine"
                    ),
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for index in range(8)
            ],
            "recent_operator_counts": {
                "move_hottest_cluster_toward_sink": {
                    "recent_selection_count": 6,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 6,
                },
                "local_refine": {
                    "recent_selection_count": 2,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 2,
                },
            },
            "operator_summary": {
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 19,
                    "recent_selection_count": 6,
                    "proposal_count": 19,
                },
                "native_sbx_pm": {
                    "selection_count": 6,
                    "recent_selection_count": 0,
                    "proposal_count": 6,
                },
                "local_refine": {
                    "selection_count": 4,
                    "recent_selection_count": 2,
                    "proposal_count": 4,
                },
            },
        },
    )


def _domain_grounded_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=7,
        evaluation_index=64,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "move_hottest_cluster_toward_sink",
                "repair_sink_budget",
            ],
            "run_state": {
                "decision_index": 12,
                "evaluations_used": 63,
                "evaluations_remaining": 66,
                "feasible_rate": 0.17,
                "first_feasible_eval": 45,
                "peak_temperature": 344.8,
                "temperature_gradient_rms": 8.7,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 3,
                "recent_frontier_stagnation_count": 3,
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 2,
            },
            "parent_state": {
                "parent_indices": [3, 8],
                "parents": [
                    {
                        "decision_vector": {"c01_x": 0.18, "c01_y": 0.18},
                        "feasible": False,
                        "total_violation": 0.7,
                        "dominant_violation": {
                            "constraint_id": "c01_peak_temperature_limit",
                            "violation": 0.7,
                        },
                    },
                    {
                        "decision_vector": {"c01_x": 0.19, "c01_y": 0.19},
                        "feasible": True,
                        "total_violation": 0.0,
                        "dominant_violation": None,
                        "objective_summary": {"minimize_peak_temperature": 344.8},
                    },
                ],
            },
            "archive_state": {
                "best_feasible": {"evaluation_index": 44, "total_violation": 0.0},
                "best_near_feasible": {"evaluation_index": 32, "total_violation": 0.2},
            },
            "domain_regime": {
                "phase": "feasible_refine",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.9166666667,
            },
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 63,
                    "evaluations_remaining": 66,
                    "feasible_rate": 0.17,
                    "first_feasible_eval": 45,
                    "peak_temperature": 344.8,
                    "temperature_gradient_rms": 8.7,
                    "pareto_size": 4,
                },
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "dominant_violation_persistence_count": 2,
                    "sink_budget_utilization": 0.9166666667,
                    "entry_pressure": "low",
                    "preservation_pressure": "medium",
                    "frontier_pressure": "high",
                },
                "parent_panel": {
                    "closest_to_feasible_parent": {
                        "evaluation_index": 44,
                        "feasible": False,
                        "total_violation": 0.7,
                    },
                    "strongest_feasible_parent": {
                        "evaluation_index": 45,
                        "feasible": True,
                        "objective_summary": {"minimize_peak_temperature": 344.8},
                    },
                },
                "operator_panel": {
                    "move_hottest_cluster_toward_sink": {
                        "entry_fit": "trusted",
                        "preserve_fit": "trusted",
                        "expand_fit": "supported",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "positive",
                        "dominant_violation_relief": "supported",
                    },
                    "repair_sink_budget": {
                        "entry_fit": "supported",
                        "preserve_fit": "trusted",
                        "expand_fit": "weak",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "limited",
                        "dominant_violation_relief": "supported",
                    },
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 61,
                    "selected_operator_id": "move_hottest_cluster_toward_sink",
                    "fallback_used": False,
                    "llm_valid": True,
                }
            ],
            "recent_operator_counts": {
                "move_hottest_cluster_toward_sink": {
                    "recent_selection_count": 2,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 2,
                }
            },
            "operator_summary": {
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 5,
                    "recent_selection_count": 2,
                    "fallback_selection_count": 0,
                    "llm_valid_selection_count": 5,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 2,
                    "proposal_count": 5,
                    "feasible_entry_count": 1,
                    "feasible_preservation_count": 2,
                    "avg_total_violation_delta": -0.18,
                },
                "repair_sink_budget": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "fallback_selection_count": 0,
                    "llm_valid_selection_count": 3,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 0,
                    "proposal_count": 3,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 1,
                    "avg_total_violation_delta": -0.06,
                },
            },
            "problem_history": [{"should_not": "appear"}],
            "case_reports": {"should_not": "appear"},
        },
    )


def _prefeasible_convert_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=33,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "repair_sink_budget",
                "move_hottest_cluster_toward_sink",
            ],
            "run_state": {
                "decision_index": 8,
                "evaluations_used": 32,
                "evaluations_remaining": 97,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
                "peak_temperature": 350.1,
                "temperature_gradient_rms": 9.9,
            },
            "progress_state": {
                "phase": "prefeasible_stagnation",
                "first_feasible_found": False,
                "prefeasible_mode": "convert",
                "recent_no_progress_count": 4,
                "evaluations_since_near_feasible_improvement": 4,
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 3,
            },
            "domain_regime": {
                "phase": "near_feasible",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.9,
            },
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 32,
                    "evaluations_remaining": 97,
                    "feasible_rate": 0.0,
                    "first_feasible_eval": None,
                    "peak_temperature": 350.1,
                    "temperature_gradient_rms": 9.9,
                    "pareto_size": 0,
                },
                "regime_panel": {
                    "phase": "prefeasible_convert",
                    "dominant_violation_family": "thermal_limit",
                    "dominant_violation_persistence_count": 3,
                    "sink_budget_utilization": 0.9,
                    "entry_pressure": "high",
                    "preservation_pressure": "low",
                    "frontier_pressure": "low",
                },
                "parent_panel": {
                    "closest_to_feasible_parent": {
                        "evaluation_index": 31,
                        "feasible": False,
                        "total_violation": 0.42,
                    },
                    "strongest_feasible_parent": None,
                },
                "operator_panel": {
                    "repair_sink_budget": {
                        "entry_fit": "trusted",
                        "preserve_fit": "supported",
                        "expand_fit": "weak",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "limited",
                        "dominant_violation_relief": "supported",
                    },
                    "move_hottest_cluster_toward_sink": {
                        "entry_fit": "weak",
                        "preserve_fit": "weak",
                        "expand_fit": "supported",
                        "recent_regression_risk": "medium",
                        "frontier_evidence": "positive",
                        "dominant_violation_relief": "limited",
                    },
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                },
                "repair_sink_budget": {
                    "selection_count": 4,
                    "recent_selection_count": 1,
                    "proposal_count": 4,
                    "feasible_entry_count": 1,
                    "dominant_violation_relief_count": 2,
                    "near_feasible_improvement_count": 2,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 6,
                    "recent_selection_count": 2,
                    "proposal_count": 6,
                    "pareto_contribution_count": 2,
                    "post_feasible_avg_objective_delta": -0.2,
                },
            },
        },
    )


def _post_feasible_collapse_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=88,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "global_explore",
                "local_refine",
                "slide_sink",
                "repair_sink_budget",
                "move_hottest_cluster_toward_sink",
            ],
            "run_state": {
                "decision_index": 26,
                "evaluations_used": 87,
                "evaluations_remaining": 42,
                "feasible_rate": 0.41,
                "first_feasible_eval": 45,
                "peak_temperature": 309.8,
                "temperature_gradient_rms": 13.2,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "first_feasible_found": True,
                "post_feasible_mode": "recover",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 5,
            },
            "domain_regime": {
                "phase": "feasible_refine",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.97,
            },
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 87,
                    "evaluations_remaining": 42,
                    "feasible_rate": 0.41,
                    "first_feasible_eval": 45,
                    "peak_temperature": 309.8,
                    "temperature_gradient_rms": 13.2,
                    "pareto_size": 5,
                },
                "regime_panel": {
                    "phase": "post_feasible_recover",
                    "dominant_violation_family": "thermal_limit",
                    "dominant_violation_persistence_count": 4,
                    "sink_budget_utilization": 0.97,
                    "entry_pressure": "low",
                    "preservation_pressure": "high",
                    "frontier_pressure": "medium",
                },
                "parent_panel": {
                    "closest_to_feasible_parent": None,
                    "strongest_feasible_parent": {
                        "evaluation_index": 83,
                        "feasible": True,
                        "objective_summary": {"minimize_peak_temperature": 309.8},
                    },
                },
                "operator_panel": {
                    "native_sbx_pm": {
                        "entry_fit": "supported",
                        "preserve_fit": "trusted",
                        "expand_fit": "supported",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "positive",
                        "dominant_violation_relief": "supported",
                    },
                    "global_explore": {
                        "entry_fit": "supported",
                        "preserve_fit": "supported",
                        "expand_fit": "supported",
                        "recent_regression_risk": "medium",
                        "frontier_evidence": "limited",
                        "dominant_violation_relief": "limited",
                    },
                    "local_refine": {
                        "entry_fit": "supported",
                        "preserve_fit": "trusted",
                        "expand_fit": "supported",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "positive",
                        "dominant_violation_relief": "supported",
                    },
                    "slide_sink": {
                        "entry_fit": "weak",
                        "preserve_fit": "weak",
                        "expand_fit": "weak",
                        "recent_regression_risk": "medium",
                        "frontier_evidence": "limited",
                        "dominant_violation_relief": "limited",
                    },
                    "repair_sink_budget": {
                        "entry_fit": "weak",
                        "preserve_fit": "weak",
                        "expand_fit": "weak",
                        "recent_regression_risk": "medium",
                        "frontier_evidence": "limited",
                        "dominant_violation_relief": "limited",
                    },
                    "move_hottest_cluster_toward_sink": {
                        "entry_fit": "weak",
                        "preserve_fit": "weak",
                        "expand_fit": "weak",
                        "recent_regression_risk": "medium",
                        "frontier_evidence": "limited",
                        "dominant_violation_relief": "limited",
                    },
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 18,
                    "recent_selection_count": 2,
                    "proposal_count": 18,
                    "feasible_preservation_count": 5,
                },
                "global_explore": {
                    "selection_count": 10,
                    "recent_selection_count": 1,
                    "proposal_count": 10,
                },
                "local_refine": {
                    "selection_count": 16,
                    "recent_selection_count": 2,
                    "proposal_count": 16,
                    "feasible_preservation_count": 4,
                },
                "slide_sink": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
                "repair_sink_budget": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                },
            },
        },
    )


def _recover_semantic_monopoly_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=62,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "global_explore",
                "local_refine",
                "move_hottest_cluster_toward_sink",
                "spread_hottest_cluster",
                "smooth_high_gradient_band",
                "reduce_local_congestion",
            ],
            "run_state": {
                "decision_index": 49,
                "evaluations_used": 61,
                "evaluations_remaining": 12,
                "feasible_rate": 0.75,
                "first_feasible_eval": 3,
                "peak_temperature": 308.22700544287414,
                "temperature_gradient_rms": 15.563525584103749,
                "pareto_size": 3,
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


def _retrieval_rich_state() -> ControllerState:
    state = _domain_grounded_state()
    state.metadata["prompt_panels"]["retrieval_panel"] = {
        "query_regime": {
            "phase": "post_feasible_expand",
            "dominant_violation_family": "thermal_limit",
            "sink_budget_bucket": "tight",
        },
        "matched_episodes": [
            {
                "operator_id": "slide_sink",
                "similarity_score": 6,
                "regime": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "sink_budget_bucket": "tight",
                },
                "evidence": {
                    "frontier_add_count": 2,
                    "feasible_preservation_count": 1,
                },
            }
        ],
    }
    return state


def _semantic_trial_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=92,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "spread_hottest_cluster",
                "move_hottest_cluster_toward_sink",
            ],
            "run_state": {
                "decision_index": 27,
                "evaluations_used": 91,
                "evaluations_remaining": 38,
                "feasible_rate": 0.39,
                "first_feasible_eval": 45,
                "peak_temperature": 307.9,
                "temperature_gradient_rms": 13.1,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "first_feasible_found": True,
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 3,
                "recent_frontier_stagnation_count": 4,
                "recent_dominant_violation_family": "thermal_limit",
                "recent_dominant_violation_persistence_count": 1,
            },
            "archive_state": {
                "best_feasible": {"evaluation_index": 88, "total_violation": 0.0},
                "best_near_feasible": {"evaluation_index": 41, "total_violation": 0.11},
                "pareto_size": 4,
                "recent_feasible_regression_count": 0,
                "recent_feasible_preservation_count": 2,
            },
            "domain_regime": {
                "phase": "feasible_refine",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.91,
            },
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 91,
                    "evaluations_remaining": 38,
                    "feasible_rate": 0.39,
                    "first_feasible_eval": 45,
                    "peak_temperature": 307.9,
                    "temperature_gradient_rms": 13.1,
                    "pareto_size": 4,
                },
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "dominant_violation_persistence_count": 1,
                    "sink_budget_utilization": 0.91,
                    "entry_pressure": "low",
                    "preservation_pressure": "medium",
                    "frontier_pressure": "high",
                },
                "spatial_panel": {
                    "hotspot_inside_sink_window": True,
                    "hotspot_to_sink_offset": 0.01,
                    "hottest_cluster_compactness": 0.08,
                    "nearest_neighbor_gap_min": 0.115,
                    "sink_budget_bucket": "tight",
                },
                "operator_panel": {
                    "native_sbx_pm": {
                        "entry_fit": "supported",
                        "preserve_fit": "supported",
                        "expand_fit": "supported",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "positive",
                        "applicability": "medium",
                        "expected_feasibility_risk": "low",
                    },
                    "spread_hottest_cluster": {
                        "entry_fit": "weak",
                        "preserve_fit": "supported",
                        "expand_fit": "trusted",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "positive",
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "improve",
                        "expected_feasibility_risk": "low",
                        "spatial_match_reason": (
                            "hot cluster already sits inside the sink corridor, so a bounded spread is the direct "
                            "way to open local space without retargeting the sink."
                        ),
                    },
                    "move_hottest_cluster_toward_sink": {
                        "entry_fit": "supported",
                        "preserve_fit": "supported",
                        "expand_fit": "supported",
                        "recent_regression_risk": "medium",
                        "frontier_evidence": "limited",
                        "applicability": "low",
                        "expected_feasibility_risk": "medium",
                        "spatial_match_reason": (
                            "hot cluster already sits inside the sink corridor, so further sink retargeting has "
                            "limited leverage."
                        ),
                    },
                },
                "retrieval_panel": {
                    "query_regime": {
                        "phase": "post_feasible_expand",
                        "dominant_violation_family": "thermal_limit",
                        "sink_budget_bucket": "tight",
                    },
                    "matched_episodes": [
                        {
                            "operator_id": "spread_hottest_cluster",
                            "similarity_score": 6,
                            "regime": {
                                "phase": "post_feasible_expand",
                                "dominant_violation_family": "thermal_limit",
                                "sink_budget_bucket": "tight",
                            },
                            "evidence": {
                                "frontier_add_count": 2,
                                "feasible_preservation_count": 1,
                            },
                        }
                    ],
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 90,
                    "selected_operator_id": "native_sbx_pm",
                    "fallback_used": False,
                    "llm_valid": True,
                }
            ],
            "recent_operator_counts": {
                "native_sbx_pm": {
                    "recent_selection_count": 1,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 1,
                }
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 18,
                    "recent_selection_count": 1,
                    "proposal_count": 18,
                },
                "spread_hottest_cluster": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                    "feasible_preservation_count": 2,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                },
            },
        },
    )


def _route_diverse_expand_state() -> ControllerState:
    state = copy.deepcopy(_semantic_trial_state())
    state.metadata["candidate_operator_ids"] = [
        "native_sbx_pm",
        "spread_hottest_cluster",
        "move_hottest_cluster_toward_sink",
        "reduce_local_congestion",
    ]
    state.metadata["prompt_panels"]["operator_panel"]["reduce_local_congestion"] = {
        "entry_fit": "supported",
        "preserve_fit": "supported",
        "expand_fit": "trusted",
        "recent_regression_risk": "low",
        "frontier_evidence": "positive",
        "applicability": "high",
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "improve",
        "expected_feasibility_risk": "low",
        "spatial_match_reason": "closest packed components indicate a local congestion bottleneck.",
    }
    state.metadata["operator_summary"]["reduce_local_congestion"] = {
        "selection_count": 4,
        "recent_selection_count": 0,
        "proposal_count": 4,
        "feasible_preservation_count": 2,
        "pareto_contribution_count": 1,
    }
    return state


def _route_rebalanced_expand_state() -> ControllerState:
    state = _route_diverse_expand_state()
    state.metadata["recent_decisions"] = [
        {
            "evaluation_index": 86 + idx,
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
    ]
    state.metadata["operator_summary"]["spread_hottest_cluster"]["recent_selection_count"] = 5
    state.metadata["operator_summary"]["spread_hottest_cluster"]["feasible_regression_count"] = 4
    state.metadata["operator_summary"]["move_hottest_cluster_toward_sink"]["pareto_contribution_count"] = 2
    state.metadata["operator_summary"]["move_hottest_cluster_toward_sink"]["post_feasible_avg_objective_delta"] = -0.15
    state.metadata["operator_summary"]["reduce_local_congestion"]["feasible_preservation_count"] = 0
    state.metadata["operator_summary"]["reduce_local_congestion"]["pareto_contribution_count"] = 0
    return state


def _route_dominance_capped_expand_state() -> ControllerState:
    state = _route_rebalanced_expand_state()
    state.metadata["operator_summary"]["spread_hottest_cluster"]["pareto_contribution_count"] = 4
    state.metadata["operator_summary"]["spread_hottest_cluster"]["feasible_regression_count"] = 1
    return state


def _expand_budget_throttled_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=84,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "local_refine",
                "spread_hottest_cluster",
                "smooth_high_gradient_band",
            ],
            "run_state": {
                "decision_index": 24,
                "evaluations_used": 83,
                "evaluations_remaining": 46,
                "feasible_rate": 0.28,
                "first_feasible_eval": 49,
                "peak_temperature": 309.7,
                "temperature_gradient_rms": 11.8,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 2,
                "recent_frontier_stagnation_count": 4,
            },
            "domain_regime": {
                "phase": "feasible_refine",
                "dominant_constraint_family": "thermal_limit",
                "sink_budget_utilization": 0.9,
            },
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 83,
                    "evaluations_remaining": 46,
                    "feasible_rate": 0.28,
                    "first_feasible_eval": 49,
                    "peak_temperature": 309.7,
                    "temperature_gradient_rms": 11.8,
                    "pareto_size": 4,
                },
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "dominant_violation_persistence_count": 0,
                    "sink_budget_utilization": 0.9,
                    "entry_pressure": "low",
                    "preservation_pressure": "medium",
                    "frontier_pressure": "high",
                },
                "parent_panel": {
                    "closest_to_feasible_parent": None,
                    "strongest_feasible_parent": {
                        "evaluation_index": 82,
                        "feasible": True,
                        "objective_summary": {"minimize_peak_temperature": 309.7},
                    },
                },
                "spatial_panel": {
                    "hotspot_to_sink_offset": 0.01,
                    "hotspot_inside_sink_window": True,
                    "hottest_cluster_compactness": 0.08,
                    "nearest_neighbor_gap_min": 0.13,
                    "sink_budget_bucket": "available",
                },
                "operator_panel": {
                    "native_sbx_pm": {
                        "entry_fit": "supported",
                        "preserve_fit": "trusted",
                        "expand_fit": "supported",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "limited",
                        "applicability": "medium",
                        "expected_peak_effect": "neutral",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "spatial_match_reason": "native baseline crossover remains a safe fallback anchor.",
                    },
                    "local_refine": {
                        "entry_fit": "supported",
                        "preserve_fit": "trusted",
                        "expand_fit": "supported",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "positive",
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "improve",
                        "expected_feasibility_risk": "low",
                        "spatial_match_reason": "current regime favors low-risk local cleanup around the incumbent basin.",
                    },
                    "spread_hottest_cluster": {
                        "entry_fit": "weak",
                        "preserve_fit": "weak",
                        "expand_fit": "supported",
                        "recent_regression_risk": "high",
                        "frontier_evidence": "limited",
                        "recent_expand_preserve_credit": 0,
                        "recent_expand_regression_credit": 2,
                        "recent_expand_frontier_credit": 0,
                        "expand_budget_status": "throttled",
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "improve",
                        "expected_feasibility_risk": "low",
                        "spatial_match_reason": "hot cluster already sits inside the sink corridor, so a bounded spread is the direct way to open local space without retargeting the sink.",
                    },
                    "smooth_high_gradient_band": {
                        "entry_fit": "weak",
                        "preserve_fit": "supported",
                        "expand_fit": "trusted",
                        "recent_regression_risk": "low",
                        "frontier_evidence": "positive",
                        "recent_expand_preserve_credit": 1,
                        "recent_expand_regression_credit": 0,
                        "recent_expand_frontier_credit": 1,
                        "expand_budget_status": "preferred",
                        "applicability": "high",
                        "expected_peak_effect": "neutral",
                        "expected_gradient_effect": "improve",
                        "expected_feasibility_risk": "low",
                        "spatial_match_reason": "post-feasible refinement is still gradient-limited in the current regime.",
                    },
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 78,
                    "selected_operator_id": "spread_hottest_cluster",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 79,
                    "selected_operator_id": "local_refine",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 80,
                    "selected_operator_id": "smooth_high_gradient_band",
                    "fallback_used": False,
                    "llm_valid": True,
                },
            ],
            "recent_operator_counts": {
                "spread_hottest_cluster": {
                    "recent_selection_count": 1,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 1,
                },
                "smooth_high_gradient_band": {
                    "recent_selection_count": 1,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 1,
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 11,
                    "recent_selection_count": 0,
                    "proposal_count": 11,
                    "feasible_preservation_count": 3,
                },
                "local_refine": {
                    "selection_count": 14,
                    "recent_selection_count": 1,
                    "proposal_count": 14,
                    "feasible_preservation_count": 4,
                },
                "spread_hottest_cluster": {
                    "selection_count": 6,
                    "recent_selection_count": 1,
                    "proposal_count": 6,
                    "pareto_contribution_count": 1,
                    "feasible_regression_count": 1,
                    "recent_expand_selection_count": 2,
                    "recent_expand_feasible_preservation_count": 0,
                    "recent_expand_feasible_regression_count": 2,
                    "recent_expand_frontier_add_count": 0,
                },
                "smooth_high_gradient_band": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                    "pareto_contribution_count": 1,
                    "post_feasible_avg_objective_delta": -0.18,
                    "recent_expand_selection_count": 1,
                    "recent_expand_feasible_preservation_count": 1,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 1,
                },
            },
        },
    )


def test_llm_controller_metrics_count_retries_and_invalid_attempts() -> None:
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=_RetryThenSuccessLLMClient(),
    )

    decision = controller.select_decision(
        _state(),
        ("native_sbx_pm", "local_refine"),
        np.random.default_rng(7),
    )

    assert decision.selected_operator_id == "local_refine"
    assert controller.metrics["retry_count"] == 1
    assert controller.metrics["invalid_response_count"] == 1
    assert controller.metrics["schema_invalid_count"] == 1


def test_llm_controller_builds_semantic_operator_prompt_and_metadata() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="move_hottest_cluster_toward_sink",
            phase="post_feasible_expand",
            rationale="Recent evidence supports clustering heat closer to the sink corridor.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "move_hottest_cluster_toward_sink"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    decision = controller.select_decision(
        _domain_grounded_state(),
        (
            "native_sbx_pm",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
        np.random.default_rng(11),
    )

    assert decision.selected_operator_id == "move_hottest_cluster_toward_sink"
    assert client.last_kwargs is not None
    system_prompt = str(client.last_kwargs["system_prompt"])
    assert "move_hottest_cluster_toward_sink" in system_prompt
    assert "repair_sink_budget" in system_prompt
    assert "hot_pair" not in system_prompt
    assert "battery" not in system_prompt

    user_payload = json.loads(str(client.last_kwargs["user_prompt"]))
    metadata = user_payload["metadata"]
    assert metadata["prompt_panels"]["run_panel"]["peak_temperature"] == pytest.approx(344.8)
    assert metadata["prompt_panels"]["run_panel"]["temperature_gradient_rms"] == pytest.approx(8.7)
    assert metadata["prompt_panels"]["regime_panel"]["phase"] == "post_feasible_expand"
    assert metadata["prompt_panels"]["operator_panel"]["move_hottest_cluster_toward_sink"]["preserve_fit"] == "trusted"
    assert "run_state" not in metadata
    assert "parent_state" not in metadata
    assert "archive_state" not in metadata
    assert "domain_regime" not in metadata
    assert "progress_state" not in metadata
    assert "problem_history" not in metadata
    assert "case_reports" not in metadata


def test_llm_system_prompt_prioritizes_first_feasible_before_pareto_in_prefeasible_convert() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="repair_sink_budget",
            phase="prefeasible_convert",
            rationale="Cross the feasibility boundary before chasing frontier novelty.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "repair_sink_budget"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _prefeasible_convert_state(),
        (
            "native_sbx_pm",
            "repair_sink_budget",
            "move_hottest_cluster_toward_sink",
        ),
        np.random.default_rng(5),
    )

    assert client.last_kwargs is not None
    system_prompt = str(client.last_kwargs["system_prompt"])
    assert "first feasible conversion" in system_prompt
    assert "before frontier growth or Pareto novelty" in system_prompt
    assert "protect stable near-feasible progress" in system_prompt


def test_llm_controller_recent_dominance_guardrail_filters_repeated_semantic_operator() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="prefeasible_progress",
            rationale="Avoid repeating the same custom move while the window is collapsed.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    decision = controller.select_decision(
        _dominance_state(),
        (
            "native_sbx_pm",
            "move_hottest_cluster_toward_sink",
            "local_refine",
        ),
        np.random.default_rng(19),
    )

    assert decision.selected_operator_id == "local_refine"
    assert decision.metadata["guardrail_filtered_operator_ids"] == ["move_hottest_cluster_toward_sink"]
    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine")
    assert controller.request_trace[0]["guardrail"]["filtered_operator_ids"] == ["move_hottest_cluster_toward_sink"]


def test_llm_controller_request_can_include_semantic_candidates_post_feasible() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="slide_sink",
            phase="post_feasible_recover",
            rationale="Keep one semantic retargeting option visible during recover mode.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "slide_sink"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    decision = controller.select_decision(
        _post_feasible_collapse_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "slide_sink",
            "repair_sink_budget",
            "move_hottest_cluster_toward_sink",
        ),
        np.random.default_rng(23),
    )

    assert decision.selected_operator_id == "slide_sink"
    assert client.last_kwargs is not None
    assert "slide_sink" in tuple(client.last_kwargs["candidate_operator_ids"])


def test_llm_controller_prompt_requests_intent_before_operator_choice() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="move_hottest_cluster_toward_sink",
            phase="post_feasible_expand",
            rationale="Choose sink_retarget intent before mapping to the operator.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_intent": "sink_retarget",
                "selected_operator_id": "move_hottest_cluster_toward_sink",
            },
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _domain_grounded_state(),
        (
            "native_sbx_pm",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    assert "intent" in str(client.last_kwargs["system_prompt"]).lower()
    assert "preserve_score" in str(client.last_kwargs["user_prompt"])
    assert "frontier_score" in str(client.last_kwargs["user_prompt"])


def test_llm_controller_prompt_includes_retrieved_episode_context() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="slide_sink",
            phase="post_feasible_expand",
            rationale="Matched historical expansion episodes favor sink retargeting here.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "slide_sink"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _retrieval_rich_state(),
        (
            "native_sbx_pm",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    assert "matched_episodes" in str(client.last_kwargs["user_prompt"])


def test_llm_controller_prompt_marks_sink_aligned_expand_as_bounded_semantic_trial() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="spread_hottest_cluster",
            phase="post_feasible_expand",
            rationale="The hotspot is already sink-aligned, so a bounded spread is the right semantic trial.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_intent": "hotspot_spread",
                "selected_operator_id": "spread_hottest_cluster",
            },
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _semantic_trial_state(),
        (
            "native_sbx_pm",
            "spread_hottest_cluster",
            "move_hottest_cluster_toward_sink",
        ),
        np.random.default_rng(13),
    )

    assert client.last_kwargs is not None
    system_prompt = str(client.last_kwargs["system_prompt"]).lower()
    user_payload = json.loads(str(client.last_kwargs["user_prompt"]))
    decision_axes = user_payload["metadata"]["decision_axes"]

    assert "bounded semantic trial" in system_prompt
    assert decision_axes["semantic_trial_mode"] == "encourage_bounded_trial"
    assert decision_axes["semantic_trial_candidates"] == ["spread_hottest_cluster"]
    assert decision_axes["semantic_trial_reason"] == "sink_aligned_compact_hotspot"


def test_llm_controller_prompt_exposes_multiple_semantic_route_family_candidates_in_expand() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="spread_hottest_cluster",
            phase="post_feasible_expand",
            rationale="Choose across multiple semantic route families before mapping to the operator.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_intent": "hotspot_spread",
                "selected_operator_id": "spread_hottest_cluster",
            },
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _route_diverse_expand_state(),
        (
            "native_sbx_pm",
            "spread_hottest_cluster",
            "move_hottest_cluster_toward_sink",
            "reduce_local_congestion",
        ),
        np.random.default_rng(29),
    )

    assert client.last_kwargs is not None
    user_payload = json.loads(str(client.last_kwargs["user_prompt"]))
    decision_axes = user_payload["metadata"]["decision_axes"]

    assert decision_axes["route_stage"] == "family_then_operator"
    assert decision_axes["route_family_mode"] == "bounded_expand_mix"
    assert set(decision_axes["route_family_candidates"]) >= {
        "hotspot_spread",
        "sink_retarget",
        "congestion_relief",
    }


def test_llm_controller_system_prompt_mentions_route_family_allocation_in_expand_mix() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="spread_hottest_cluster",
            phase="post_feasible_expand",
            rationale="Use route-family allocation before selecting the final operator.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_intent": "hotspot_spread",
                "selected_operator_id": "spread_hottest_cluster",
            },
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _route_diverse_expand_state(),
        (
            "native_sbx_pm",
            "spread_hottest_cluster",
            "move_hottest_cluster_toward_sink",
            "reduce_local_congestion",
        ),
        np.random.default_rng(31),
    )

    assert client.last_kwargs is not None
    system_prompt = str(client.last_kwargs["system_prompt"]).lower()
    assert "route family" in system_prompt
    assert "bounded expand mix" in system_prompt


def test_llm_controller_expand_request_rebalances_away_from_cooled_route_family() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="move_hottest_cluster_toward_sink",
            phase="post_feasible_expand",
            rationale="Hotspot-spread is cooled down, so rebalance toward underused route families first.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_intent": "sink_retarget",
                "selected_operator_id": "move_hottest_cluster_toward_sink",
            },
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _route_rebalanced_expand_state(),
        (
            "native_sbx_pm",
            "spread_hottest_cluster",
            "move_hottest_cluster_toward_sink",
            "reduce_local_congestion",
            "local_refine",
        ),
        np.random.default_rng(37),
    )

    assert client.last_kwargs is not None
    candidate_operator_ids = tuple(client.last_kwargs["candidate_operator_ids"])
    assert "spread_hottest_cluster" not in candidate_operator_ids
    assert "native_sbx_pm" in candidate_operator_ids
    assert "local_refine" in candidate_operator_ids
    assert "move_hottest_cluster_toward_sink" in candidate_operator_ids
    assert "reduce_local_congestion" in candidate_operator_ids


def test_llm_controller_expand_request_caps_recently_dominant_route_family() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="move_hottest_cluster_toward_sink",
            phase="post_feasible_expand",
            rationale="Recent hotspot-spread dominance should be capped before asking the model to expand again.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_intent": "sink_retarget",
                "selected_operator_id": "move_hottest_cluster_toward_sink",
            },
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _route_dominance_capped_expand_state(),
        (
            "native_sbx_pm",
            "spread_hottest_cluster",
            "move_hottest_cluster_toward_sink",
            "reduce_local_congestion",
            "local_refine",
        ),
        np.random.default_rng(41),
    )

    assert client.last_kwargs is not None
    assert "spread_hottest_cluster" not in client.last_kwargs["candidate_operator_ids"]


def test_llm_controller_expand_request_marks_regression_dominant_semantic_route_as_throttled() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="smooth_high_gradient_band",
            phase="post_feasible_expand",
            rationale="Keep the gradient-smoothing semantic route available and suppress the regressing hotspot-spread route.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_intent": "local_cleanup",
                "selected_operator_id": "smooth_high_gradient_band",
            },
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _expand_budget_throttled_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "spread_hottest_cluster",
            "smooth_high_gradient_band",
        ),
        np.random.default_rng(43),
    )

    assert client.last_kwargs is not None
    candidate_operator_ids = tuple(client.last_kwargs["candidate_operator_ids"])
    assert "spread_hottest_cluster" not in candidate_operator_ids
    assert "smooth_high_gradient_band" in candidate_operator_ids


def test_llm_controller_recover_request_retains_stable_floor_when_semantic_preserver_exists() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="post_feasible_recover",
            rationale="Recover should keep stable routes visible instead of collapsing to one semantic cleanup move.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=client,
    )

    controller.select_decision(
        _recover_semantic_monopoly_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "spread_hottest_cluster",
            "smooth_high_gradient_band",
            "reduce_local_congestion",
        ),
        np.random.default_rng(43),
    )

    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "smooth_high_gradient_band",
    )
