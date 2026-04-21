from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from llm.openai_compatible.client import OpenAICompatibleDecision
from optimizers.operator_pool.llm_controller import LLMOperatorController
from optimizers.operator_pool.policy_kernel import PolicySnapshot
from optimizers.operator_pool.state import ControllerState
from optimizers.traces.prompt_store import PromptStore


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


def _generation_local_dominance_state(*, viable_alternative: bool) -> ControllerState:
    operator_panel = {
        "native_sbx_pm": {
            "applicability": "low",
            "expected_peak_effect": "neutral",
            "expected_gradient_effect": "neutral",
            "expected_feasibility_risk": "low",
            "recent_regression_risk": "low",
        },
        "local_refine": {
            "applicability": "high" if viable_alternative else "low",
            "expected_peak_effect": "improve",
            "expected_gradient_effect": "neutral",
            "expected_feasibility_risk": "low",
            "recent_regression_risk": "low",
        },
        "slide_sink": {
            "applicability": "high",
            "expected_peak_effect": "improve",
            "expected_gradient_effect": "neutral",
            "expected_feasibility_risk": "low",
            "recent_regression_risk": "low",
        },
    }
    generation_panel = {
        "accepted_count": 4,
        "target_offsprings": 20,
        "accepted_share": 0.2,
        "dominant_operator_id": "slide_sink",
        "dominant_operator_count": 4,
        "dominant_operator_share": 1.0,
        "dominant_operator_streak": 4,
        "operator_counts": {
            "slide_sink": {
                "accepted_count": 4,
                "accepted_share": 1.0,
            }
        },
    }
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=162,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "local_refine",
                "slide_sink",
            ],
            "run_state": {
                "decision_index": 58,
                "evaluations_used": 161,
                "evaluations_remaining": 40,
                "feasible_rate": 1.0,
                "first_feasible_eval": 21,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 4,
                "recent_frontier_stagnation_count": 8,
            },
            "generation_local_memory": generation_panel,
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "preservation_pressure": "medium",
                    "frontier_pressure": "high",
                    "objective_balance": {
                        "stagnant_objectives": ["temperature_max", "gradient_rms"],
                        "improving_objectives": [],
                        "balance_pressure": "medium",
                        "preferred_effect": "balanced",
                    },
                },
                "operator_panel": operator_panel,
                "generation_panel": generation_panel,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 10,
                    "recent_selection_count": 0,
                    "proposal_count": 10,
                    "feasible_preservation_count": 4,
                },
                "local_refine": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "feasible_preservation_count": 4,
                },
                "slide_sink": {
                    "selection_count": 18,
                    "recent_selection_count": 4,
                    "proposal_count": 18,
                    "pareto_contribution_count": 3,
                    "post_feasible_avg_objective_delta": -0.2,
                },
            },
            "recent_decisions": [],
            "recent_operator_counts": {},
        },
    )


