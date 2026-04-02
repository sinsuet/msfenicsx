from __future__ import annotations

import numpy as np
import pytest

from optimizers.operator_pool.domain_state import build_progress_state
from optimizers.operator_pool.reflection import summarize_operator_history
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.state_builder import build_controller_state
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow


def _parents() -> ParentBundle:
    return ParentBundle.from_vectors(
        np.asarray([0.2, 0.3, 0.4], dtype=np.float64),
        np.asarray([0.25, 0.35, 0.45], dtype=np.float64),
    )


_THERMAL_VARIABLE_IDS = (
    "processor_x",
    "processor_y",
    "rf_power_amp_x",
    "rf_power_amp_y",
    "battery_pack_x",
    "battery_pack_y",
    "radiator_start",
    "radiator_end",
)


def _thermal_parents() -> ParentBundle:
    return ParentBundle.from_vectors(
        np.asarray([0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71], dtype=np.float64),
        np.asarray([0.28, 0.55, 0.46, 0.52, 0.37, 0.41, 0.16, 0.76], dtype=np.float64),
    )


def _record(
    evaluation_index: int,
    vector: tuple[float, ...],
    *,
    feasible: bool,
    hot_pa_limit: float,
    hot_processor_limit: float,
    cold_battery_floor: float,
    hot_component_spread_limit: float,
    hot_pa_peak: float,
    cold_battery_min: float,
    radiator_resource: float,
) -> dict[str, object]:
    return {
        "evaluation_index": evaluation_index,
        "source": "optimizer",
        "feasible": feasible,
        "decision_vector": {
            variable_id: float(value)
            for variable_id, value in zip(_THERMAL_VARIABLE_IDS, vector, strict=True)
        },
        "objective_values": {
            "minimize_hot_pa_peak": float(hot_pa_peak),
            "maximize_cold_battery_min": float(cold_battery_min),
            "minimize_radiator_resource": float(radiator_resource),
        },
        "constraint_values": {
            "hot_pa_limit": float(hot_pa_limit),
            "hot_processor_limit": float(hot_processor_limit),
            "cold_battery_floor": float(cold_battery_floor),
            "hot_component_spread_limit": float(hot_component_spread_limit),
        },
        "case_reports": {},
    }


def test_build_controller_state_captures_recent_decisions_and_operator_summary() -> None:
    controller_trace = [
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=1,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="native_sbx_pm",
            metadata={"decision_index": 0, "fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=2,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"decision_index": 1, "fallback_used": True},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"decision_index": 2, "fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=0,
            evaluation_index=1,
            operator_id="native_sbx_pm",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.21, 0.31, 0.41),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=0,
            evaluation_index=2,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.22, 0.32, 0.42),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=3,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.23, 0.33, 0.43),
            metadata={},
        ),
    ]

    state = build_controller_state(
        _parents(),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=9,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        metadata={"search_phase": "feasible_refine"},
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        recent_window=2,
    )

    assert state.metadata["search_phase"] == "feasible_refine"
    assert state.metadata["candidate_operator_ids"] == ["native_sbx_pm", "local_refine"]
    assert len(state.metadata["recent_decisions"]) == 2
    assert state.metadata["recent_decisions"] == [
        {
            "evaluation_index": 2,
            "selected_operator_id": "local_refine",
            "fallback_used": True,
            "llm_valid": False,
        },
        {
            "evaluation_index": 3,
            "selected_operator_id": "local_refine",
            "fallback_used": False,
            "llm_valid": True,
        },
    ]
    assert state.metadata["recent_operator_counts"]["local_refine"]["recent_selection_count"] == 2
    assert state.metadata["recent_operator_counts"]["local_refine"]["recent_fallback_selection_count"] == 1
    assert state.metadata["recent_operator_counts"]["local_refine"]["recent_llm_valid_selection_count"] == 1
    assert state.metadata["operator_summary"]["native_sbx_pm"]["selection_count"] == 1
    assert state.metadata["operator_summary"]["local_refine"]["selection_count"] == 2
    assert state.metadata["operator_summary"]["local_refine"]["recent_selection_count"] == 2
    assert state.metadata["operator_summary"]["local_refine"]["fallback_selection_count"] == 1
    assert state.metadata["operator_summary"]["local_refine"]["llm_valid_selection_count"] == 1


