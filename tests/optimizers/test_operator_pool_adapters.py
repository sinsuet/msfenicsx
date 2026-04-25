from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from evaluation.io import load_spec
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.models import OptimizationSpec


PRIMITIVE_OPERATOR_IDS = (
    "vector_sbx_pm",
    "component_jitter_1",
    "component_relocate_1",
    "component_swap_2",
    "sink_shift",
    "sink_resize",
)

ASSISTED_OPERATOR_IDS = (
    "hotspot_pull_toward_sink",
    "hotspot_spread",
    "gradient_band_smooth",
    "congestion_relief",
    "sink_retarget",
    "layout_rebalance",
)


def _approved_union_operator_ids() -> list[str]:
    return list(PRIMITIVE_OPERATOR_IDS)


def _approved_assisted_operator_ids() -> list[str]:
    return [*PRIMITIVE_OPERATOR_IDS, *ASSISTED_OPERATOR_IDS]


def _spec(spec_path: str, *, seed: int = 7, population_size: int = 4, num_generations: int = 2) -> OptimizationSpec:
    payload = load_optimization_spec(spec_path).to_dict()
    payload["algorithm"]["population_size"] = population_size
    payload["algorithm"]["num_generations"] = num_generations
    payload["algorithm"]["seed"] = seed
    return OptimizationSpec.from_dict(payload)


def _base_case(spec_path: str, spec: OptimizationSpec):
    return generate_benchmark_case(spec_path, spec)


def _evaluation_spec(spec_path: str, spec: OptimizationSpec):
    return load_spec(resolve_evaluation_spec_path(spec_path, spec))


def _duplicate_evaluation_count(history: list[dict[str, object]]) -> int:
    seen: dict[tuple[float, ...], int] = {}
    duplicates = 0
    for entry in history:
        vector = tuple(round(float(value), 12) for value in entry["decision_vector"].values())
        count = seen.get(vector, 0)
        if count:
            duplicates += 1
        seen[vector] = count + 1
    return duplicates


def test_s1_typical_union_runs_and_emits_primitive_operator_traces() -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    spec_path = "scenarios/optimization/s1_typical_union.yaml"
    spec = _spec(spec_path)
    run = run_union_optimization(
        _base_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
    )

    assert run.result.aggregate_metrics["num_evaluations"] > 0
    assert run.controller_trace
    assert run.operator_trace
    assert len(run.controller_trace) == len(run.operator_trace)
    assert {row.backbone for row in run.controller_trace} == {"nsga2"}
    assert {row.controller_id for row in run.controller_trace} == {"random_uniform"}
    assert {row.selected_operator_id for row in run.controller_trace}.issubset(_approved_union_operator_ids())


