from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from optimizers.codec import extract_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec


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

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: str) -> dict:
    with (REPO_ROOT / path).open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _substrate_fields(spec: dict) -> dict:
    operator_control = spec["operator_control"]
    evaluation_protocol = spec["evaluation_protocol"]
    algorithm = spec["algorithm"]
    return {
        "design_variables": spec["design_variables"],
        "registry_profile": operator_control["registry_profile"],
        "operator_pool": operator_control["operator_pool"],
        "legality_policy_id": evaluation_protocol["legality_policy_id"],
        "evaluation_spec_path": evaluation_protocol["evaluation_spec_path"],
        "family": algorithm["family"],
        "backbone": algorithm["backbone"],
        "population_size": algorithm["population_size"],
        "num_generations": algorithm["num_generations"],
        "seed": algorithm["seed"],
    }
def test_s1_typical_union_and_llm_share_search_substrate() -> None:
    union_spec = _load_yaml("scenarios/optimization/s1_typical_union.yaml")
    llm_spec = _load_yaml("scenarios/optimization/s1_typical_llm.yaml")

    assert union_spec["operator_control"]["controller"] == "random_uniform"
    assert llm_spec["operator_control"]["controller"] == "llm"
    assert _substrate_fields(llm_spec) == _substrate_fields(union_spec)


def test_s2_staged_union_and_llm_share_search_substrate() -> None:
    union_spec = _load_yaml("scenarios/optimization/s2_staged_union.yaml")
    llm_spec = _load_yaml("scenarios/optimization/s2_staged_llm.yaml")

    assert union_spec["operator_control"]["controller"] == "random_uniform"
    assert llm_spec["operator_control"]["controller"] == "llm"
    assert _substrate_fields(llm_spec) == _substrate_fields(union_spec)


def _union_spec():
    return load_optimization_spec("scenarios/optimization/s1_typical_union.yaml")


def _layout():
    from optimizers.operator_pool.layout import VariableLayout

    return VariableLayout.from_optimization_spec(_union_spec())


def _parent_bundle():
    from optimizers.operator_pool.models import ParentBundle

    spec = _union_spec()
    layout = _layout()
    case = generate_benchmark_case("scenarios/optimization/s1_typical_union.yaml", spec)
    primary = extract_decision_vector(case, spec)
    offsets = np.linspace(-0.025, 0.025, num=layout.vector_size, dtype=np.float64)
    secondary = layout.clip(primary + offsets)
    return ParentBundle.from_vectors(primary, secondary)


def _controller_state():
    from optimizers.operator_pool.state import ControllerState

    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=17,
        parent_count=2,
        vector_size=32,
        metadata={
            "scenario": "s1_typical",
            "native_parameters": {
                "crossover": {"eta": 12.0, "prob": 0.9},
                "mutation": {"eta": 18.0},
            },
            "radiator_span_max": 0.48,
            "run_state": {
                "peak_temperature": 344.8,
                "temperature_gradient_rms": 8.9,
            },
        },
    )


def test_registry_profiles_expose_clean_vs_assisted_pools() -> None:
    from optimizers.operator_pool.operators import approved_operator_pool

    assert approved_operator_pool("primitive_clean") == PRIMITIVE_OPERATOR_IDS
    assert approved_operator_pool("primitive_plus_assisted") == (
        *PRIMITIVE_OPERATOR_IDS,
        *ASSISTED_OPERATOR_IDS,
    )


def test_registry_profile_contract_is_controller_agnostic() -> None:
    from optimizers.models import OptimizationSpec

    payload = load_optimization_spec("scenarios/optimization/s1_typical_union.yaml").to_dict()
    payload["operator_control"]["controller"] = "llm"
    payload["operator_control"]["registry_profile"] = "primitive_clean"
    payload["operator_control"]["operator_pool"] = list(PRIMITIVE_OPERATOR_IDS)

    assert OptimizationSpec.from_dict(payload).operator_control["registry_profile"] == "primitive_clean"