def test_summarize_operator_history_separates_fallback_and_llm_valid_counts() -> None:
    controller_trace = [
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=1,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="native_sbx_pm",
            metadata={"fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=2,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"fallback_used": True},
        ),
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=0,
            evaluation_index=1,
            operator_id="native_sbx_pm",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.21, 0.31, 0.41),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=0,
            evaluation_index=2,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.22, 0.32, 0.42),
            metadata={},
        ),
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=2,
    )

    assert summary["local_refine"]["selection_count"] == 2
    assert summary["local_refine"]["proposal_count"] == 1
    assert summary["local_refine"]["fallback_selection_count"] == 1
    assert summary["local_refine"]["llm_valid_selection_count"] == 1
    assert summary["local_refine"]["recent_fallback_selection_count"] == 1
    assert summary["local_refine"]["recent_llm_valid_selection_count"] == 1
    assert summary["native_sbx_pm"]["fallback_selection_count"] == 0


def test_build_controller_state_includes_run_parent_archive_and_regime_blocks() -> None:
    parents = _thermal_parents()
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=7,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="native_sbx_pm",
            metadata={"decision_index": 0, "fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=8,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"decision_index": 1, "fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=7,
            operator_id="native_sbx_pm",
            parent_count=2,
            parent_vectors=tuple(tuple(float(value) for value in vector.tolist()) for vector in parents.vectors),
            proposal_vector=tuple(float(value) for value in parents.primary.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=8,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=tuple(tuple(float(value) for value in vector.tolist()) for vector in parents.vectors),
            proposal_vector=tuple(float(value) for value in parents.secondary.tolist()),
            metadata={},
        ),
    ]
    history = [
        _record(
            2,
            tuple(float(value) for value in parents.primary.tolist()),
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.6,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.9,
            radiator_resource=0.53,
        ),
        _record(
            3,
            tuple(float(value) for value in parents.secondary.tolist()),
            feasible=True,
            hot_pa_limit=-4.3,
            hot_processor_limit=-1.8,
            cold_battery_floor=-0.1,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=349.4,
            cold_battery_min=259.8,
            radiator_resource=0.49,
        ),
        _record(
            4,
            (0.31, 0.58, 0.49, 0.57, 0.36, 0.43, 0.14, 0.8),
            feasible=True,
            hot_pa_limit=-5.1,
            hot_processor_limit=-2.1,
            cold_battery_floor=-0.2,
            hot_component_spread_limit=-0.5,
            hot_pa_peak=348.7,
            cold_battery_min=260.1,
            radiator_resource=0.44,
        ),
    ]

    state = build_controller_state(
        parents,
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=9,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        metadata={
            "design_variable_ids": list(_THERMAL_VARIABLE_IDS),
            "decision_index": 5,
            "total_evaluation_budget": 20,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=2,
    )

    run_state = state.metadata["run_state"]
    assert run_state["evaluations_used"] == 8
    assert run_state["evaluations_remaining"] == 12
    assert run_state["feasible_rate"] == pytest.approx(2.0 / 3.0)
    assert run_state["first_feasible_eval"] == 3

    parent_state = state.metadata["parent_state"]
    assert parent_state["parent_indices"] == []
    assert parent_state["parents"][0]["decision_vector"]["processor_x"] == pytest.approx(0.22)
    assert parent_state["parents"][0]["feasible"] is False
    assert parent_state["parents"][0]["total_violation"] == pytest.approx(0.6)
    assert parent_state["parents"][0]["dominant_violation"]["constraint_id"] == "cold_battery_floor"
    assert parent_state["parents"][1]["feasible"] is True
    assert parent_state["parents"][1]["objective_summary"]["maximize_cold_battery_min"] == pytest.approx(259.8)

    archive_state = state.metadata["archive_state"]
    assert archive_state["best_feasible"]["evaluation_index"] == 4
    assert archive_state["best_near_feasible"]["evaluation_index"] == 2

    domain_regime = state.metadata["domain_regime"]
    assert domain_regime["phase"] == "feasible_refine"
    assert domain_regime["dominant_constraint_family"] == "cold_dominant"
    assert state.metadata["search_phase"] == "feasible_refine"


def test_build_controller_state_includes_frontier_aware_archive_state() -> None:
    history = [
        _record(
            1,
            (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71),
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.8,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.5,
            radiator_resource=0.53,
        ),
        _record(
            2,
            (0.24, 0.52, 0.42, 0.48, 0.34, 0.28, 0.17, 0.73),
            feasible=True,
            hot_pa_limit=-4.2,
            hot_processor_limit=-1.4,
            cold_battery_floor=-0.1,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=350.0,
            cold_battery_min=259.8,
            radiator_resource=0.49,
        ),
        _record(
            3,
            (0.26, 0.54, 0.44, 0.5, 0.35, 0.31, 0.16, 0.75),
            feasible=True,
            hot_pa_limit=-4.5,
            hot_processor_limit=-1.8,
            cold_battery_floor=-0.2,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=349.2,
            cold_battery_min=260.0,
            radiator_resource=0.52,
        ),
        _record(
            4,
            (0.27, 0.55, 0.45, 0.51, 0.36, 0.32, 0.15, 0.76),
            feasible=False,
            hot_pa_limit=-3.5,
            hot_processor_limit=-1.3,
            cold_battery_floor=0.2,
            hot_component_spread_limit=-0.1,
            hot_pa_peak=349.5,
            cold_battery_min=259.7,
            radiator_resource=0.48,
        ),
    ]

    state = build_controller_state(
        _thermal_parents(),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=5,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        metadata={
            "design_variable_ids": list(_THERMAL_VARIABLE_IDS),
            "decision_index": 4,
            "total_evaluation_budget": 20,
        },
        history=history,
        recent_window=2,
    )

    archive_state = state.metadata["archive_state"]
    assert archive_state["pareto_size"] == 2
    assert archive_state["recent_frontier_add_count"] == 2
    assert archive_state["evaluations_since_frontier_add"] == 1
    assert archive_state["recent_feasible_regression_count"] == 1
    assert archive_state["recent_feasible_preservation_count"] == 0


def test_build_controller_state_includes_generic_progress_state() -> None:
    history = [
        _record(
            1,
            (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71),
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=1.0,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.5,
            radiator_resource=0.53,
        ),
        _record(
            2,
            (0.24, 0.52, 0.42, 0.48, 0.34, 0.28, 0.17, 0.73),
            feasible=False,
            hot_pa_limit=-2.1,
            hot_processor_limit=-1.1,
            cold_battery_floor=0.7,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=352.0,
            cold_battery_min=258.8,
            radiator_resource=0.52,
        ),
        _record(
            3,
            (0.26, 0.54, 0.44, 0.5, 0.35, 0.31, 0.16, 0.75),
            feasible=False,
            hot_pa_limit=-2.2,
            hot_processor_limit=-1.0,
            cold_battery_floor=0.4,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=351.6,
            cold_battery_min=259.1,
            radiator_resource=0.51,
        ),
    ]

    state = build_controller_state(
        _thermal_parents(),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=4,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        metadata={
            "design_variable_ids": list(_THERMAL_VARIABLE_IDS),
            "decision_index": 2,
            "total_evaluation_budget": 20,
        },
        history=history,
        recent_window=2,
    )

    progress_state = state.metadata["progress_state"]
    assert progress_state["phase"] == "prefeasible_progress"
    assert progress_state["first_feasible_found"] is False
    assert progress_state["recent_no_progress_count"] == 0
    assert progress_state["recent_best_near_feasible_improvement"] == pytest.approx(-0.3)


def test_build_controller_state_tracks_prefeasible_reset_windows_and_recent_role_share() -> None:
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=2,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "sbx_pm_global", "local_refine"),
            selected_operator_id="native_sbx_pm",
            metadata={
                "fallback_used": False,
                "policy_phase": "prefeasible_stagnation",
                "guardrail_policy_reset_active": True,
                "guardrail_reason_codes": ["prefeasible_forced_reset"],
            },
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "sbx_pm_global", "local_refine"),
            selected_operator_id="local_refine",
            metadata={
                "fallback_used": False,
                "policy_phase": "prefeasible_stagnation",
                "guardrail_policy_reset_active": True,
                "guardrail_reason_codes": ["prefeasible_forced_reset"],
            },
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=4,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "sbx_pm_global", "local_refine"),
            selected_operator_id="native_sbx_pm",
            metadata={
                "fallback_used": False,
                "policy_phase": "prefeasible_stagnation",
                "guardrail_policy_reset_active": True,
                "guardrail_reason_codes": ["prefeasible_forced_reset"],
            },
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=2,
            operator_id="native_sbx_pm",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.21, 0.31, 0.41),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=3,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.22, 0.32, 0.42),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="native_sbx_pm",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.23, 0.33, 0.43),
            metadata={},
        ),
    ]
    history = [
        _record(
            1,
            tuple(float(value) for value in _thermal_parents().primary.tolist()),
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=1.0,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.5,
            radiator_resource=0.53,
        ),
        _record(
            2,
            tuple(float(value) for value in _thermal_parents().secondary.tolist()),
            feasible=False,
            hot_pa_limit=-2.1,
            hot_processor_limit=-1.1,
            cold_battery_floor=0.7,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=352.0,
            cold_battery_min=258.8,
            radiator_resource=0.52,
        ),
        _record(
            3,
            (0.26, 0.54, 0.44, 0.5, 0.35, 0.31, 0.16, 0.75),
            feasible=False,
            hot_pa_limit=-2.2,
            hot_processor_limit=-1.0,
            cold_battery_floor=0.4,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=351.6,
            cold_battery_min=259.1,
            radiator_resource=0.51,
        ),
    ]

    state = build_controller_state(
        _thermal_parents(),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=5,
        candidate_operator_ids=("native_sbx_pm", "sbx_pm_global", "local_refine"),
        metadata={
            "design_variable_ids": list(_THERMAL_VARIABLE_IDS),
            "decision_index": 4,
            "total_evaluation_budget": 20,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=3,
    )

    progress_state = state.metadata["progress_state"]
    assert progress_state["prefeasible_reset_window_count"] == 3
    assert progress_state["prefeasible_recent_stable_family_mix"] == {
        "native_baseline": 2,
        "local_refine": 1,
    }
    assert state.metadata["operator_summary"]["native_sbx_pm"]["recent_family_share"] == pytest.approx(2.0 / 3.0)
    assert state.metadata["operator_summary"]["native_sbx_pm"]["recent_role_share"] == pytest.approx(2.0 / 3.0)
    assert state.metadata["operator_summary"]["local_refine"]["recent_family_share"] == pytest.approx(1.0 / 3.0)
    assert state.metadata["operator_summary"]["local_refine"]["recent_role_share"] == pytest.approx(1.0 / 3.0)


def test_build_progress_state_distinguishes_post_feasible_expand_preserve_recover_modes() -> None:
    preserve_history = [
        _record(
            1,
            (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71),
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.8,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.5,
            radiator_resource=0.53,
        ),
        _record(
            2,
            (0.24, 0.52, 0.42, 0.48, 0.34, 0.28, 0.17, 0.73),
            feasible=True,
            hot_pa_limit=-4.2,
            hot_processor_limit=-1.4,
            cold_battery_floor=-0.1,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=350.0,
            cold_battery_min=259.8,
            radiator_resource=0.49,
        ),
        _record(
            3,
            (0.26, 0.54, 0.44, 0.5, 0.35, 0.31, 0.16, 0.75),
            feasible=True,
            hot_pa_limit=-4.5,
            hot_processor_limit=-1.8,
            cold_battery_floor=-0.2,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=349.2,
            cold_battery_min=260.0,
            radiator_resource=0.47,
        ),
    ]
    expand_history = [
        *preserve_history[:2],
        _record(
            3,
            (0.27, 0.53, 0.43, 0.49, 0.35, 0.29, 0.18, 0.74),
            feasible=True,
            hot_pa_limit=-4.1,
            hot_processor_limit=-1.5,
            cold_battery_floor=-0.12,
            hot_component_spread_limit=-0.28,
            hot_pa_peak=350.4,
            cold_battery_min=259.7,
            radiator_resource=0.5,
        ),
        _record(
            4,
            (0.28, 0.54, 0.44, 0.5, 0.36, 0.3, 0.19, 0.75),
            feasible=True,
            hot_pa_limit=-4.0,
            hot_processor_limit=-1.4,
            cold_battery_floor=-0.1,
            hot_component_spread_limit=-0.25,
            hot_pa_peak=350.5,
            cold_battery_min=259.6,
            radiator_resource=0.51,
        ),
    ]
    recover_history = [
        *preserve_history[:2],
        _record(
            3,
            (0.28, 0.55, 0.45, 0.51, 0.36, 0.32, 0.15, 0.76),
            feasible=False,
            hot_pa_limit=-3.5,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.3,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=350.1,
            cold_battery_min=259.4,
            radiator_resource=0.5,
        ),
    ]

    preserve_progress = build_progress_state(history=preserve_history)
    expand_progress = build_progress_state(history=expand_history)
    recover_progress = build_progress_state(history=recover_history)

    assert preserve_progress["post_feasible_mode"] == "preserve"
    assert expand_progress["post_feasible_mode"] == "expand"
    assert expand_progress["recent_frontier_stagnation_count"] == 2
    assert recover_progress["post_feasible_mode"] == "recover"


def test_summarize_operator_history_tracks_feasible_entry_preservation_and_violation_delta() -> None:
    parent_a = (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71)
    parent_b = (0.25, 0.53, 0.43, 0.49, 0.35, 0.27, 0.17, 0.73)
    feasible_parent_a = (0.28, 0.55, 0.46, 0.52, 0.37, 0.41, 0.16, 0.76)
    feasible_parent_b = (0.31, 0.58, 0.49, 0.57, 0.36, 0.43, 0.14, 0.8)
    history = [
        _record(
            1,
            parent_a,
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.6,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.9,
            radiator_resource=0.53,
        ),
        _record(
            2,
            parent_b,
            feasible=False,
            hot_pa_limit=-1.8,
            hot_processor_limit=-1.1,
            cold_battery_floor=0.4,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=352.0,
            cold_battery_min=259.1,
            radiator_resource=0.54,
        ),
        _record(
            3,
            feasible_parent_a,
            feasible=True,
            hot_pa_limit=-4.3,
            hot_processor_limit=-1.8,
            cold_battery_floor=-0.1,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=349.4,
            cold_battery_min=259.8,
            radiator_resource=0.49,
        ),
        _record(
            4,
            feasible_parent_b,
            feasible=True,
            hot_pa_limit=-5.1,
            hot_processor_limit=-2.1,
            cold_battery_floor=-0.2,
            hot_component_spread_limit=-0.5,
            hot_pa_peak=348.7,
            cold_battery_min=260.1,
            radiator_resource=0.44,
        ),
        _record(
            5,
            (0.27, 0.57, 0.45, 0.54, 0.34, 0.39, 0.16, 0.78),
            feasible=True,
            hot_pa_limit=-4.7,
            hot_processor_limit=-2.0,
            cold_battery_floor=-0.15,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=349.0,
            cold_battery_min=259.9,
            radiator_resource=0.47,
        ),
        _record(
            6,
            (0.24, 0.5, 0.42, 0.46, 0.34, 0.23, 0.19, 0.69),
            feasible=False,
            hot_pa_limit=-1.6,
            hot_processor_limit=-1.0,
            cold_battery_floor=0.7,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=353.0,
            cold_battery_min=258.8,
            radiator_resource=0.52,
        ),
    ]
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=5,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("hot_pair_to_sink", "local_refine"),
            selected_operator_id="hot_pair_to_sink",
            metadata={"fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=6,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("hot_pair_to_sink", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=5,
            operator_id="hot_pair_to_sink",
            parent_count=2,
            parent_vectors=(parent_a, parent_b),
            proposal_vector=(0.27, 0.57, 0.45, 0.54, 0.34, 0.39, 0.16, 0.78),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=6,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=(feasible_parent_a, feasible_parent_b),
            proposal_vector=(0.24, 0.5, 0.42, 0.46, 0.34, 0.23, 0.19, 0.69),
            metadata={},
        ),
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=2,
        history=history,
        design_variable_ids=_THERMAL_VARIABLE_IDS,
    )

    assert summary["hot_pair_to_sink"]["feasible_entry_count"] == 1
    assert summary["hot_pair_to_sink"]["feasible_preservation_count"] == 0
    assert summary["hot_pair_to_sink"]["avg_total_violation_delta"] == pytest.approx(-0.5)
    assert "cold_dominant" in summary["hot_pair_to_sink"]["recent_helpful_regimes"]
    assert summary["local_refine"]["feasible_entry_count"] == 0
    assert summary["local_refine"]["feasible_preservation_count"] == 0
    assert summary["local_refine"]["avg_total_violation_delta"] == pytest.approx(0.7)
    assert "feasible_refine" in summary["local_refine"]["recent_harmful_regimes"]


