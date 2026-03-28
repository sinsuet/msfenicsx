from __future__ import annotations

from pathlib import Path

import pytest

from core.generator.paired_pipeline import generate_operating_case_pair
from evaluation.io import load_multicase_spec
from optimizers.models import OptimizationSpec


APPROVED_SHARED_OPERATOR_IDS = [
    "sbx_pm_global",
    "local_refine",
    "hot_pair_to_sink",
    "hot_pair_separate",
    "battery_to_warm_zone",
    "radiator_align_hot_pair",
    "radiator_expand",
    "radiator_contract",
]


def _native_operator_id(backbone: str) -> str:
    if backbone in {"nsga2", "nsga3", "ctaea", "rvea"}:
        return "native_sbx_pm"
    if backbone == "moead":
        return "native_moead"
    if backbone == "cmopso":
        return "native_cmopso"
    raise KeyError(backbone)


def _approved_union_operator_ids(backbone: str) -> list[str]:
    return [_native_operator_id(backbone), *APPROVED_SHARED_OPERATOR_IDS]


def _union_spec(backbone: str) -> OptimizationSpec:
    from optimizers.io import load_optimization_spec

    raw_spec = load_optimization_spec(f"scenarios/optimization/panel_four_component_hot_cold_{backbone}_raw_b0.yaml")
    payload = raw_spec.to_dict()
    payload["spec_meta"] = {
        "spec_id": f"panel-four-component-hot-cold-{backbone}-union-uniform-test",
        "description": f"{backbone} union-uniform regression test fixture.",
    }
    payload["algorithm"]["mode"] = "union"
    payload["algorithm"]["population_size"] = 6
    payload["algorithm"]["num_generations"] = 2
    payload["algorithm"].pop("profile_path", None)
    payload["operator_control"] = {
        "controller": "random_uniform",
        "operator_pool": _approved_union_operator_ids(backbone),
    }
    return OptimizationSpec.from_dict(payload)


def _small_union_spec(backbone: str, *, seed: int = 7) -> OptimizationSpec:
    spec = _union_spec(backbone)
    payload = spec.to_dict()
    payload["algorithm"]["population_size"] = 4
    payload["algorithm"]["num_generations"] = 2
    payload["algorithm"]["seed"] = seed
    return OptimizationSpec.from_dict(payload)


def _spec_with_seed(spec_path: str, seed: int) -> OptimizationSpec:
    from optimizers.io import load_optimization_spec

    payload = load_optimization_spec(spec_path).to_dict()
    payload["algorithm"]["seed"] = seed
    return OptimizationSpec.from_dict(payload)


def _base_cases(spec: OptimizationSpec):
    return generate_operating_case_pair(
        spec.benchmark_source["template_path"],
        seed=int(spec.benchmark_source["seed"]),
    )


def _evaluation_spec(spec: OptimizationSpec):
    return load_multicase_spec(spec.evaluation_protocol["evaluation_spec_path"])


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


@pytest.mark.parametrize("backbone", ["nsga2", "nsga3", "ctaea", "rvea", "moead", "cmopso"])
def test_union_uniform_runs_across_all_first_batch_backbones(backbone: str) -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    spec = _union_spec(backbone)
    run = run_union_optimization(
        _base_cases(spec),
        spec,
        _evaluation_spec(spec),
    )

    assert run.result.aggregate_metrics["num_evaluations"] > 0
    assert run.controller_trace
    assert run.operator_trace
    assert len(run.controller_trace) == len(run.operator_trace)
    assert {row.backbone for row in run.controller_trace} == {backbone}
    assert {row.controller_id for row in run.controller_trace} == {"random_uniform"}
    assert {row.selected_operator_id for row in run.controller_trace}.issubset(_approved_union_operator_ids(backbone))


@pytest.mark.parametrize("backbone", ["nsga2", "nsga3", "ctaea", "rvea", "moead", "cmopso"])
def test_union_driver_keeps_operator_telemetry_out_of_optimization_result_contract(backbone: str) -> None:
    from optimizers.drivers.union_driver import run_union_optimization

    spec = _union_spec(backbone)
    run = run_union_optimization(
        _base_cases(spec),
        spec,
        _evaluation_spec(spec),
    )
    result_payload = run.result.to_dict()

    assert "controller_trace" not in result_payload
    assert "operator_trace" not in result_payload


