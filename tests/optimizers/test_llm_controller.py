from __future__ import annotations

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