def test_summarize_operator_history_reports_pareto_and_regression_evidence() -> None:
    parent_a = (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71)
    parent_b = (0.25, 0.53, 0.43, 0.49, 0.35, 0.27, 0.17, 0.73)
    feasible_parent_a = (0.28, 0.55, 0.46, 0.52, 0.37, 0.41, 0.16, 0.76)
    feasible_parent_b = (0.31, 0.58, 0.49, 0.57, 0.36, 0.43, 0.14, 0.8)
    frontier_child = (0.27, 0.57, 0.45, 0.54, 0.34, 0.39, 0.16, 0.78)
    regression_child = (0.24, 0.5, 0.42, 0.46, 0.34, 0.23, 0.19, 0.69)
    history = [
        _record(
            1,
            parent_a,
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.6,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.9,
            radiator_resource=0.53,
        ),
        _record(
            2,
            parent_b,
            feasible=False,
            hot_pa_limit=-1.8,
            hot_processor_limit=-1.1,
            cold_battery_floor=0.4,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=352.0,
            cold_battery_min=259.1,
            radiator_resource=0.54,
        ),
        _record(
            3,
            feasible_parent_a,
            feasible=True,
            hot_pa_limit=-4.3,
            hot_processor_limit=-1.8,
            cold_battery_floor=-0.1,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=349.4,
            cold_battery_min=259.8,
            radiator_resource=0.49,
        ),
        _record(
            4,
            feasible_parent_b,
            feasible=True,
            hot_pa_limit=-5.1,
            hot_processor_limit=-2.1,
            cold_battery_floor=-0.2,
            hot_component_spread_limit=-0.5,
            hot_pa_peak=348.7,
            cold_battery_min=260.1,
            radiator_resource=0.44,
        ),
        _record(
            5,
            frontier_child,
            feasible=True,
            hot_pa_limit=-4.8,
            hot_processor_limit=-2.0,
            cold_battery_floor=-0.15,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=348.4,
            cold_battery_min=260.0,
            radiator_resource=0.43,
        ),
        _record(
            6,
            regression_child,
            feasible=False,
            hot_pa_limit=-1.6,
            hot_processor_limit=-1.0,
            cold_battery_floor=0.7,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=353.0,
            cold_battery_min=258.8,
            radiator_resource=0.52,
        ),
    ]
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=5,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("hot_pair_to_sink", "local_refine"),
            selected_operator_id="hot_pair_to_sink",
            metadata={"fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=6,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("hot_pair_to_sink", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=5,
            operator_id="hot_pair_to_sink",
            parent_count=2,
            parent_vectors=(feasible_parent_a, feasible_parent_b),
            proposal_vector=frontier_child,
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=6,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=(feasible_parent_a, feasible_parent_b),
            proposal_vector=regression_child,
            metadata={},
        ),
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=2,
        history=history,
        design_variable_ids=_THERMAL_VARIABLE_IDS,
    )

    assert summary["hot_pair_to_sink"]["pareto_contribution_count"] == 1
    assert summary["hot_pair_to_sink"]["post_feasible_avg_objective_delta"] < 0.0
    assert summary["local_refine"]["feasible_regression_count"] == 1


