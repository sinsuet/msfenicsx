from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from pymoo.core.population import Population

from llm.openai_compatible.client import OpenAICompatibleDecision
from optimizers.adapters.genetic_family import GeneticFamilyUnionMating
from optimizers.operator_pool.controllers import build_controller, list_registered_controller_ids
from optimizers.operator_pool.llm_direct_controller import LLMDirectOperatorController
from optimizers.operator_pool.layout import VariableLayout
from optimizers.operator_pool.state import ControllerState
from optimizers.traces.prompt_store import PromptStore


class _FakeDirectClient:
    def __init__(self, decision: OpenAICompatibleDecision) -> None:
        self.decision = decision
        self.last_kwargs: dict[str, object] | None = None

    def request_operator_decision(self, **kwargs) -> OpenAICompatibleDecision:
        self.last_kwargs = dict(kwargs)
        attempt_trace = kwargs.get("attempt_trace")
        if isinstance(attempt_trace, list):
            attempt_trace.append(
                {
                    "attempt_index": 1,
                    "valid": True,
                    "selected_operator_id": self.decision.selected_operator_id,
                }
            )
        return self.decision


def _controller_parameters() -> dict[str, object]:
    return {
        "provider": "openai-compatible",
        "capability_profile": "chat_compatible_json",
        "performance_profile": "balanced",
        "model": "direct-test-model",
        "api_key_env_var": "TEST_OPENAI_API_KEY",
        "base_url": "https://llm.example/v1",
        "max_output_tokens": 128,
        "temperature": 0.7,
        "retry": {
            "max_attempts": 1,
            "timeout_seconds": 10,
        },
    }


def _mechanism_heavy_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=41,
        parent_count=2,
        vector_size=32,
        metadata={
            "decision_index": 9,
            "policy_phase": "post_feasible_expand",
            "guardrail": {"suppressed_operator_ids": ["sink_shift"]},
            "prompt_panels": {
                "semantic_task_panel": {"active_semantic_tasks": ["sink_budget_shape"]},
                "operator_panel": {"sink_shift": {"portfolio_priority": "repay_task_debt"}},
            },
            "run_state": {
                "feasible_rate": 0.55,
                "first_feasible_eval": 13,
                "peak_temperature": 331.8,
                "temperature_gradient_rms": 20.4,
                "sink_span": 0.32,
                "sink_budget_utilization": 0.91,
            },
            "progress_state": {
                "recent_no_progress_count": 5,
                "recent_best_feasible_improvement": -0.08,
                "recent_best_near_feasible_improvement": -0.02,
            },
            "recent_decisions": [
                {"selected_operator_id": "component_jitter_1", "fallback_used": False},
                {"selected_operator_id": "component_jitter_1", "fallback_used": False},
            ],
        },
    )


def test_llm_direct_controller_is_registered_as_a_separate_controller() -> None:
    assert "llm_direct" in list_registered_controller_ids()
    controller = build_controller("llm_direct", _controller_parameters())

    assert controller.controller_id == "llm_direct"
    assert isinstance(controller, LLMDirectOperatorController)


