from __future__ import annotations

import json

import numpy as np
import pytest

from llm.openai_compatible.client import OpenAICompatibleDecision
from optimizers.operator_pool.decisions import ControllerDecision
import optimizers.operator_pool.llm_controller as llm_controller_module
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


def _state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=12,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
        },
    )


def _collapsed_state() -> ControllerState:
    recent_selected_operator_ids = (
        "hot_pair_to_sink",
        "hot_pair_to_sink",
        "hot_pair_to_sink",
        "hot_pair_to_sink",
        "hot_pair_to_sink",
        "native_sbx_pm",
        "hot_pair_to_sink",
        "local_refine",
    )
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=48,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "hot_pair_to_sink", "local_refine"],
            "recent_decisions": [
                {
                    "generation_index": 5,
                    "evaluation_index": 40 + index,
                    "selected_operator_id": operator_id,
                    "metadata": {"decision_index": index},
                }
                for index, operator_id in enumerate(recent_selected_operator_ids)
            ],
            "operator_summary": {
                "hot_pair_to_sink": {
                    "selection_count": 19,
                    "recent_selection_count": 6,
                    "proposal_count": 19,
                },
                "native_sbx_pm": {
                    "selection_count": 6,
                    "recent_selection_count": 1,
                    "proposal_count": 6,
                },
                "local_refine": {
                    "selection_count": 4,
                    "recent_selection_count": 1,
                    "proposal_count": 4,
                },
            },
        },
    )


def _fallback_dominated_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=7,
        evaluation_index=64,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "hot_pair_to_sink", "local_refine"],
            "parent_indices": [3, 8],
            "native_parameters": {"crossover": {"eta": 10}},
            "recent_decisions": [
                {
                    "evaluation_index": 56 + index,
                    "selected_operator_id": "hot_pair_to_sink" if index < 6 else "local_refine",
                    "fallback_used": index < 6,
                    "llm_valid": index >= 6,
                }
                for index in range(8)
            ],
            "recent_operator_counts": {
                "hot_pair_to_sink": {
                    "recent_selection_count": 6,
                    "recent_fallback_selection_count": 6,
                    "recent_llm_valid_selection_count": 0,
                },
                "local_refine": {
                    "recent_selection_count": 2,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 2,
                },
            },
            "operator_summary": {
                "hot_pair_to_sink": {
                    "selection_count": 12,
                    "recent_selection_count": 6,
                    "fallback_selection_count": 6,
                    "llm_valid_selection_count": 0,
                    "recent_fallback_selection_count": 6,
                    "recent_llm_valid_selection_count": 0,
                    "proposal_count": 12,
                },
                "local_refine": {
                    "selection_count": 5,
                    "recent_selection_count": 2,
                    "fallback_selection_count": 0,
                    "llm_valid_selection_count": 5,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 2,
                    "proposal_count": 5,
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
        vector_size=8,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": ["native_sbx_pm", "hot_pair_to_sink", "local_refine"],
            "run_state": {
                "decision_index": 12,
                "evaluations_used": 63,
                "evaluations_remaining": 66,
                "feasible_rate": 0.17,
                "first_feasible_eval": 45,
            },
            "parent_state": {
                "parent_indices": [3, 8],
                "parents": [
                    {
                        "decision_vector": {"processor_x": 0.22, "processor_y": 0.51},
                        "feasible": False,
                        "total_violation": 0.6,
                        "dominant_violation": {"constraint_id": "cold_battery_floor", "violation": 0.6},
                    },
                    {
                        "decision_vector": {"processor_x": 0.28, "processor_y": 0.55},
                        "feasible": True,
                        "total_violation": 0.0,
                        "dominant_violation": None,
                        "objective_summary": {"maximize_cold_battery_min": 259.8},
                    },
                ],
            },
            "archive_state": {
                "best_feasible": {"evaluation_index": 44, "total_violation": 0.0},
                "best_near_feasible": {"evaluation_index": 32, "total_violation": 0.2},
            },
            "domain_regime": {
                "phase": "feasible_refine",
                "dominant_constraint_family": "cold_dominant",
            },
            "recent_decisions": [
                {
                    "evaluation_index": 61,
                    "selected_operator_id": "local_refine",
                    "fallback_used": False,
                    "llm_valid": True,
                }
            ],
            "recent_operator_counts": {
                "local_refine": {
                    "recent_selection_count": 2,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 2,
                }
            },
            "operator_summary": {
                "local_refine": {
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
                }
            },
            "problem_history": [{"should_not": "appear"}],
            "case_reports": {"should_not": "appear"},
        },
    )