def _generation_local_strategy_group_state() -> ControllerState:
    generation_panel = {
        "accepted_count": 6,
        "target_offsprings": 20,
        "accepted_share": 0.3,
        "dominant_operator_id": "slide_sink",
        "dominant_operator_count": 3,
        "dominant_operator_share": 0.5,
        "dominant_operator_streak": 1,
        "operator_counts": {
            "slide_sink": {
                "accepted_count": 3,
                "accepted_share": 0.5,
            },
            "repair_sink_budget": {
                "accepted_count": 3,
                "accepted_share": 0.5,
            },
        },
    }
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=9,
        evaluation_index=168,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "local_refine",
                "move_hottest_cluster_toward_sink",
                "repair_sink_budget",
                "slide_sink",
            ],
            "run_state": {
                "decision_index": 64,
                "evaluations_used": 167,
                "evaluations_remaining": 34,
                "feasible_rate": 1.0,
                "first_feasible_eval": 21,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 4,
                "recent_frontier_stagnation_count": 9,
            },
            "generation_local_memory": generation_panel,
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
                        "expected_feasibility_risk": "medium",
                        "recent_regression_risk": "high",
                    },
                    "move_hottest_cluster_toward_sink": {
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "medium",
                        "recent_regression_risk": "high",
                    },
                    "repair_sink_budget": {
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                    "slide_sink": {
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                },
                "generation_panel": generation_panel,
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 12,
                    "recent_selection_count": 0,
                    "proposal_count": 12,
                    "feasible_preservation_count": 5,
                },
                "local_refine": {
                    "selection_count": 11,
                    "recent_selection_count": 1,
                    "proposal_count": 11,
                    "feasible_preservation_count": 4,
                },
                "move_hottest_cluster_toward_sink": {
                    "selection_count": 3,
                    "recent_selection_count": 0,
                    "proposal_count": 3,
                    "pareto_contribution_count": 1,
                    "post_feasible_avg_objective_delta": -0.1,
                },
                "repair_sink_budget": {
                    "selection_count": 9,
                    "recent_selection_count": 3,
                    "proposal_count": 9,
                    "pareto_contribution_count": 2,
                    "post_feasible_avg_objective_delta": -0.2,
                },
                "slide_sink": {
                    "selection_count": 14,
                    "recent_selection_count": 3,
                    "proposal_count": 14,
                    "pareto_contribution_count": 3,
                    "post_feasible_avg_objective_delta": -0.25,
                },
            },
            "recent_decisions": [],
            "recent_operator_counts": {},
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


def _make_minimal_llm_state(*, objective_balance: dict[str, object] | None = None) -> ControllerState:
    metadata: dict[str, object] = {
        "run_state": {"first_feasible_eval": 10},
        "prompt_panels": {
            "regime_panel": {
                "phase": "post_feasible_expand",
                "preservation_pressure": "medium",
                "frontier_pressure": "high",
            },
            "operator_panel": {
                "slide_sink": {
                    "applicability": "high",
                    "expected_peak_effect": "improve",
                    "expected_gradient_effect": "neutral",
                    "expected_feasibility_risk": "low",
                    "recent_regression_risk": "low",
                },
                "native_sbx_pm": {
                    "applicability": "medium",
                    "expected_peak_effect": "neutral",
                    "expected_gradient_effect": "neutral",
                    "expected_feasibility_risk": "low",
                    "recent_regression_risk": "low",
                },
            },
            "spatial_panel": {},
        },
    }
    if objective_balance is not None:
        regime_panel = dict(metadata["prompt_panels"]["regime_panel"])
        regime_panel["objective_balance"] = objective_balance
        metadata["prompt_panels"] = dict(metadata["prompt_panels"])
        metadata["prompt_panels"]["regime_panel"] = regime_panel
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=80,
        parent_count=2,
        vector_size=32,
        metadata=metadata,
    )


