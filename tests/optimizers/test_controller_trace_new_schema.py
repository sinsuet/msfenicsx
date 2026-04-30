"""LLM controller writes § 4.4 controller_trace.jsonl records."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from llm.openai_compatible.client import OpenAICompatibleDecision
from optimizers.operator_pool.controllers import configure_controller_trace_outputs
from optimizers.operator_pool.llm_controller import LLMOperatorController
from optimizers.operator_pool.state import ControllerState
from optimizers.traces.prompt_store import PromptStore


class _FakeLLMClient:
    def request_operator_decision(self, **kwargs) -> OpenAICompatibleDecision:
        del kwargs
        return OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="tighten the current layout around the strongest evidence.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={
                "selected_operator_id": "local_refine",
                "phase": "repair",
                "rationale": "tighten the current layout around the strongest evidence.",
            },
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
            "decision_index": 4,
            "search_phase": "near_feasible",
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
        },
    )


def test_controller_trace_records_have_new_schema(tmp_path: Path) -> None:
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=_FakeLLMClient(),
    )
    run_root = tmp_path / "run"
    controller.configure_trace_outputs(
        controller_trace_path=run_root / "traces" / "controller_trace.jsonl",
        llm_request_trace_path=run_root / "traces" / "llm_request_trace.jsonl",
        llm_response_trace_path=run_root / "traces" / "llm_response_trace.jsonl",
        prompt_store=PromptStore(run_root / "prompts"),
    )

    decision = controller.select_decision(
        _state(),
        ("native_sbx_pm", "local_refine"),
        np.random.default_rng(7),
    )

    assert decision.selected_operator_id == "local_refine"

    trace_path = run_root / "traces" / "controller_trace.jsonl"
    request_trace_path = run_root / "traces" / "llm_request_trace.jsonl"
    response_trace_path = run_root / "traces" / "llm_response_trace.jsonl"
    assert trace_path.exists()
    assert request_trace_path.exists()
    assert response_trace_path.exists()

    rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    row = rows[0]
    for key in (
        "decision_id",
        "phase",
        "operator_selected",
        "operator_pool_snapshot",
        "input_state_digest",
        "prompt_ref",
        "rationale",
        "fallback_used",
        "latency_ms",
    ):
        assert key in row
    assert row["decision_id"] == "g003-e0012-d04"
    assert row["prompt_ref"].startswith("prompts/")
    assert row["prompt_ref"].endswith(".md")

    request_rows = [json.loads(line) for line in request_trace_path.read_text(encoding="utf-8").splitlines()]
    response_rows = [json.loads(line) for line in response_trace_path.read_text(encoding="utf-8").splitlines()]
    assert request_rows[0]["prompt_ref"] == row["prompt_ref"]
    assert response_rows[0]["response_ref"].startswith("prompts/")

    prompt_path = run_root / row["prompt_ref"]
    response_path = run_root / response_rows[0]["response_ref"]
    assert prompt_path.exists()
    assert response_path.exists()
    prompt_body = prompt_path.read_text(encoding="utf-8")
    response_body = response_path.read_text(encoding="utf-8")
    assert "# System" in prompt_body
    assert "# User" in prompt_body
    assert '"selected_operator_id": "local_refine"' in response_body


def test_mainline_llm_controller_requires_trace_output_root() -> None:
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "model": "GPT-5.4",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
        },
        client=_FakeLLMClient(),
    )

    with pytest.raises(ValueError, match="trace_output_root"):
        configure_controller_trace_outputs(controller, output_root=None)


def test_llm_semantic_prior_trace_surfaces_sampler_metadata(tmp_path: Path) -> None:
    from llm.openai_compatible.client import (
        OpenAICompatiblePriorAdvice,
        OperatorPrior,
    )

    class _PriorClient:
        def request_operator_prior_advice(self, **kwargs):
            return OpenAICompatiblePriorAdvice(
                operator_priors=(
                    OperatorPrior("component_jitter_1", prior=1.0, risk=0.0, confidence=0.9),
                ),
                semantic_task_priors=(),
                phase="post_feasible_preserve",
                rationale="bounded local polish",
                provider="openai-compatible",
                model="fake-model",
                capability_profile="chat_compatible_json",
                performance_profile="balanced",
                raw_payload={
                    "operator_priors": [
                        {"operator_id": "component_jitter_1", "prior": 1.0, "risk": 0.0, "confidence": 0.9}
                    ],
                    "phase": "post_feasible_preserve",
                    "rationale": "bounded local polish",
                },
            )

    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model_env_var": "LLM_MODEL",
            "api_key_env_var": "LLM_API_KEY",
            "base_url_env_var": "LLM_BASE_URL",
            "max_output_tokens": 512,
            "selection_strategy": "semantic_prior_sampler",
        },
        client=_PriorClient(),
    )
    controller.configure_trace_outputs(
        controller_trace_path=tmp_path / "controller_trace.jsonl",
        llm_request_trace_path=tmp_path / "llm_request_trace.jsonl",
        llm_response_trace_path=tmp_path / "llm_response_trace.jsonl",
        prompt_store=PromptStore(tmp_path / "prompts"),
    )
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=42,
        parent_count=2,
        vector_size=32,
        metadata={
            "decision_index": 3,
            "search_phase": "post_feasible_preserve",
            "progress_state": {"phase": "post_feasible_preserve", "post_feasible_mode": "preserve"},
            "prompt_panels": {"run_panel": {}, "operator_panel": {"rows": []}},
            "recent_decisions": [],
        },
    )

    controller.select_decision(state, ("component_jitter_1", "sink_shift"), np.random.default_rng(1))

    response_rows = [
        json.loads(line) for line in (tmp_path / "llm_response_trace.jsonl").read_text().splitlines()
    ]
    assert response_rows[0]["selection_strategy"] == "semantic_prior_sampler"
    assert response_rows[0]["llm_operator_priors"][0]["operator_id"] == "component_jitter_1"
    assert response_rows[0]["sampler_probabilities"]["component_jitter_1"] > 0.0
    assert response_rows[0]["selected_probability"] > 0.0


def test_llm_semantic_ranked_pick_trace_surfaces_ranker_metadata(tmp_path: Path) -> None:
    from llm.openai_compatible.client import OpenAICompatibleRankAdvice, RankedOperatorCandidate

    class _RankClient:
        def request_operator_rank_advice(self, **kwargs):
            return OpenAICompatibleRankAdvice(
                ranked_operators=(
                    RankedOperatorCandidate(
                        operator_id="component_jitter_1",
                        semantic_task="local_polish",
                        score=0.82,
                        risk=0.10,
                        confidence=0.70,
                        rationale="bounded local polish",
                    ),
                    RankedOperatorCandidate(
                        operator_id="sink_shift",
                        semantic_task="sink_alignment",
                        score=0.70,
                        risk=0.30,
                        confidence=0.60,
                        rationale="alignment backup",
                    ),
                ),
                phase="post_feasible_preserve",
                rationale="rank local polish first",
                provider="openai-compatible",
                model="fake-model",
                capability_profile="chat_compatible_json",
                performance_profile="balanced",
                raw_payload={"ranked_operators": [{"operator_id": "component_jitter_1"}]},
            )

    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model_env_var": "LLM_MODEL",
            "api_key_env_var": "LLM_API_KEY",
            "base_url_env_var": "LLM_BASE_URL",
            "max_output_tokens": 512,
            "selection_strategy": "semantic_ranked_pick",
        },
        client=_RankClient(),
    )
    controller.configure_trace_outputs(
        controller_trace_path=tmp_path / "controller_trace.jsonl",
        llm_request_trace_path=tmp_path / "llm_request_trace.jsonl",
        llm_response_trace_path=tmp_path / "llm_response_trace.jsonl",
        prompt_store=PromptStore(tmp_path / "prompts"),
    )
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=42,
        parent_count=2,
        vector_size=32,
        metadata={
            "decision_index": 3,
            "search_phase": "post_feasible_preserve",
            "progress_state": {"phase": "post_feasible_preserve", "post_feasible_mode": "preserve"},
            "prompt_panels": {"run_panel": {}, "operator_panel": {"rows": []}},
            "recent_decisions": [],
        },
    )

    controller.select_decision(state, ("component_jitter_1", "sink_shift"), np.random.default_rng(1))

    response_rows = [
        json.loads(line) for line in (tmp_path / "llm_response_trace.jsonl").read_text().splitlines()
    ]
    assert response_rows[0]["selection_strategy"] == "semantic_ranked_pick"
    assert response_rows[0]["llm_ranked_operators"][0]["operator_id"] == "component_jitter_1"
    assert response_rows[0]["selected_rank"] == 1
    assert response_rows[0]["ranker_config"]["rolling_window"] == 16
    assert response_rows[0]["ranker_override_reason"] == ""
    assert "sampler_probabilities" not in response_rows[0]