def _post_feasible_state_without_guardrail() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=7,
        evaluation_index=64,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "feasible_refine",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine", "radiator_expand"],
            "run_state": {
                "decision_index": 12,
                "evaluations_used": 63,
                "evaluations_remaining": 66,
                "feasible_rate": 0.17,
                "first_feasible_eval": 45,
            },
            "progress_state": {
                "phase": "post_feasible_progress",
                "first_feasible_found": True,
                "evaluations_since_first_feasible": 18,
                "recent_no_progress_count": 0,
                "last_progress_eval": 63,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 61,
                    "selected_operator_id": "local_refine",
                    "fallback_used": False,
                    "llm_valid": True,
                }
            ],
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 5,
                    "recent_selection_count": 0,
                    "proposal_count": 5,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 2,
                },
                "local_refine": {
                    "selection_count": 5,
                    "recent_selection_count": 1,
                    "proposal_count": 5,
                    "feasible_entry_count": 1,
                    "feasible_preservation_count": 2,
                },
                "radiator_expand": {
                    "selection_count": 2,
                    "recent_selection_count": 0,
                    "proposal_count": 2,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
            },
        },
    )


def _prefeasible_support_limited_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=33,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "sbx_pm_global", "battery_to_warm_zone"],
            "run_state": {
                "decision_index": 9,
                "evaluations_used": 32,
                "evaluations_remaining": 97,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
                "generation_index": 4,
            },
            "archive_state": {
                "best_feasible": None,
                "best_near_feasible": {
                    "evaluation_index": 19,
                    "total_violation": 0.12,
                    "dominant_violation": {
                        "constraint_id": "cold_battery_floor",
                        "violation": 0.06,
                    },
                },
            },
            "domain_regime": {
                "phase": "near_feasible",
                "dominant_constraint_family": "cold_dominant",
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 10,
                    "recent_selection_count": 4,
                    "recent_llm_valid_selection_count": 4,
                    "proposal_count": 10,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                    "avg_total_violation_delta": -0.12,
                },
                "sbx_pm_global": {
                    "selection_count": 5,
                    "recent_selection_count": 2,
                    "recent_llm_valid_selection_count": 2,
                    "proposal_count": 5,
                    "feasible_entry_count": 1,
                    "feasible_preservation_count": 0,
                    "avg_total_violation_delta": -0.4,
                },
                "battery_to_warm_zone": {
                    "selection_count": 1,
                    "recent_selection_count": 1,
                    "recent_llm_valid_selection_count": 1,
                    "proposal_count": 1,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                    "avg_total_violation_delta": -73.79,
                    "recent_helpful_regimes": ["near_feasible", "cold_dominant"],
                },
            },
        },
    )