def test_llm_direct_controller_uses_plain_top1_prompt_without_semantic_mechanisms(tmp_path: Path) -> None:
    client = _FakeDirectClient(
        OpenAICompatibleDecision(
            selected_operator_id="sink_shift",
            phase="direct_choice",
            rationale="The sink window should be moved before another component perturbation.",
            provider="openai-compatible",
            model="direct-test-model",
            capability_profile="chat_compatible_json",
            performance_profile="balanced",
            raw_payload={
                "selected_operator_id": "sink_shift",
                "phase": "direct_choice",
                "rationale": "The sink window should be moved before another component perturbation.",
            },
        )
    )
    controller = LLMDirectOperatorController(
        controller_parameters=_controller_parameters(),
        client=client,
    )
    controller.configure_trace_outputs(
        controller_trace_path=tmp_path / "controller_trace.jsonl",
        llm_request_trace_path=tmp_path / "llm_request_trace.jsonl",
        llm_response_trace_path=tmp_path / "llm_response_trace.jsonl",
        prompt_store=PromptStore(tmp_path / "prompts"),
    )

    decision = controller.select_decision(
        _mechanism_heavy_state(),
        ("vector_sbx_pm", "component_jitter_1", "sink_shift"),
        np.random.default_rng(7),
    )

    assert decision.selected_operator_id == "sink_shift"
    assert decision.metadata["selection_strategy"] == "llm_direct_top1"
    assert decision.metadata["controller_id"] == "llm_direct"
    assert "policy_phase" not in decision.metadata
    assert "guardrail" not in decision.metadata
    assert "llm_ranked_operators" not in decision.metadata
    assert "semantic_ranked_pick" not in decision.metadata

    assert client.last_kwargs is not None
    assert client.last_kwargs["candidate_operator_ids"] == (
        "vector_sbx_pm",
        "component_jitter_1",
        "sink_shift",
    )
    prompt_surface = (
        str(client.last_kwargs["system_prompt"])
        + "\n"
        + str(client.last_kwargs["user_prompt"])
    ).lower()
    assert "semantic_ranked_pick" not in prompt_surface
    assert "policy kernel" not in prompt_surface
    assert "guardrail" not in prompt_surface
    assert "semantic task" not in prompt_surface
    assert "prompt_panels" not in prompt_surface
    assert "policy_phase" not in prompt_surface

    assert controller.request_trace[0]["selection_strategy"] == "llm_direct_top1"
    assert controller.request_trace[0]["candidate_operator_ids"] == [
        "vector_sbx_pm",
        "component_jitter_1",
        "sink_shift",
    ]
    response_row = controller.response_trace[0]
    assert response_row["selection_strategy"] == "llm_direct_top1"
    assert response_row["selected_operator_id"] == "sink_shift"
    assert "policy_phase" not in response_row
    assert "guardrail" not in response_row
    assert "llm_ranked_operators" not in response_row

    controller_rows = [
        json.loads(line)
        for line in (tmp_path / "controller_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert controller_rows[0]["operator_selected"] == "sink_shift"
    request_rows = [
        json.loads(line)
        for line in (tmp_path / "llm_request_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert request_rows[0]["selection_strategy"] == "llm_direct_top1"


def test_llm_direct_mating_uses_serial_union_path_without_llm_batch_branch(monkeypatch) -> None:
    class _RawMating:
        repair = None
        eliminate_duplicates = None
        n_max_iterations = 2

        class _Crossover:
            n_offsprings = 1
            n_parents = 2

        crossover = _Crossover()

    mating = GeneticFamilyUnionMating(
        operator_ids=["vector_sbx_pm", "component_jitter_1"],
        registry_profile="primitive_structured",
        legality_policy_id="projection_plus_local_restore",
        controller_id="llm_direct",
        variable_layout=VariableLayout.from_optimization_spec(
            {
                "design_variables": [
                    {
                        "variable_id": "c01_x",
                        "path": "components[0].pose.x",
                        "lower_bound": 0.06,
                        "upper_bound": 0.94,
                    },
                    {
                        "variable_id": "c01_y",
                        "path": "components[0].pose.y",
                        "lower_bound": 0.05,
                        "upper_bound": 0.72,
                    },
                ]
            }
        ),
        repair_reference_case=object(),
        optimization_spec={
            "design_variables": [
                {
                    "variable_id": "c01_x",
                    "path": "components[0].pose.x",
                    "lower_bound": 0.06,
                    "upper_bound": 0.94,
                },
                {
                    "variable_id": "c01_y",
                    "path": "components[0].pose.y",
                    "lower_bound": 0.05,
                    "upper_bound": 0.72,
                },
            ],
            "algorithm": {"population_size": 2, "num_generations": 1},
        },
        family="genetic",
        backbone="nsga2",
        selection=object(),
        raw_mating=_RawMating(),
        native_parameters={},
        controller_parameters=_controller_parameters(),
        llm_batch_size=16,
    )
    pop = Population.new("X", np.asarray([[0.2, 0.3], [0.6, 0.5]], dtype=np.float64))
    called = {"legacy": 0, "dispatch": 0}

    def fake_legacy(*args, **kwargs):
        called["legacy"] += 1
        return Population.create()

    def fail_dispatch(*args, **kwargs):
        called["dispatch"] += 1
        raise AssertionError("llm_direct must not use the LLM batch dispatch path")

    monkeypatch.setattr(mating, "_legacy_batched_do", fake_legacy)
    monkeypatch.setattr(mating, "_dispatch_single_llm_decision", fail_dispatch)

    result = mating.do(
        object(),
        pop,
        1,
        random_state=np.random.default_rng(3),
        algorithm=type("Algorithm", (), {"n_iter": 1, "random_state": np.random.default_rng(4)})(),
    )

    assert len(result) == 0
    assert called == {"legacy": 1, "dispatch": 0}