def test_behavior_profiles_cover_matrix_native_operator_ids() -> None:
    from optimizers.operator_pool.operators import get_operator_behavior_profile, native_operator_id_for_backbone

    for family, backbone in (("decomposition", "moead"), ("swarm", "cmopso")):
        operator_id = native_operator_id_for_backbone(family, backbone)
        profile = get_operator_behavior_profile(operator_id)
        assert profile.operator_id == operator_id
        assert profile.family == "native_baseline"
        assert profile.exploration_class == "stable"

    semantic_profile = get_operator_behavior_profile("hotspot_pull_toward_sink")
    assert semantic_profile.exploration_class == "custom"


def test_variable_layout_maps_s1_typical_variables_in_order() -> None:
    layout = _layout()

    assert layout.variable_ids[:4] == [
        "c01_x",
        "c01_y",
        "c02_x",
        "c02_y",
    ]
    assert layout.variable_ids[-4:] == [
        "c15_x",
        "c15_y",
        "sink_start",
        "sink_end",
    ]
    assert layout.vector_size == 32
    assert layout.index_of("c15_y") == 29
    assert layout.slot_for("sink_end").path == "boundary_features[0].end"
    assert layout.slot_for("sink_end").lower_bound == pytest.approx(0.2)
    assert layout.slot_for("sink_end").upper_bound == pytest.approx(0.95)


def test_parent_bundle_copies_numeric_vectors_and_preserves_shape() -> None:
    from optimizers.operator_pool.models import ParentBundle

    primary = np.asarray([0.1, 0.2, 0.3], dtype=np.float64)
    secondary = np.asarray([0.4, 0.5, 0.6], dtype=np.float64)

    bundle = ParentBundle.from_vectors(primary, secondary)
    primary[0] = -1.0
    secondary[1] = -2.0

    assert bundle.num_parents == 2
    assert bundle.primary.shape == (3,)
    assert bundle.secondary.shape == (3,)
    assert bundle.primary[0] == pytest.approx(0.1)
    assert bundle.secondary[1] == pytest.approx(0.5)


def test_random_controller_is_algorithm_agnostic() -> None:
    from optimizers.operator_pool.random_controller import RandomUniformController
    from optimizers.operator_pool.state import ControllerState

    controller = RandomUniformController()
    genetic_state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=9,
        parent_count=2,
        vector_size=32,
    )
    swarm_state = ControllerState(
        family="swarm",
        backbone="cmopso",
        generation_index=2,
        evaluation_index=9,
        parent_count=2,
        vector_size=32,
    )

    genetic_selection = controller.select_operator(
        genetic_state,
        PRIMITIVE_OPERATOR_IDS,
        np.random.default_rng(7),
    )
    swarm_selection = controller.select_operator(
        swarm_state,
        PRIMITIVE_OPERATOR_IDS,
        np.random.default_rng(7),
    )

    assert controller.controller_id == "random_uniform"
    assert genetic_selection == swarm_selection
    assert genetic_selection in PRIMITIVE_OPERATOR_IDS


@pytest.mark.parametrize("operator_id", (*PRIMITIVE_OPERATOR_IDS, *ASSISTED_OPERATOR_IDS))
def test_registered_operators_propose_bounded_numeric_vectors_without_mutating_parents(operator_id: str) -> None:
    from optimizers.operator_pool.operators import get_operator_definition

    layout = _layout()
    parents = _parent_bundle()
    state = _controller_state()
    primary_before = parents.primary.copy()
    secondary_before = parents.secondary.copy()

    proposal = get_operator_definition(operator_id).propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(17),
    )

    assert isinstance(proposal, np.ndarray)
    assert proposal.shape == (layout.vector_size,)
    assert proposal.dtype == np.float64
    assert np.isfinite(proposal).all()
    assert np.all(proposal >= layout.lower_bounds - 1.0e-12)
    assert np.all(proposal <= layout.upper_bounds + 1.0e-12)
    assert np.allclose(parents.primary, primary_before)
    assert np.allclose(parents.secondary, secondary_before)