def test_clean_union_uses_primitive_pool_and_skips_repair_collapsed_dedup(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    spec_path = "scenarios/optimization/s1_typical_union.yaml"
    spec = _spec(spec_path)
    run = run_union_optimization(
        _base_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
    )

    assert {row.selected_operator_id for row in run.controller_trace}.issubset(set(PRIMITIVE_OPERATOR_IDS))
    assert all(not getattr(row, "repair_collapsed_duplicate", False) for row in run.operator_attempt_trace)


def test_llm_assisted_path_keeps_attempt_level_screening_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    def _fake_build_controller(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(controller_id="llm")

    def _fake_select_controller_decision(controller, state, operator_ids, rng):
        del controller, state, rng
        return SimpleNamespace(
            selected_operator_id="sink_retarget" if "sink_retarget" in operator_ids else operator_ids[0],
            metadata={},
            phase="post_feasible_expand",
            rationale="test",
        )

    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller", _fake_build_controller)
    monkeypatch.setattr(
        "optimizers.adapters.genetic_family.configure_controller_trace_outputs",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "optimizers.adapters.genetic_family.select_controller_decision",
        _fake_select_controller_decision,
    )

    spec_path = "scenarios/optimization/s1_typical_llm.yaml"
    spec = _spec(spec_path, population_size=4, num_generations=2)
    run = run_union_optimization(
        _base_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
    )

    assert run.operator_attempt_trace
    assert all(row.metadata.get("legality_policy_id") == "projection_plus_local_restore" for row in run.operator_attempt_trace)


def test_s1_typical_union_vector_sbx_only_matches_raw_nsga2(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.raw_driver import run_raw_optimization
    from optimizers.drivers.union_driver import run_union_optimization
    from optimizers.operator_pool.random_controller import RandomUniformController
    seed = 7

    def _always_pick_native(self, state, operator_ids, rng):
        del self, state, rng
        assert "vector_sbx_pm" in operator_ids
        return "vector_sbx_pm"

    monkeypatch.setattr(RandomUniformController, "select_operator", _always_pick_native)

    raw_spec_path = "scenarios/optimization/s1_typical_raw.yaml"
    union_spec_path = "scenarios/optimization/s1_typical_union.yaml"
    raw_spec = _spec(raw_spec_path, seed=seed)
    union_spec = _spec(union_spec_path, seed=seed)

    raw_run = run_raw_optimization(
        _base_case(raw_spec_path, raw_spec),
        raw_spec,
        _evaluation_spec(raw_spec_path, raw_spec),
        spec_path=raw_spec_path,
    )
    union_run = run_union_optimization(
        _base_case(union_spec_path, union_spec),
        union_spec,
        _evaluation_spec(union_spec_path, union_spec),
        spec_path=union_spec_path,
    )

    assert union_run.result.aggregate_metrics == raw_run.result.aggregate_metrics
    assert _duplicate_evaluation_count(union_run.result.history) == _duplicate_evaluation_count(raw_run.result.history)


def test_s1_typical_union_mixed_trace_uses_one_decision_per_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.union_driver import run_union_optimization
    from optimizers.operator_pool.random_controller import RandomUniformController

    selections = iter(
        [
            "vector_sbx_pm",
            "component_jitter_1",
            "vector_sbx_pm",
            "sink_resize",
        ]
    )

    def _scripted_select(self, state, operator_ids, rng):
        del self, state, operator_ids, rng
        return next(selections)

    monkeypatch.setattr(RandomUniformController, "select_operator", _scripted_select)
    spec_path = "scenarios/optimization/s1_typical_union.yaml"
    spec = _spec(spec_path)
    run = run_union_optimization(
        _base_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
    )

    assert len(run.controller_trace) == 4
    assert len(run.operator_trace) == 4
    assert [row.selected_operator_id for row in run.controller_trace] == [
        "vector_sbx_pm",
        "component_jitter_1",
        "vector_sbx_pm",
        "sink_resize",
    ]
    assert [row.metadata["decision_index"] for row in run.controller_trace] == [0, 1, 2, 3]
    assert {row.metadata["children_per_event"] for row in run.controller_trace} == {1}
    assert [row.metadata["decision_index"] for row in run.operator_trace] == [0, 1, 2, 3]


def test_s1_typical_union_keeps_trace_indices_ordered_with_parallel_workers() -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    spec_path = "scenarios/optimization/s1_typical_union.yaml"
    spec = _spec(spec_path, seed=13, population_size=4, num_generations=1)
    run = run_union_optimization(
        _base_case(spec_path, spec),
        spec,
        _evaluation_spec(spec_path, spec),
        spec_path=spec_path,
        evaluation_workers=2,
    )

    controller_indices = [row.evaluation_index for row in run.controller_trace]
    operator_indices = [row.evaluation_index for row in run.operator_trace]

    assert controller_indices == sorted(controller_indices)
    assert operator_indices == sorted(operator_indices)
    assert controller_indices == operator_indices


def test_genetic_union_llm_uses_configured_recent_window(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.adapters.genetic_family import GeneticFamilyUnionMating

    captured: dict[str, int] = {}

    def _fake_build_controller(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(controller_id="llm")

    def _fake_build_controller_state(parents, **kwargs):
        del parents
        captured["recent_window"] = int(kwargs["recent_window"])
        return SimpleNamespace()

    def _fake_select_controller_decision(controller, state, operator_ids, rng):
        del controller, state, operator_ids, rng
        return SimpleNamespace(
            selected_operator_id="vector_sbx_pm",
            metadata={},
            phase="prefeasible_convert",
            rationale="test",
        )

    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller", _fake_build_controller)
    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller_state", _fake_build_controller_state)
    monkeypatch.setattr(
        "optimizers.adapters.genetic_family.select_controller_decision",
        _fake_select_controller_decision,
    )

    raw_mating = SimpleNamespace(
        repair=None,
        eliminate_duplicates=None,
        n_max_iterations=1,
        crossover=SimpleNamespace(n_offsprings=1, n_parents=2),
    )
    mating = GeneticFamilyUnionMating(
        operator_ids=_approved_union_operator_ids(),
        registry_profile="primitive_clean",
        legality_policy_id="minimal_canonicalization",
        controller_id="llm",
        variable_layout=None,
        repair_reference_case=None,
        optimization_spec={
            "design_variables": [{"variable_id": "c01_x"}, {"variable_id": "c01_y"}],
            "algorithm": {"population_size": 4, "num_generations": 2},
        },
        family="genetic",
        backbone="nsga2",
        selection=None,
        raw_mating=raw_mating,
        native_parameters={},
        controller_parameters={"memory": {"recent_window": 12}},
    )

    pop = [
        SimpleNamespace(X=np.asarray([0.2, 0.3], dtype=np.float64)),
        SimpleNamespace(X=np.asarray([0.4, 0.5], dtype=np.float64)),
    ]
    problem = SimpleNamespace(_next_evaluation_index=1, history=[])

    record = mating._build_event_record(
        pop,
        [0, 1],
        generation_index=0,
        event_index=0,
        rng=np.random.default_rng(0),
        problem=problem,
    )

    assert captured["recent_window"] == 12
    assert record["operator_id"] == "vector_sbx_pm"


def test_genetic_union_do_records_attempts_separately_from_accepted_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pymoo.core.duplicate import DefaultDuplicateElimination
    from pymoo.core.population import Population

    from optimizers.adapters.genetic_family import GeneticFamilyUnionMating

    def _fake_build_controller(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(controller_id="random_uniform")

    def _fake_build_controller_state(parents, **kwargs):
        del parents, kwargs
        return SimpleNamespace()

    def _fake_select_controller_decision(controller, state, operator_ids, rng):
        del controller, state, operator_ids, rng
        return SimpleNamespace(
            selected_operator_id="component_jitter_1",
            metadata={},
            phase="post_feasible_expand",
            rationale="test",
        )

    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller", _fake_build_controller)
    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller_state", _fake_build_controller_state)
    monkeypatch.setattr(
        "optimizers.adapters.genetic_family.select_controller_decision",
        _fake_select_controller_decision,
    )

    raw_mating = SimpleNamespace(
        repair=None,
        eliminate_duplicates=DefaultDuplicateElimination(),
        n_max_iterations=3,
        crossover=SimpleNamespace(n_offsprings=1, n_parents=2),
    )
    mating = GeneticFamilyUnionMating(
        operator_ids=_approved_union_operator_ids(),
        registry_profile="primitive_clean",
        legality_policy_id="minimal_canonicalization",
        controller_id="random_uniform",
        variable_layout=None,
        repair_reference_case=None,
        optimization_spec={
            "design_variables": [{"variable_id": "c01_x"}, {"variable_id": "c01_y"}],
            "algorithm": {"population_size": 4, "num_generations": 2},
        },
        family="genetic",
        backbone="nsga2",
        selection=None,
        raw_mating=raw_mating,
        native_parameters={},
        controller_parameters={},
    )

    monkeypatch.setattr(
        mating,
        "_repair_vector",
        lambda vector: np.asarray(vector, dtype=np.float64),
    )
    monkeypatch.setattr(
        mating,
        "_select_parent_rows",
        lambda problem, pop, n_select, rng, algorithm, **kwargs: np.asarray([[0, 1]] * n_select, dtype=np.int64),
    )
    proposals = iter(
        [
            np.asarray([0.15, 0.25], dtype=np.float64),
            np.asarray([0.15, 0.25], dtype=np.float64),
            np.asarray([0.35, 0.45], dtype=np.float64),
        ]
    )
    monkeypatch.setattr(
        mating,
        "_event_proposals",
        lambda problem, pop, record, rng, algorithm, **kwargs: [next(proposals)],
    )

    pop = Population.new(
        "X",
        np.asarray(
            [
                [0.2, 0.3],
                [0.4, 0.5],
            ],
            dtype=np.float64,
        ),
    )
    problem = SimpleNamespace(_next_evaluation_index=7, history=[])
    algorithm = SimpleNamespace(random_state=np.random.default_rng(0), n_iter=1)

    off = mating.do(problem, pop, 2, algorithm=algorithm, random_state=np.random.default_rng(0))

    assert len(off) == 2
    assert len(mating.controller_attempt_trace) == 3
    assert len(mating.operator_attempt_trace) == 3
    assert [row.accepted_for_evaluation for row in mating.controller_attempt_trace] == [True, False, True]
    assert mating.controller_attempt_trace[0].accepted_evaluation_indices == [7]
    assert mating.controller_attempt_trace[1].accepted_evaluation_indices == []
    assert mating.controller_attempt_trace[2].accepted_evaluation_indices == [8]
    assert mating.controller_attempt_trace[1].rejection_reason == "duplicate_within_batch"

    assert [row.evaluation_index for row in mating.controller_trace] == [7, 8]
    assert [row.evaluation_index for row in mating.operator_trace] == [7, 8]
    assert [row.metadata["decision_index"] for row in mating.controller_trace] == [0, 2]
    assert [row.metadata["attempt_index"] for row in mating.controller_trace] == [0, 2]


def test_genetic_union_do_feeds_generation_local_memory_into_later_decisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pymoo.core.duplicate import DefaultDuplicateElimination
    from pymoo.core.population import Population

    from optimizers.adapters.genetic_family import GeneticFamilyUnionMating

    seen_local_accepted_counts: list[int] = []

    def _fake_build_controller(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(controller_id="llm")

    def _fake_build_controller_state(parents, **kwargs):
        del parents
        seen_local_accepted_counts.append(len(kwargs.get("local_controller_trace") or []))
        return SimpleNamespace(generation_index=kwargs["generation_index"])

    def _fake_select_controller_decision(controller, state, operator_ids, rng):
        del controller, state, operator_ids, rng
        return SimpleNamespace(
            selected_operator_id="sink_retarget",
            metadata={},
            phase="post_feasible_expand",
            rationale="test",
        )

    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller", _fake_build_controller)
    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller_state", _fake_build_controller_state)
    monkeypatch.setattr(
        "optimizers.adapters.genetic_family.select_controller_decision",
        _fake_select_controller_decision,
    )

    raw_mating = SimpleNamespace(
        repair=None,
        eliminate_duplicates=DefaultDuplicateElimination(),
        n_max_iterations=4,
        crossover=SimpleNamespace(n_offsprings=1, n_parents=2),
    )
    mating = GeneticFamilyUnionMating(
        operator_ids=_approved_assisted_operator_ids(),
        registry_profile="primitive_plus_assisted",
        legality_policy_id="projection_plus_local_restore",
        controller_id="llm",
        variable_layout=None,
        repair_reference_case=None,
        optimization_spec={
            "design_variables": [{"variable_id": "c01_x"}, {"variable_id": "c01_y"}],
            "algorithm": {"population_size": 4, "num_generations": 2},
        },
        family="genetic",
        backbone="nsga2",
        selection=None,
        raw_mating=raw_mating,
        native_parameters={},
        controller_parameters={},
    )

    monkeypatch.setattr(
        mating,
        "_repair_vector",
        lambda vector: np.asarray(vector, dtype=np.float64),
    )
    monkeypatch.setattr(
        mating,
        "_select_parent_rows",
        lambda problem, pop, n_select, rng, algorithm, **kwargs: np.asarray([[0, 1]] * n_select, dtype=np.int64),
    )
    proposals = iter(
        [
            np.asarray([0.15, 0.25], dtype=np.float64),
            np.asarray([0.35, 0.45], dtype=np.float64),
            np.asarray([0.55, 0.65], dtype=np.float64),
        ]
    )
    monkeypatch.setattr(
        mating,
        "_event_proposals",
        lambda problem, pop, record, rng, algorithm, **kwargs: [next(proposals)],
    )

    pop = Population.new(
        "X",
        np.asarray(
            [
                [0.2, 0.3],
                [0.4, 0.5],
            ],
            dtype=np.float64,
        ),
    )
    problem = SimpleNamespace(_next_evaluation_index=7, history=[])
    algorithm = SimpleNamespace(random_state=np.random.default_rng(0), n_iter=1)

    off = mating.do(problem, pop, 3, algorithm=algorithm, random_state=np.random.default_rng(0))

    assert len(off) == 3
    assert seen_local_accepted_counts == [0, 1, 2]


def test_genetic_union_llm_reuses_repaired_reference_keys_within_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pymoo.core.duplicate import DefaultDuplicateElimination
    from pymoo.core.population import Population

    from optimizers.adapters.genetic_family import GeneticFamilyUnionMating

    def _fake_build_controller(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(controller_id="llm")

    def _fake_build_controller_state(parents, **kwargs):
        del parents, kwargs
        return SimpleNamespace()

    def _fake_select_controller_decision(controller, state, operator_ids, rng):
        del controller, state, operator_ids, rng
        return SimpleNamespace(
            selected_operator_id="sink_retarget",
            metadata={},
            phase="post_feasible_expand",
            rationale="test",
        )

    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller", _fake_build_controller)
    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller_state", _fake_build_controller_state)
    monkeypatch.setattr(
        "optimizers.adapters.genetic_family.select_controller_decision",
        _fake_select_controller_decision,
    )

    raw_mating = SimpleNamespace(
        repair=None,
        eliminate_duplicates=DefaultDuplicateElimination(),
        n_max_iterations=4,
        crossover=SimpleNamespace(n_offsprings=1, n_parents=2),
    )
    mating = GeneticFamilyUnionMating(
        operator_ids=_approved_assisted_operator_ids(),
        registry_profile="primitive_plus_assisted",
        legality_policy_id="projection_plus_local_restore",
        controller_id="llm",
        variable_layout=None,
        repair_reference_case=None,
        optimization_spec={
            "design_variables": [{"variable_id": "c01_x"}, {"variable_id": "c01_y"}],
            "algorithm": {"population_size": 4, "num_generations": 2},
        },
        family="genetic",
        backbone="nsga2",
        selection=None,
        raw_mating=raw_mating,
        native_parameters={},
        controller_parameters={},
    )

    repair_call_count = {"value": 0}

    def _counting_repair(vector: np.ndarray) -> np.ndarray:
        repair_call_count["value"] += 1
        return np.asarray(vector, dtype=np.float64)

    monkeypatch.setattr(mating, "_repair_vector", _counting_repair)
    monkeypatch.setattr(
        mating,
        "_select_parent_rows",
        lambda problem, pop, n_select, rng, algorithm, **kwargs: np.asarray([[0, 1]] * n_select, dtype=np.int64),
    )
    proposals = iter(
        [
            np.asarray([0.15, 0.25], dtype=np.float64),
            np.asarray([0.35, 0.45], dtype=np.float64),
            np.asarray([0.55, 0.65], dtype=np.float64),
        ]
    )
    monkeypatch.setattr(
        mating,
        "_event_proposals",
        lambda problem, pop, record, rng, algorithm, **kwargs: [next(proposals)],
    )

    pop = Population.new(
        "X",
        np.asarray(
            [
                [0.2, 0.3],
                [0.4, 0.5],
            ],
            dtype=np.float64,
        ),
    )
    problem = SimpleNamespace(_next_evaluation_index=7, history=[])
    algorithm = SimpleNamespace(random_state=np.random.default_rng(0), n_iter=1)

    off = mating.do(problem, pop, 3, algorithm=algorithm, random_state=np.random.default_rng(0))

    assert len(off) == 3
    assert repair_call_count["value"] == 8