def test_summarize_operator_history_includes_family_and_evidence_rollups() -> None:
    parent_a = (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71)
    parent_b = (0.25, 0.53, 0.43, 0.49, 0.35, 0.27, 0.17, 0.73)
    feasible_child = (0.27, 0.57, 0.45, 0.54, 0.34, 0.39, 0.16, 0.78)
    bad_child = (0.24, 0.5, 0.42, 0.46, 0.34, 0.23, 0.19, 0.69)
    history = [
        _record(
            1,
            parent_a,
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.6,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.9,
            radiator_resource=0.53,
        ),
        _record(
            2,
            parent_b,
            feasible=False,
            hot_pa_limit=-1.8,
            hot_processor_limit=-1.1,
            cold_battery_floor=0.4,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=352.0,
            cold_battery_min=259.1,
            radiator_resource=0.54,
        ),
        _record(
            3,
            feasible_child,
            feasible=True,
            hot_pa_limit=-4.3,
            hot_processor_limit=-1.8,
            cold_battery_floor=-0.1,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=349.4,
            cold_battery_min=259.8,
            radiator_resource=0.49,
        ),
        _record(
            4,
            bad_child,
            feasible=False,
            hot_pa_limit=-1.6,
            hot_processor_limit=-1.0,
            cold_battery_floor=0.7,
            hot_component_spread_limit=-0.2,
            hot_pa_peak=353.0,
            cold_battery_min=258.8,
            radiator_resource=0.52,
        ),
    ]
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("hot_pair_to_sink", "local_refine"),
            selected_operator_id="hot_pair_to_sink",
            metadata={"fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=4,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("hot_pair_to_sink", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=3,
            operator_id="hot_pair_to_sink",
            parent_count=2,
            parent_vectors=(parent_a, parent_b),
            proposal_vector=feasible_child,
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=(parent_a, parent_b),
            proposal_vector=bad_child,
            metadata={},
        ),
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=2,
        history=history,
        design_variable_ids=_THERMAL_VARIABLE_IDS,
    )

    assert summary["hot_pair_to_sink"]["operator_family"] == "speculative_custom"
    assert summary["hot_pair_to_sink"]["evidence_level"] == "trusted"
    assert summary["local_refine"]["operator_family"] == "local_refine"
    assert summary["local_refine"]["evidence_level"] == "speculative"


