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