def test_sink_peak_operators_add_bounded_rng_variation() -> None:
    from optimizers.operator_pool.operators import get_operator_definition

    layout = _layout()
    parents = _parent_bundle()
    state = _controller_state()

    slide_a = get_operator_definition("sink_shift").propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(17),
    )
    slide_b = get_operator_definition("sink_shift").propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(18),
    )
    repair_a = get_operator_definition("sink_resize").propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(17),
    )
    repair_b = get_operator_definition("sink_resize").propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(18),
    )

    sink_start_index = layout.index_of("sink_start")
    sink_end_index = layout.index_of("sink_end")

    assert not np.allclose(slide_a[[sink_start_index, sink_end_index]], slide_b[[sink_start_index, sink_end_index]])
    assert not np.allclose(repair_a[[sink_start_index, sink_end_index]], repair_b[[sink_start_index, sink_end_index]])


def test_trace_rows_round_trip_through_dict_payloads() -> None:
    from optimizers.operator_pool.trace import (
        ControllerAttemptTraceRow,
        ControllerTraceRow,
        OperatorAttemptTraceRow,
        OperatorTraceRow,
    )

    controller_attempt_row = ControllerAttemptTraceRow(
        generation_index=2,
        provisional_evaluation_index=9,
        decision_index=4,
        attempt_index=7,
        family="genetic",
        backbone="nsga2",
        controller_id="llm",
        candidate_operator_ids=(*PRIMITIVE_OPERATOR_IDS, *ASSISTED_OPERATOR_IDS),
        selected_operator_id="sink_retarget",
        accepted_for_evaluation=True,
        accepted_evaluation_indices=[9],
        metadata={"seed": 7},
    )
    controller_row = ControllerTraceRow(
        generation_index=2,
        evaluation_index=9,
        family="genetic",
        backbone="nsga2",
        controller_id="random_uniform",
        candidate_operator_ids=PRIMITIVE_OPERATOR_IDS,
        selected_operator_id="component_jitter_1",
        metadata={"seed": 7},
    )
    operator_attempt_row = OperatorAttemptTraceRow(
        generation_index=2,
        provisional_evaluation_index=9,
        decision_index=4,
        attempt_index=7,
        operator_id="sink_retarget",
        parent_count=2,
        parent_vectors=((0.1, 0.2), (0.3, 0.4)),
        proposal_vector=(0.2, 0.25),
        repaired_vector=(0.21, 0.26),
        accepted_for_evaluation=True,
        accepted_evaluation_indices=[9],
        metadata={"family": "genetic"},
    )
    operator_row = OperatorTraceRow(
        generation_index=2,
        evaluation_index=9,
        operator_id="component_jitter_1",
        parent_count=2,
        parent_vectors=((0.1, 0.2), (0.3, 0.4)),
        proposal_vector=(0.2, 0.25),
        metadata={"family": "genetic"},
    )

    assert ControllerAttemptTraceRow.from_dict(controller_attempt_row.to_dict()) == controller_attempt_row
    assert ControllerTraceRow.from_dict(controller_row.to_dict()) == controller_row
    assert OperatorAttemptTraceRow.from_dict(operator_attempt_row.to_dict()) == operator_attempt_row
    assert OperatorTraceRow.from_dict(operator_row.to_dict()) == operator_row


def test_operator_trace_rows_round_trip_with_evaluated_vector() -> None:
    from optimizers.operator_pool.trace import OperatorTraceRow

    row = OperatorTraceRow(
        generation_index=2,
        evaluation_index=9,
        operator_id="vector_sbx_pm",
        parent_count=2,
        parent_vectors=((0.1, 0.2), (0.3, 0.4)),
        proposal_vector=(0.11, 0.21),
        evaluated_vector=(0.12, 0.22),
        legality_policy_id="minimal_canonicalization",
        metadata={"decision_index": 4},
    )

    restored = OperatorTraceRow.from_dict(row.to_dict())
    assert restored.evaluated_vector == (0.12, 0.22)
    assert restored.legality_policy_id == "minimal_canonicalization"
