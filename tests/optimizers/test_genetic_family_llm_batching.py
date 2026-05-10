from __future__ import annotations

import numpy as np
from pymoo.core.population import Population

from optimizers.adapters.genetic_family import GeneticFamilyUnionMating
from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.layout import VariableLayout


def _controller_parameters() -> dict[str, object]:
    return {
        "provider": "openai-compatible",
        "capability_profile": "chat_compatible_json",
        "performance_profile": "balanced",
        "model": "batch-test-model",
        "api_key_env_var": "TEST_OPENAI_API_KEY",
        "base_url": "https://llm.example/v1",
        "max_output_tokens": 128,
        "temperature": 0.7,
        "retry": {
            "max_attempts": 1,
            "timeout_seconds": 10,
        },
    }


def _variable_spec() -> dict[str, object]:
    return {
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


def test_llm_mating_ignores_batch_size_and_builds_state_serially(monkeypatch) -> None:
    class _RawMating:
        repair = None
        eliminate_duplicates = None
        n_max_iterations = 2

        class _Crossover:
            n_offsprings = 1
            n_parents = 2

        crossover = _Crossover()

    class _Problem:
        _next_evaluation_index = 10
        history: list[object] = []

    mating = GeneticFamilyUnionMating(
        operator_ids=["vector_sbx_pm", "component_jitter_1"],
        registry_profile="primitive_structured",
        legality_policy_id="bounds_only",
        controller_id="llm",
        variable_layout=VariableLayout.from_optimization_spec(_variable_spec()),
        repair_reference_case=object(),
        optimization_spec={**_variable_spec(), "algorithm": {"population_size": 2, "num_generations": 1}},
        family="genetic",
        backbone="nsga2",
        selection=object(),
        raw_mating=_RawMating(),
        native_parameters={},
        controller_parameters=_controller_parameters(),
        llm_batch_size=16,
    )
    pop = Population.new("X", np.asarray([[0.2, 0.3], [0.6, 0.5]], dtype=np.float64))
    parents = np.asarray([[0, 1], [1, 0]], dtype=np.int64)
    order: list[str] = []

    def fake_build_event_state(
        pop_arg,
        row,
        *,
        generation_index,
        event_index,
        decision_index,
        evaluation_index,
        problem,
        local_controller_trace=None,
        local_operator_trace=None,
        generation_target_offsprings=None,
    ):
        del pop_arg, row, generation_index, evaluation_index, problem
        del local_controller_trace, local_operator_trace, generation_target_offsprings
        order.append(f"build-{event_index}")
        return {
            "decision_index": decision_index,
            "evaluation_index": 10 + int(event_index),
            "generation_index": 1,
            "row": [0, 1],
            "parents": object(),
            "state": {"event_index": event_index},
        }

    def fake_dispatch_single_llm_decision(state, rng):
        del rng
        order.append(f"dispatch-{state['event_index']}")
        return ControllerDecision(selected_operator_id="component_jitter_1")

    def fake_proposal_population_for_record(
        problem,
        pop_arg,
        record,
        rng,
        *,
        algorithm,
        provisional_evaluation_start,
        **kwargs,
    ):
        del problem, pop_arg, rng, algorithm, kwargs
        order.append(f"process-{record['state']['event_index']}")
        return Population.create(), int(provisional_evaluation_start)

    monkeypatch.setattr(mating, "_build_event_state", fake_build_event_state)
    monkeypatch.setattr(mating, "_dispatch_single_llm_decision", fake_dispatch_single_llm_decision)
    monkeypatch.setattr(mating, "_proposal_population_for_record", fake_proposal_population_for_record)
    monkeypatch.setattr(mating, "_filter_raw_duplicates", lambda population, pop_arg, off: population)

    result = mating.do(
        _Problem(),
        pop,
        2,
        random_state=np.random.default_rng(3),
        algorithm=type("Algorithm", (), {"n_iter": 1, "random_state": np.random.default_rng(4)})(),
        parents=parents,
    )

    assert len(result) == 0
    assert order == [
        "build-0",
        "dispatch-0",
        "process-0",
        "build-1",
        "dispatch-1",
        "process-1",
    ]
