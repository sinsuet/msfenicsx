from __future__ import annotations

import numpy as np
import pytest

from optimizers.codec import extract_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec


APPROVED_SHARED_OPERATOR_IDS = (
    "global_explore",
    "local_refine",
    "move_hottest_cluster_toward_sink",
    "spread_hottest_cluster",
    "smooth_high_gradient_band",
    "reduce_local_congestion",
    "repair_sink_budget",
    "slide_sink",
    "rebalance_layout",
)

APPROVED_UNION_OPERATOR_IDS = (
    "native_sbx_pm",
    *APPROVED_SHARED_OPERATOR_IDS,
)


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


def test_operator_registry_exposes_semantic_s1_typical_actions() -> None:
    from optimizers.operator_pool.operators import (
        approved_union_operator_ids_for_backbone,
        list_registered_operator_ids,
    )

    assert approved_union_operator_ids_for_backbone("genetic", "nsga2") == APPROVED_UNION_OPERATOR_IDS
    assert tuple(list_registered_operator_ids()) == APPROVED_UNION_OPERATOR_IDS


def test_behavior_profiles_cover_matrix_native_operator_ids() -> None:
    from optimizers.operator_pool.operators import get_operator_behavior_profile, native_operator_id_for_backbone

    for family, backbone in (("decomposition", "moead"), ("swarm", "cmopso")):
        operator_id = native_operator_id_for_backbone(family, backbone)
        profile = get_operator_behavior_profile(operator_id)
        assert profile.operator_id == operator_id
        assert profile.family == "native_baseline"
        assert profile.exploration_class == "stable"

    semantic_profile = get_operator_behavior_profile("move_hottest_cluster_toward_sink")
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
        APPROVED_UNION_OPERATOR_IDS,
        np.random.default_rng(7),
    )
    swarm_selection = controller.select_operator(
        swarm_state,
        APPROVED_UNION_OPERATOR_IDS,
        np.random.default_rng(7),
    )

    assert controller.controller_id == "random_uniform"
    assert genetic_selection == swarm_selection
    assert genetic_selection in APPROVED_UNION_OPERATOR_IDS


@pytest.mark.parametrize("operator_id", APPROVED_UNION_OPERATOR_IDS)
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

    slide_a = get_operator_definition("slide_sink").propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(17),
    )
    slide_b = get_operator_definition("slide_sink").propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(18),
    )
    repair_a = get_operator_definition("repair_sink_budget").propose(
        parents=parents,
        state=state,
        variable_layout=layout,
        rng=np.random.default_rng(17),
    )
    repair_b = get_operator_definition("repair_sink_budget").propose(
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
        candidate_operator_ids=APPROVED_UNION_OPERATOR_IDS,
        selected_operator_id="slide_sink",
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
        candidate_operator_ids=APPROVED_UNION_OPERATOR_IDS,
        selected_operator_id="reduce_local_congestion",
        metadata={"seed": 7},
    )
    operator_attempt_row = OperatorAttemptTraceRow(
        generation_index=2,
        provisional_evaluation_index=9,
        decision_index=4,
        attempt_index=7,
        operator_id="slide_sink",
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
        operator_id="reduce_local_congestion",
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