@pytest.mark.parametrize("backbone", ["nsga2", "nsga3", "ctaea", "rvea", "moead", "cmopso"])
def test_union_native_action_path_runs_without_custom_operators(backbone: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.union_driver import run_union_optimization
    from optimizers.operator_pool.random_controller import RandomUniformController

    native_operator_id = _native_operator_id(backbone)

    def _always_pick_native(self, state, operator_ids, rng):
        del self, state, rng
        assert native_operator_id in operator_ids
        return native_operator_id

    monkeypatch.setattr(RandomUniformController, "select_operator", _always_pick_native)
    spec = _union_spec(backbone)
    run = run_union_optimization(
        _base_cases(spec),
        spec,
        _evaluation_spec(spec),
    )

    assert run.result.aggregate_metrics["num_evaluations"] > 0
    assert run.controller_trace
    assert {row.selected_operator_id for row in run.controller_trace} == {native_operator_id}


@pytest.mark.parametrize("seed", [7, 27])
def test_nsga2_union_native_only_matches_raw_nsga2(seed: int, monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.raw_driver import run_raw_optimization
    from optimizers.drivers.union_driver import run_union_optimization
    from optimizers.operator_pool.random_controller import RandomUniformController

    raw_spec_path = "scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml"
    union_spec_path = "scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml"
    raw_spec = _spec_with_seed(raw_spec_path, seed)
    union_spec = _spec_with_seed(union_spec_path, seed)

    def _always_pick_native(self, state, operator_ids, rng):
        del self, state, rng
        assert "native_sbx_pm" in operator_ids
        return "native_sbx_pm"

    monkeypatch.setattr(RandomUniformController, "select_operator", _always_pick_native)

    raw_run = run_raw_optimization(
        _base_cases(raw_spec),
        raw_spec,
        _evaluation_spec(raw_spec),
        spec_path=raw_spec_path,
    )
    union_run = run_union_optimization(
        _base_cases(union_spec),
        union_spec,
        _evaluation_spec(union_spec),
        spec_path=union_spec_path,
    )

    assert union_run.result.aggregate_metrics == raw_run.result.aggregate_metrics
    assert _duplicate_evaluation_count(union_run.result.history) == _duplicate_evaluation_count(raw_run.result.history)


@pytest.mark.parametrize("backbone", ["nsga2", "nsga3", "ctaea", "rvea", "moead", "cmopso"])
def test_active_union_specs_produce_feasible_candidates_on_seed7(backbone: str) -> None:
    from optimizers.drivers.union_driver import run_union_optimization_from_spec

    run = run_union_optimization_from_spec(
        f"scenarios/optimization/panel_four_component_hot_cold_{backbone}_union_uniform_p1.yaml"
    )

    assert run.result.aggregate_metrics["feasible_rate"] > 0.0
    assert run.result.aggregate_metrics["pareto_size"] > 0


def test_nsga2_union_mixed_trace_uses_one_decision_per_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    from optimizers.drivers.union_driver import run_union_optimization
    from optimizers.operator_pool.random_controller import RandomUniformController

    selections = iter(
        [
            "native_sbx_pm",
            "local_refine",
            "native_sbx_pm",
            "radiator_expand",
        ]
    )

    def _scripted_select(self, state, operator_ids, rng):
        del self, state, operator_ids, rng
        return next(selections)

    monkeypatch.setattr(RandomUniformController, "select_operator", _scripted_select)
    spec = _small_union_spec("nsga2")
    run = run_union_optimization(
        _base_cases(spec),
        spec,
        _evaluation_spec(spec),
    )

    assert len(run.controller_trace) == 4
    assert len(run.operator_trace) == 4
    assert [row.selected_operator_id for row in run.controller_trace] == [
        "native_sbx_pm",
        "local_refine",
        "native_sbx_pm",
        "radiator_expand",
    ]
    assert [row.metadata["decision_index"] for row in run.controller_trace] == [0, 1, 2, 3]
    assert {row.metadata["children_per_event"] for row in run.controller_trace} == {1}
    assert [row.metadata["decision_index"] for row in run.operator_trace] == [0, 1, 2, 3]


def test_nsga2_union_native_only_trace_marks_shared_decision_index_for_siblings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from optimizers.drivers.union_driver import run_union_optimization
    from optimizers.operator_pool.random_controller import RandomUniformController

    def _always_pick_native(self, state, operator_ids, rng):
        del self, state, rng
        assert "native_sbx_pm" in operator_ids
        return "native_sbx_pm"

    monkeypatch.setattr(RandomUniformController, "select_operator", _always_pick_native)
    spec = _small_union_spec("nsga2")
    run = run_union_optimization(
        _base_cases(spec),
        spec,
        _evaluation_spec(spec),
    )

    assert len(run.controller_trace) == 4
    assert [row.metadata["decision_index"] for row in run.controller_trace] == [0, 0, 1, 1]
    assert [row.metadata["children_per_event"] for row in run.controller_trace] == [2, 2, 2, 2]
    assert [row.metadata["sibling_index"] for row in run.controller_trace] == [0, 1, 0, 1]
    assert [row.metadata["decision_index"] for row in run.operator_trace] == [0, 0, 1, 1]