def _recover_gradient_pressure_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=88,
        parent_count=2,
        vector_size=32,
        metadata={
            "decision_index": 11,
            "run_state": {
                "first_feasible_eval": 12,
                "evaluations_used": 87,
                "evaluations_remaining": 40,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
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
                "generation_panel": {
                    "accepted_count": 0,
                    "dominant_operator_id": "",
                    "dominant_operator_share": 0.0,
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
                    "smooth_high_gradient_band": {
                        "applicability": "high",
                        "expected_peak_effect": "neutral",
                        "expected_gradient_effect": "improve",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                    "reduce_local_congestion": {
                        "applicability": "high",
                        "expected_peak_effect": "neutral",
                        "expected_gradient_effect": "improve",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                    "move_hottest_cluster_toward_sink": {
                        "applicability": "medium",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "medium",
                        "recent_regression_risk": "medium",
                    },
                },
                "spatial_panel": {
                    "hotspot_inside_sink_window": False,
                    "nearest_neighbor_gap_min": 0.04,
                    "hottest_cluster_compactness": 0.11,
                },
            },
        },
    )


def _recover_positive_budget_credit_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=92,
        parent_count=2,
        vector_size=32,
        metadata={
            "decision_index": 12,
            "run_state": {
                "first_feasible_eval": 12,
                "evaluations_used": 91,
                "evaluations_remaining": 36,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "recover",
                "recover_pressure_level": "medium",
                "recover_exit_ready": False,
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
                "generation_panel": {
                    "accepted_count": 0,
                    "dominant_operator_id": "",
                    "dominant_operator_share": 0.0,
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
                    "move_hottest_cluster_toward_sink": {
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
                    "repair_sink_budget": {
                        "applicability": "high",
                        "expected_peak_effect": "improve",
                        "expected_gradient_effect": "neutral",
                        "expected_feasibility_risk": "low",
                        "recent_regression_risk": "low",
                    },
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


def test_llm_controller_generation_local_guardrail_filters_current_generation_monopoly() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="post_feasible_expand",
            rationale="The generation is already saturated with slide_sink, so diversify into another viable peak improver.",
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
        _generation_local_dominance_state(viable_alternative=True),
        (
            "native_sbx_pm",
            "local_refine",
            "slide_sink",
        ),
        np.random.default_rng(23),
    )

    assert decision.selected_operator_id == "local_refine"
    assert decision.metadata["guardrail_reason"] == "generation_local_operator_dominance"
    assert decision.metadata["guardrail_filtered_operator_ids"] == ["slide_sink"]
    assert decision.metadata["guardrail_viable_alternative_operator_ids"] == ["local_refine"]
    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine")


def test_llm_controller_generation_local_guardrail_keeps_unique_viable_operator() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="slide_sink",
            phase="post_feasible_expand",
            rationale="slide_sink is still the only viable peak-improving option here.",
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
        _generation_local_dominance_state(viable_alternative=False),
        (
            "native_sbx_pm",
            "local_refine",
            "slide_sink",
        ),
        np.random.default_rng(29),
    )

    assert decision.selected_operator_id == "slide_sink"
    assert "guardrail_reason" not in decision.metadata
    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine", "slide_sink")


def test_llm_controller_generation_local_strategy_group_guardrail_filters_sink_rotation() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="post_feasible_expand",
            rationale="The generation is over-concentrated in sink retargeting moves, so switch to a different peak-improving pathway.",
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
        _generation_local_strategy_group_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
            "slide_sink",
        ),
        np.random.default_rng(31),
    )

    assert decision.selected_operator_id == "local_refine"
    assert decision.metadata["guardrail_reason"] == "generation_local_strategy_group_dominance"
    assert decision.metadata["guardrail_filtered_operator_ids"] == ["repair_sink_budget", "slide_sink"]
    assert decision.metadata["guardrail_viable_alternative_operator_ids"] == [
        "local_refine",
        "move_hottest_cluster_toward_sink",
    ]
    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == (
        "native_sbx_pm",
        "local_refine",
        "move_hottest_cluster_toward_sink",
    )


def test_decision_axes_objective_balance_fields() -> None:
    """decision_axes should include objective_balance_pressure and preferred_effect from regime_panel."""
    metadata = {
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
            },
            "operator_panel": {
                "slide_sink": {
                    "applicability": "high",
                    "expected_peak_effect": "improve",
                    "expected_gradient_effect": "neutral",
                    "expected_feasibility_risk": "low",
                    "recent_regression_risk": "low",
                },
                "native_sbx_pm": {
                    "applicability": "medium",
                    "expected_peak_effect": "neutral",
                    "expected_gradient_effect": "neutral",
                    "expected_feasibility_risk": "low",
                    "recent_regression_risk": "low",
                },
            },
            "spatial_panel": {"hotspot_inside_sink_window": False},
        },
    }

    axes = LLMOperatorController._build_decision_axes(metadata)

    assert axes["objective_balance_pressure"] == "high"
    assert axes["preferred_effect"] == "peak_improve"
    assert "slide_sink" in axes["peak_improve_candidates"]