def test_build_controller_state_tracks_near_feasible_entry_progress_and_dominant_violation_family() -> None:
    history = [
        _record(
            1,
            (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71),
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.9,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.5,
            radiator_resource=0.53,
        ),
        _record(
            2,
            (0.24, 0.52, 0.42, 0.48, 0.34, 0.28, 0.17, 0.73),
            feasible=False,
            hot_pa_limit=-2.1,
            hot_processor_limit=-1.1,
            cold_battery_floor=0.35,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=352.0,
            cold_battery_min=259.15,
            radiator_resource=0.52,
        ),
        _record(
            3,
            (0.245, 0.525, 0.425, 0.485, 0.345, 0.285, 0.168, 0.735),
            feasible=False,
            hot_pa_limit=-2.05,
            hot_processor_limit=-1.08,
            cold_battery_floor=0.34,
            hot_component_spread_limit=-0.28,
            hot_pa_peak=351.95,
            cold_battery_min=259.16,
            radiator_resource=0.515,
        ),
        _record(
            4,
            (0.247, 0.527, 0.427, 0.487, 0.347, 0.287, 0.167, 0.737),
            feasible=False,
            hot_pa_limit=-2.03,
            hot_processor_limit=-1.07,
            cold_battery_floor=0.36,
            hot_component_spread_limit=-0.27,
            hot_pa_peak=351.98,
            cold_battery_min=259.14,
            radiator_resource=0.514,
        ),
    ]

    state = build_controller_state(
        _thermal_parents(),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=5,
        candidate_operator_ids=("native_sbx_pm", "sbx_pm_global", "local_refine"),
        metadata={
            "design_variable_ids": list(_THERMAL_VARIABLE_IDS),
            "decision_index": 4,
            "total_evaluation_budget": 20,
        },
        history=history,
        recent_window=3,
    )

    progress_state = state.metadata["progress_state"]
    assert progress_state["prefeasible_mode"] == "convert"
    assert progress_state["evaluations_since_near_feasible_improvement"] >= 0
    assert progress_state["recent_dominant_violation_family"] == "cold_dominant"
    assert state.metadata["archive_state"]["best_near_feasible"]["dominant_violation"]["constraint_id"] == "cold_battery_floor"