def _prefeasible_custom_dominance_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=28,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine", "battery_to_warm_zone"],
            "run_state": {
                "decision_index": 10,
                "evaluations_used": 27,
                "evaluations_remaining": 102,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
                "generation_index": 3,
            },
            "recent_decisions": [
                {"evaluation_index": 23, "selected_operator_id": "native_sbx_pm", "fallback_used": False, "llm_valid": True},
                {
                    "evaluation_index": 24,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 25,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 26,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 27,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
            ],
            "recent_operator_counts": {
                "native_sbx_pm": {
                    "recent_selection_count": 1,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 1,
                },
                "battery_to_warm_zone": {
                    "recent_selection_count": 4,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 4,
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 8,
                    "recent_selection_count": 1,
                    "proposal_count": 8,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "battery_to_warm_zone": {
                    "selection_count": 8,
                    "recent_selection_count": 4,
                    "proposal_count": 8,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "local_refine": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
            },
        },
    )


def _prefeasible_window_dominance_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=36,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine", "battery_to_warm_zone"],
            "run_state": {
                "decision_index": 11,
                "evaluations_used": 35,
                "evaluations_remaining": 94,
                "feasible_rate": 0.0,
                "first_feasible_eval": None,
                "generation_index": 4,
            },
            "recent_decisions": [
                {"evaluation_index": 28, "selected_operator_id": "native_sbx_pm", "fallback_used": False, "llm_valid": True},
                {"evaluation_index": 29, "selected_operator_id": "native_sbx_pm", "fallback_used": False, "llm_valid": True},
                {"evaluation_index": 30, "selected_operator_id": "native_sbx_pm", "fallback_used": False, "llm_valid": True},
                {"evaluation_index": 31, "selected_operator_id": "native_sbx_pm", "fallback_used": False, "llm_valid": True},
                {
                    "evaluation_index": 32,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 33,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 34,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
                {
                    "evaluation_index": 35,
                    "selected_operator_id": "battery_to_warm_zone",
                    "fallback_used": False,
                    "llm_valid": True,
                },
            ],
            "recent_operator_counts": {
                "native_sbx_pm": {
                    "recent_selection_count": 4,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 4,
                },
                "battery_to_warm_zone": {
                    "recent_selection_count": 4,
                    "recent_fallback_selection_count": 0,
                    "recent_llm_valid_selection_count": 4,
                },
            },
            "operator_summary": {
                "native_sbx_pm": {
                    "selection_count": 12,
                    "recent_selection_count": 4,
                    "proposal_count": 12,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "battery_to_warm_zone": {
                    "selection_count": 8,
                    "recent_selection_count": 4,
                    "proposal_count": 8,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "local_refine": {
                    "selection_count": 1,
                    "recent_selection_count": 0,
                    "proposal_count": 1,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
            },
        },
    )


def _prefeasible_family_collapse_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=81,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "local_refine",
                "battery_to_warm_zone",
                "hot_pair_separate",
            ],
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


def _prefeasible_reset_policy_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=64,
        parent_count=2,
        vector_size=8,
        metadata={
            "search_phase": "near_feasible",
            "candidate_operator_ids": [
                "native_sbx_pm",
                "local_refine",
                "battery_to_warm_zone",
                "hot_pair_to_sink",
            ],
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
                        "hot_pair_to_sink",
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
                "local_refine": {
                    "selection_count": 4,
                    "recent_selection_count": 0,
                    "proposal_count": 4,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                },
                "hot_pair_to_sink": {
                    "selection_count": 7,
                    "recent_selection_count": 3,
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


def _controller_parameters() -> dict[str, object]:
    return {
        "provider": "openai",
        "model": "gpt-5.4",
        "capability_profile": "responses_native",
        "performance_profile": "balanced",
        "api_key_env_var": "TEST_OPENAI_API_KEY",
        "max_output_tokens": 512,
        "fallback_controller": "random_uniform",
    }


def test_llm_controller_returns_structured_decision_from_client() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="bias toward local cleanup",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    decision = controller.select_decision(
        _state(),
        ("native_sbx_pm", "local_refine"),
        np.random.default_rng(7),
    )

    assert isinstance(decision, ControllerDecision)
    assert decision.selected_operator_id == "local_refine"
    assert decision.phase == "post_feasible"
    assert decision.rationale == "bias toward local cleanup"
    assert decision.metadata["provider"] == "openai"
    assert decision.metadata["model"] == "gpt-5.4"
    assert decision.metadata["policy_phase"] == "post_feasible"
    assert decision.metadata["phase_source"] == "policy_kernel"
    assert decision.metadata["model_phase"] == "repair"
    assert client.last_kwargs is not None
    assert "candidate_operator_ids" in client.last_kwargs["user_prompt"]


def test_llm_controller_records_local_policy_phase_even_without_active_guardrail() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="",
            rationale="preserve feasible frontier stability",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    decision = controller.select_decision(
        _post_feasible_state_without_guardrail(),
        ("native_sbx_pm", "local_refine", "radiator_expand"),
        np.random.default_rng(7),
    )

    assert decision.phase == "post_feasible_progress"
    assert decision.metadata["policy_phase"] == "post_feasible_progress"
    assert not decision.metadata.get("guardrail_applied", False)


def test_llm_controller_records_elapsed_seconds_in_response_trace_and_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="bias toward local cleanup",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )
    perf_counter_values = iter([10.0, 12.5])
    monkeypatch.setattr(llm_controller_module.time, "perf_counter", lambda: next(perf_counter_values))

    decision = controller.select_decision(
        _state(),
        ("native_sbx_pm", "local_refine"),
        np.random.default_rng(7),
    )

    assert decision.metadata["elapsed_seconds"] == pytest.approx(2.5)
    assert controller.response_trace[0]["elapsed_seconds"] == pytest.approx(2.5)
    assert controller.metrics["elapsed_seconds_total"] == pytest.approx(2.5)
    assert controller.metrics["elapsed_seconds_avg"] == pytest.approx(2.5)


def test_llm_controller_falls_back_to_random_uniform_on_client_error() -> None:
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=_FakeLLMClient(error=RuntimeError("provider outage")),
    )

    decision = controller.select_decision(
        _state(),
        ("native_sbx_pm", "local_refine"),
        np.random.default_rng(7),
    )

    assert decision.selected_operator_id in {"native_sbx_pm", "local_refine"}
    assert decision.metadata["fallback_used"] is True
    assert decision.metadata["fallback_controller"] == "random_uniform"
    assert "provider outage" in decision.metadata["fallback_reason"]


def test_llm_controller_discourages_recent_operator_collapse_in_system_prompt() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="break recent action collapse",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    controller.select_decision(
        _collapsed_state(),
        ("native_sbx_pm", "hot_pair_to_sink", "local_refine"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    system_prompt = str(client.last_kwargs["system_prompt"]).lower()
    assert "avoid repeatedly selecting the same operator" in system_prompt
    assert "hot_pair_to_sink" in system_prompt
    assert "local_refine" in system_prompt


def test_llm_controller_applies_traceable_recent_dominance_guardrail() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="break recent action collapse",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    decision = controller.select_decision(
        _collapsed_state(),
        ("native_sbx_pm", "hot_pair_to_sink", "local_refine"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine")
    assert decision.metadata["guardrail_applied"] is True
    assert decision.metadata["guardrail_filtered_operator_ids"] == ["hot_pair_to_sink"]
    assert decision.metadata["guardrail_reason"] == "recent_operator_dominance"
    assert controller.request_trace[0]["original_candidate_operator_ids"] == [
        "native_sbx_pm",
        "hot_pair_to_sink",
        "local_refine",
    ]
    assert controller.request_trace[0]["guardrail"]["filtered_operator_ids"] == ["hot_pair_to_sink"]


def test_llm_controller_user_prompt_uses_compact_state_fields() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="compact prompt test",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    controller.select_decision(
        _fallback_dominated_state(),
        ("native_sbx_pm", "hot_pair_to_sink", "local_refine"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    payload = json.loads(str(client.last_kwargs["user_prompt"]))
    metadata = payload["metadata"]
    assert metadata["search_phase"] == "near_feasible"
    assert "recent_operator_counts" in metadata
    assert "operator_summary" in metadata
    assert "recent_decisions" in metadata
    assert "native_parameters" not in metadata
    assert "parent_indices" not in metadata


def test_llm_controller_user_prompt_includes_domain_grounded_blocks_without_raw_history() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="domain-grounded prompt test",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    controller.select_decision(
        _domain_grounded_state(),
        ("native_sbx_pm", "hot_pair_to_sink", "local_refine"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    payload = json.loads(str(client.last_kwargs["user_prompt"]))
    metadata = payload["metadata"]
    assert metadata["run_state"]["decision_index"] == 12
    assert metadata["parent_state"]["parents"][0]["decision_vector"]["processor_x"] == pytest.approx(0.22)
    assert metadata["archive_state"]["best_feasible"]["evaluation_index"] == 44
    assert metadata["domain_regime"]["phase"] == "feasible_refine"
    assert "problem_history" not in metadata
    assert "case_reports" not in metadata


def test_llm_controller_prefeasible_prompt_warns_against_low_support_violation_outliers() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="sbx_pm_global",
            phase="repair",
            rationale="prefer stable pre-feasible evidence",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "sbx_pm_global"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    controller.select_decision(
        _prefeasible_support_limited_state(),
        ("native_sbx_pm", "sbx_pm_global", "battery_to_warm_zone"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    system_prompt = str(client.last_kwargs["system_prompt"]).lower()
    payload = json.loads(str(client.last_kwargs["user_prompt"]))
    operator_summary = payload["metadata"]["operator_summary"]
    assert "before first feasible" in system_prompt
    assert "do not over-weight one-off large" in system_prompt
    assert "avg_total_violation_delta" not in operator_summary["battery_to_warm_zone"]
    assert operator_summary["battery_to_warm_zone"]["evidence_level"] == "limited"
    assert operator_summary["sbx_pm_global"]["feasible_entry_count"] == 1
    assert "avg_total_violation_delta" in operator_summary["sbx_pm_global"]


def test_llm_controller_guardrail_ignores_fallback_only_recent_dominance() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="hot_pair_to_sink",
            phase="repair",
            rationale="fallback-only dominance should not filter",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "hot_pair_to_sink"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    decision = controller.select_decision(
        _fallback_dominated_state(),
        ("native_sbx_pm", "hot_pair_to_sink", "local_refine"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "hot_pair_to_sink", "local_refine")
    assert decision.metadata.get("guardrail_applied") is None
    assert controller.request_trace[0]["guardrail"] is None


def test_llm_controller_prefeasible_guardrail_filters_zero_credit_custom_dominance() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="break custom dominance before first feasible",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    decision = controller.select_decision(
        _prefeasible_custom_dominance_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine")
    assert decision.metadata["guardrail_applied"] is True
    assert decision.metadata["guardrail_filtered_operator_ids"] == ["battery_to_warm_zone"]
    assert controller.request_trace[0]["guardrail"]["filtered_operator_ids"] == ["battery_to_warm_zone"]


def test_llm_controller_prefeasible_guardrail_uses_recent_decision_window_for_custom_dominance() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="break recent custom streak before first feasible",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    decision = controller.select_decision(
        _prefeasible_window_dominance_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine")
    assert decision.metadata["guardrail_applied"] is True
    assert decision.metadata["guardrail_filtered_operator_ids"] == ["battery_to_warm_zone"]


def test_llm_controller_prefeasible_policy_filters_speculative_custom_families() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="family-aware filter",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    controller.select_decision(
        _prefeasible_family_collapse_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone", "hot_pair_separate"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine")


def test_llm_controller_prompt_reports_phase_policy_not_operator_specific_patch() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="prefer stable reset path",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    controller.select_decision(
        _prefeasible_reset_policy_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone", "hot_pair_to_sink"),
        np.random.default_rng(7),
    )

    assert client.last_kwargs is not None
    system_prompt = str(client.last_kwargs["system_prompt"]).lower()
    assert "prefeasible" in system_prompt
    assert "trusted evidence" in system_prompt
    assert "battery_to_warm_zone" not in system_prompt


def test_llm_controller_trace_records_policy_reason_codes() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="trace policy reason codes",
            provider="openai",
            model="gpt-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )

    decision = controller.select_decision(
        _prefeasible_reset_policy_state(),
        ("native_sbx_pm", "local_refine", "battery_to_warm_zone", "hot_pair_to_sink"),
        np.random.default_rng(7),
    )

    assert decision.metadata["guardrail_reason_codes"] == [
        "prefeasible_speculative_family_collapse",
        "prefeasible_forced_reset",
    ]


def test_llm_controller_records_elapsed_seconds_for_fallback_trace_and_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=_FakeLLMClient(error=RuntimeError("provider outage")),
    )
    perf_counter_values = iter([20.0, 23.25])
    monkeypatch.setattr(llm_controller_module.time, "perf_counter", lambda: next(perf_counter_values))

    decision = controller.select_decision(
        _state(),
        ("native_sbx_pm", "local_refine"),
        np.random.default_rng(7),
    )

    assert decision.metadata["fallback_used"] is True
    assert decision.metadata["elapsed_seconds"] == pytest.approx(3.25)
    assert controller.response_trace[0]["elapsed_seconds"] == pytest.approx(3.25)
    assert controller.metrics["elapsed_seconds_total"] == pytest.approx(3.25)
    assert controller.metrics["elapsed_seconds_avg"] == pytest.approx(3.25)


def test_llm_controller_requires_at_least_one_candidate_operator() -> None:
    controller = LLMOperatorController(
        controller_parameters=_controller_parameters(),
        client=_FakeLLMClient(
            decision=OpenAICompatibleDecision(
                selected_operator_id="local_refine",
                phase="repair",
                rationale="bias toward local cleanup",
                provider="openai",
                model="gpt-5.4",
                capability_profile="responses_native",
                performance_profile="balanced",
                raw_payload={"selected_operator_id": "local_refine"},
            )
        ),
    )

    with pytest.raises(ValueError, match="at least one candidate operator"):
        controller.select_decision(
            _state(),
            (),
            np.random.default_rng(7),
        )