def test_decision_axes_enable_route_family_reasoning_during_recover_gradient_pressure() -> None:
    axes = LLMOperatorController._build_decision_axes(
        {"prompt_panels": dict(_recover_gradient_pressure_state().metadata["prompt_panels"])}
    )

    assert axes["preferred_effect"] == "gradient_improve"
    assert axes["route_stage"] == "family_then_operator"
    assert axes["route_family_mode"] == "recover_family_mix"
    assert axes["semantic_trial_mode"] == "encourage_bounded_trial"
    assert "congestion_relief" in axes["route_family_candidates"]
    assert "smooth_high_gradient_band" in axes["semantic_trial_candidates"]
    assert "reduce_local_congestion" in axes["semantic_trial_candidates"]


def test_system_prompt_objective_balance_guidance() -> None:
    """system_prompt should mention objective balance alert when balance_pressure is high."""
    from optimizers.operator_pool.policy_kernel import PolicySnapshot

    policy_snapshot = PolicySnapshot(
        phase="post_feasible_expand",
        allowed_operator_ids=("native_sbx_pm", "slide_sink"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=(),
        candidate_annotations={},
    )
    state = _make_minimal_llm_state(
        objective_balance={
            "balance_pressure": "high",
            "preferred_effect": "peak_improve",
            "stagnant_objectives": ["temperature_max"],
            "improving_objectives": ["gradient_rms"],
        }
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
        client=_FakeLLMClient(
            OpenAICompatibleDecision(
                selected_operator_id="slide_sink",
                phase="post_feasible_expand",
                rationale="Favor peak improvement.",
                provider="openai-compatible",
                model="GPT-5.4",
                capability_profile="responses_native",
                performance_profile="balanced",
                raw_payload={"selected_operator_id": "slide_sink"},
            )
        ),
    )
    prompt = controller._build_system_prompt(
        state,
        ("native_sbx_pm", "slide_sink"),
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    assert "Objective balance alert" in prompt
    assert "temperature_max" in prompt


def test_llm_controller_input_state_digest_accepts_tuple_key_metadata() -> None:
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=17,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
            "route_family_counts": {
                ("sink_retarget", "hotspot_shift"): {
                    "count": 3,
                }
            },
        },
    )
    policy_snapshot = PolicySnapshot(
        phase="prefeasible_progress",
        allowed_operator_ids=("native_sbx_pm", "local_refine"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=("policy_kernel",),
        candidate_annotations={},
    )

    digest = LLMOperatorController._input_state_digest(
        state,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        policy_snapshot=policy_snapshot,
        guardrail={
            "filtered_operator_ids": ["local_refine"],
            "generation_local_memory": {("sink", "budget"): 2},
        },
    )

    assert isinstance(digest, str)
    assert len(digest) == 40


def test_llm_controller_request_trace_exposes_route_visibility_fields(tmp_path: Path) -> None:
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=_FakeLLMClient(
            OpenAICompatibleDecision(
                selected_operator_id="reduce_local_congestion",
                phase="post_feasible_recover",
                rationale="Gradient pressure favors a bounded congestion-relief move.",
                provider="openai-compatible",
                model="GPT-5.4",
                capability_profile="responses_native",
                performance_profile="balanced",
                raw_payload={"selected_operator_id": "reduce_local_congestion"},
            )
        ),
    )
    run_root = tmp_path / "run"
    controller.configure_trace_outputs(
        controller_trace_path=run_root / "traces" / "controller_trace.jsonl",
        llm_request_trace_path=run_root / "traces" / "llm_request_trace.jsonl",
        llm_response_trace_path=run_root / "traces" / "llm_response_trace.jsonl",
        prompt_store=PromptStore(run_root / "prompts"),
    )

    controller.select_decision(
        _recover_gradient_pressure_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "smooth_high_gradient_band",
            "reduce_local_congestion",
            "move_hottest_cluster_toward_sink",
        ),
        np.random.default_rng(13),
    )

    request_entry = controller.request_trace[0]
    assert request_entry["route_family_mode"] == "recover_family_mix"
    assert request_entry["semantic_trial_mode"] == "encourage_bounded_trial"
    assert "stable_local" in request_entry["original_route_families"]
    assert "congestion_relief" in request_entry["visible_route_families"]
    assert request_entry["preferred_effect"] == "gradient_improve"
    assert request_entry["recover_exit_ready"] is False
    assert request_entry["effective_candidate_pool_size"] >= 3

    request_rows = [
        json.loads(line)
        for line in (run_root / "traces" / "llm_request_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert request_rows[0]["route_family_mode"] == "recover_family_mix"
    assert request_rows[0]["semantic_trial_mode"] == "encourage_bounded_trial"
    assert "stable_local" in request_rows[0]["original_route_families"]
    assert "congestion_relief" in request_rows[0]["visible_route_families"]
    assert request_rows[0]["preferred_effect"] == "gradient_improve"
    assert request_rows[0]["recover_exit_ready"] is False
    assert request_rows[0]["effective_candidate_pool_size"] >= 3


def test_llm_controller_request_trace_keeps_positive_budget_guard_family_visible(tmp_path: Path) -> None:
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=_FakeLLMClient(
            OpenAICompatibleDecision(
                selected_operator_id="move_hottest_cluster_toward_sink",
                phase="post_feasible_recover",
                rationale="Use the currently visible sink-retarget route.",
                provider="openai-compatible",
                model="GPT-5.4",
                capability_profile="responses_native",
                performance_profile="balanced",
                raw_payload={"selected_operator_id": "move_hottest_cluster_toward_sink"},
            )
        ),
    )
    run_root = tmp_path / "run"
    controller.configure_trace_outputs(
        controller_trace_path=run_root / "traces" / "controller_trace.jsonl",
        llm_request_trace_path=run_root / "traces" / "llm_request_trace.jsonl",
        llm_response_trace_path=run_root / "traces" / "llm_response_trace.jsonl",
        prompt_store=PromptStore(run_root / "prompts"),
    )

    controller.select_decision(
        _recover_positive_budget_credit_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
        np.random.default_rng(17),
    )

    request_entry = controller.request_trace[0]
    assert "budget_guard" in request_entry["visible_route_families"]


def test_llm_controller_request_trace_exposes_suppressed_route_families_with_reasons(tmp_path: Path) -> None:
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=_FakeLLMClient(
            OpenAICompatibleDecision(
                selected_operator_id="reduce_local_congestion",
                phase="post_feasible_recover",
                rationale="Gradient pressure favors a bounded congestion-relief move.",
                provider="openai-compatible",
                model="GPT-5.4",
                capability_profile="responses_native",
                performance_profile="balanced",
                raw_payload={"selected_operator_id": "reduce_local_congestion"},
            )
        ),
    )
    run_root = tmp_path / "run"
    controller.configure_trace_outputs(
        controller_trace_path=run_root / "traces" / "controller_trace.jsonl",
        llm_request_trace_path=run_root / "traces" / "llm_request_trace.jsonl",
        llm_response_trace_path=run_root / "traces" / "llm_response_trace.jsonl",
        prompt_store=PromptStore(run_root / "prompts"),
    )

    controller.select_decision(
        _recover_gradient_pressure_state(),
        (
            "native_sbx_pm",
            "local_refine",
            "smooth_high_gradient_band",
            "reduce_local_congestion",
            "move_hottest_cluster_toward_sink",
        ),
        np.random.default_rng(19),
    )

    request_entry = controller.request_trace[0]
    assert request_entry["suppressed_route_families"]
    for route_family in request_entry["suppressed_route_families"]:
        assert request_entry["suppressed_route_family_reasons"][route_family]
