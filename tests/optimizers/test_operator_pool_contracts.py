from __future__ import annotations

import numpy as np
import pytest

from core.generator.paired_pipeline import generate_operating_case_pair
from optimizers.codec import extract_decision_vector
from optimizers.io import load_optimization_spec


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

APPROVED_UNION_OPERATOR_IDS = [
    "native_sbx_pm",
    *APPROVED_SHARED_OPERATOR_IDS,
]


def _baseline_spec():
    return load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml")


def _layout():
    from optimizers.operator_pool.layout import VariableLayout

    return VariableLayout.from_optimization_spec(_baseline_spec())


def _parent_bundle():
    from optimizers.operator_pool.models import ParentBundle

    spec = _baseline_spec()
    case = generate_operating_case_pair(spec.benchmark_source["template_path"], seed=int(spec.benchmark_source["seed"]))["hot"]
    layout = _layout()
    primary = extract_decision_vector(case, spec)
    secondary = layout.clip(
        primary
        + np.asarray(
            [0.08, 0.06, -0.09, 0.07, -0.12, -0.1, 0.04, -0.03],
            dtype=np.float64,
        )
    )
    return ParentBundle.from_vectors(primary, secondary)


def _controller_state():
    from optimizers.operator_pool.state import ControllerState

    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=9,
        parent_count=2,
        vector_size=8,
        metadata={
            "scenario": "panel-four-component-hot-cold",
            "native_parameters": {
                "crossover": {"eta": 10.0, "prob": 0.9},
                "mutation": {"eta": 15.0},
            },
        },
    )


def test_operator_pool_registry_matches_union_action_contract() -> None:
    from optimizers.operator_pool.operators import list_registered_operator_ids

    assert list_registered_operator_ids() == APPROVED_UNION_OPERATOR_IDS


def test_variable_layout_maps_active_benchmark_variables_in_order() -> None:
    layout = _layout()

    assert layout.variable_ids == [
        "processor_x",
        "processor_y",
        "rf_power_amp_x",
        "rf_power_amp_y",
        "battery_pack_x",
        "battery_pack_y",
        "radiator_start",
        "radiator_end",
    ]
    assert layout.vector_size == 8
    assert layout.index_of("battery_pack_y") == 5
    assert layout.slot_for("radiator_end").path == "boundary_features[0].end"
    assert layout.slot_for("radiator_end").lower_bound == pytest.approx(0.2)
    assert layout.slot_for("radiator_end").upper_bound == pytest.approx(0.95)


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
        vector_size=8,
    )
    swarm_state = ControllerState(
        family="swarm",
        backbone="cmopso",
        generation_index=2,
        evaluation_index=9,
        parent_count=2,
        vector_size=8,
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


def test_trace_rows_round_trip_through_dict_payloads() -> None:
    from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow

    controller_row = ControllerTraceRow(
        generation_index=2,
        evaluation_index=9,
        family="genetic",
        backbone="nsga2",
        controller_id="random_uniform",
        candidate_operator_ids=tuple(APPROVED_UNION_OPERATOR_IDS),
        selected_operator_id="local_refine",
        metadata={"seed": 7},
    )
    operator_row = OperatorTraceRow(
        generation_index=2,
        evaluation_index=9,
        operator_id="local_refine",
        parent_count=2,
        parent_vectors=((0.1, 0.2), (0.3, 0.4)),
        proposal_vector=(0.2, 0.25),
        metadata={"family": "genetic"},
    )

    assert ControllerTraceRow.from_dict(controller_row.to_dict()) == controller_row
    assert OperatorTraceRow.from_dict(operator_row.to_dict()) == operator_row