def test_summarize_operator_history_tracks_violation_family_relief_counts() -> None:
    parent_a = (0.22, 0.51, 0.41, 0.47, 0.33, 0.24, 0.18, 0.71)
    parent_b = (0.24, 0.52, 0.42, 0.48, 0.34, 0.28, 0.17, 0.73)
    improved_child = (0.245, 0.525, 0.425, 0.485, 0.345, 0.305, 0.168, 0.735)
    history = [
        _record(
            1,
            parent_a,
            feasible=False,
            hot_pa_limit=-2.0,
            hot_processor_limit=-1.2,
            cold_battery_floor=0.9,
            hot_component_spread_limit=-0.4,
            hot_pa_peak=352.5,
            cold_battery_min=258.5,
            radiator_resource=0.53,
        ),
        _record(
            2,
            parent_b,
            feasible=False,
            hot_pa_limit=-2.1,
            hot_processor_limit=-1.1,
            cold_battery_floor=0.6,
            hot_component_spread_limit=-0.3,
            hot_pa_peak=352.0,
            cold_battery_min=258.9,
            radiator_resource=0.52,
        ),
        _record(
            3,
            improved_child,
            feasible=False,
            hot_pa_limit=-2.15,
            hot_processor_limit=-1.15,
            cold_battery_floor=0.2,
            hot_component_spread_limit=-0.25,
            hot_pa_peak=351.8,
            cold_battery_min=259.3,
            radiator_resource=0.51,
        ),
    ]
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=3,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=(parent_a, parent_b),
            proposal_vector=improved_child,
            metadata={},
        ),
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=1,
        history=history,
        design_variable_ids=_THERMAL_VARIABLE_IDS,
    )

    assert summary["local_refine"]["dominant_violation_relief_count"] >= 1
    assert "cold_dominant" in summary["local_refine"]["recent_entry_helpful_regimes"]
