from __future__ import annotations

import pytest

from evaluation.io import load_spec
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.models import OptimizationSpec


APPROVED_SHARED_OPERATOR_IDS = [
    "global_explore",
    "local_refine",
    "move_hottest_cluster_toward_sink",
    "spread_hottest_cluster",
    "smooth_high_gradient_band",
    "reduce_local_congestion",
    "repair_sink_budget",
    "slide_sink",
    "rebalance_layout",
]


def _approved_union_operator_ids() -> list[str]:
    return ["native_sbx_pm", *APPROVED_SHARED_OPERATOR_IDS]


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


def test_s1_typical_union_runs_and_emits_semantic_operator_traces() -> None:
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


def test_s1_typical_union_native_only_matches_raw_nsga2(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.raw_driver import run_raw_optimization
    from optimizers.drivers.union_driver import run_union_optimization
    from optimizers.operator_pool.random_controller import RandomUniformController
    seed = 7

    def _always_pick_native(self, state, operator_ids, rng):
        del self, state, rng
        assert "native_sbx_pm" in operator_ids
        return "native_sbx_pm"

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
            "native_sbx_pm",
            "local_refine",
            "native_sbx_pm",
            "repair_sink_budget",
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
        "native_sbx_pm",
        "local_refine",
        "native_sbx_pm",
        "repair_sink_budget",
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
