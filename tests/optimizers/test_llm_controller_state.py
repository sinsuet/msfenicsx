from __future__ import annotations

import numpy as np
import pytest

from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.reflection import summarize_operator_history
from optimizers.operator_pool.state_builder import build_controller_state
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow


_S1_VARIABLE_IDS = tuple(
    [
        *(value for component_index in range(1, 16) for value in (f"c{component_index:02d}_x", f"c{component_index:02d}_y")),
        "sink_start",
        "sink_end",
    ]
)


def _vector(*, sink_start: float = 0.22, sink_end: float = 0.62, x_shift: float = 0.0, y_shift: float = 0.0) -> np.ndarray:
    values: list[float] = []
    for row in range(3):
        for col in range(5):
            component_index = row * 5 + col
            values.append(0.18 + 0.14 * col + x_shift + 0.003 * component_index)
            values.append(0.18 + 0.15 * row + y_shift + 0.004 * component_index)
    values.extend([sink_start, sink_end])
    return np.asarray(values, dtype=np.float64)


def _parents() -> ParentBundle:
    return ParentBundle.from_vectors(
        _vector(sink_start=0.18, sink_end=0.72),
        _vector(sink_start=0.22, sink_end=0.66, x_shift=0.01, y_shift=0.01),
    )


def _record(
    evaluation_index: int,
    vector: np.ndarray,
    *,
    feasible: bool,
    peak_temperature: float,
    temperature_gradient_rms: float,
    c01_temperature_violation: float,
    panel_spread_violation: float,
) -> dict[str, object]:
    decision_vector = {
        variable_id: float(value)
        for variable_id, value in zip(_S1_VARIABLE_IDS, vector.tolist(), strict=True)
    }
    sink_span = float(decision_vector["sink_end"] - decision_vector["sink_start"])
    return {
        "evaluation_index": evaluation_index,
        "source": "optimizer",
        "feasible": feasible,
        "decision_vector": decision_vector,
        "objective_values": {
            "minimize_peak_temperature": float(peak_temperature),
            "minimize_temperature_gradient_rms": float(temperature_gradient_rms),
        },
        "constraint_values": {
            "radiator_span_budget": max(0.0, sink_span - 0.48),
            "c01_peak_temperature_limit": float(c01_temperature_violation),
            "panel_temperature_spread_limit": float(panel_spread_violation),
        },
        "evaluation_report": {
            "metric_values": {
                "summary.temperature_max": float(peak_temperature),
                "summary.temperature_gradient_rms": float(temperature_gradient_rms),
                "case.total_radiator_span": float(sink_span),
            }
        },
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
            "generation_local": False,
        },
        {
            "evaluation_index": 3,
            "selected_operator_id": "local_refine",
            "fallback_used": False,
            "llm_valid": True,
            "generation_local": False,
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


def test_build_controller_state_tracks_generation_local_memory_without_rewriting_historical_evidence() -> None:
    controller_trace = [
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=1,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "slide_sink"),
            selected_operator_id="native_sbx_pm",
            metadata={"decision_index": 0, "fallback_used": False},
        )
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
        )
    ]
    generation_local_controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=7,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "slide_sink"),
            selected_operator_id="slide_sink",
            metadata={"decision_index": 2, "fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=8,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "slide_sink"),
            selected_operator_id="slide_sink",
            metadata={"decision_index": 3, "fallback_used": False},
        ),
    ]

    state = build_controller_state(
        _parents(),
        family="genetic",
        backbone="nsga2",
        generation_index=1,
        evaluation_index=9,
        candidate_operator_ids=("native_sbx_pm", "slide_sink"),
        metadata={"generation_target_offsprings": 4},
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        local_controller_trace=generation_local_controller_trace,
        recent_window=4,
    )

    assert state.metadata["recent_decisions"] == [
        {
            "evaluation_index": 1,
            "selected_operator_id": "native_sbx_pm",
            "fallback_used": False,
            "llm_valid": True,
            "generation_local": False,
        },
        {
            "evaluation_index": 7,
            "selected_operator_id": "slide_sink",
            "fallback_used": False,
            "llm_valid": True,
            "generation_local": True,
        },
        {
            "evaluation_index": 8,
            "selected_operator_id": "slide_sink",
            "fallback_used": False,
            "llm_valid": True,
            "generation_local": True,
        },
    ]
    assert state.metadata["recent_operator_counts"]["slide_sink"]["recent_selection_count"] == 2
    assert state.metadata["generation_local_memory"]["accepted_count"] == 2
    assert state.metadata["generation_local_memory"]["accepted_share"] == pytest.approx(0.5)
    assert state.metadata["generation_local_memory"]["dominant_operator_id"] == "slide_sink"
    assert state.metadata["generation_local_memory"]["dominant_operator_share"] == pytest.approx(1.0)
    assert state.metadata["operator_summary"]["native_sbx_pm"]["selection_count"] == 1
    assert "slide_sink" not in state.metadata["operator_summary"]


def test_summarize_operator_history_separates_fallback_and_llm_valid_counts() -> None:
    controller_trace = [
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=1,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "reduce_local_congestion"),
            selected_operator_id="native_sbx_pm",
            metadata={"fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=2,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "reduce_local_congestion"),
            selected_operator_id="reduce_local_congestion",
            metadata={"fallback_used": True},
        ),
        ControllerTraceRow(
            generation_index=0,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "reduce_local_congestion"),
            selected_operator_id="reduce_local_congestion",
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
            operator_id="reduce_local_congestion",
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

    assert summary["reduce_local_congestion"]["selection_count"] == 2
    assert summary["reduce_local_congestion"]["proposal_count"] == 1
    assert summary["reduce_local_congestion"]["fallback_selection_count"] == 1
    assert summary["reduce_local_congestion"]["llm_valid_selection_count"] == 1
    assert summary["reduce_local_congestion"]["recent_fallback_selection_count"] == 1
    assert summary["reduce_local_congestion"]["recent_llm_valid_selection_count"] == 1
    assert summary["native_sbx_pm"]["fallback_selection_count"] == 0


def test_build_controller_state_reports_peak_gradient_budget_and_congestion() -> None:
    parents = _parents()
    history = [
        _record(
            2,
            parents.primary,
            feasible=False,
            peak_temperature=352.4,
            temperature_gradient_rms=12.6,
            c01_temperature_violation=1.3,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=True,
            peak_temperature=347.9,
            temperature_gradient_rms=9.8,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            _vector(sink_start=0.24, sink_end=0.68, x_shift=0.015, y_shift=0.02),
            feasible=True,
            peak_temperature=344.8,
            temperature_gradient_rms=8.7,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    state = build_controller_state(
        parents,
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=9,
        candidate_operator_ids=("native_sbx_pm", "move_hottest_cluster_toward_sink", "repair_sink_budget"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 5,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        history=history,
        recent_window=2,
    )

    run_state = state.metadata["run_state"]
    assert run_state["evaluations_used"] == 8
    assert run_state["evaluations_remaining"] == 12
    assert run_state["feasible_rate"] == pytest.approx(2.0 / 3.0)
    assert run_state["first_feasible_eval"] == 3
    assert run_state["peak_temperature"] == pytest.approx(344.8)
    assert run_state["temperature_gradient_rms"] == pytest.approx(8.7)

    parent_state = state.metadata["parent_state"]
    assert parent_state["parent_indices"] == []
    assert parent_state["parents"][0]["decision_vector"]["c01_x"] == pytest.approx(0.18)
    assert parent_state["parents"][0]["feasible"] is False
    assert parent_state["parents"][0]["total_violation"] == pytest.approx(1.36)
    assert parent_state["parents"][0]["dominant_violation"]["constraint_id"] == "c01_peak_temperature_limit"
    assert parent_state["parents"][1]["feasible"] is True
    assert parent_state["parents"][1]["objective_summary"]["minimize_temperature_gradient_rms"] == pytest.approx(9.8)

    archive_state = state.metadata["archive_state"]
    assert archive_state["best_feasible"]["evaluation_index"] == 4
    assert archive_state["best_near_feasible"]["evaluation_index"] == 2

    domain_regime = state.metadata["domain_regime"]
    assert domain_regime["phase"] == "feasible_refine"
    assert domain_regime["dominant_constraint_family"] == "thermal_limit"
    assert domain_regime["sink_budget_utilization"] == pytest.approx(0.44 / 0.48)
    assert state.metadata["search_phase"] == "feasible_refine"


def test_build_controller_state_emits_phase_aware_prompt_panels() -> None:
    parents = _parents()
    history = [
        _record(
            2,
            parents.primary,
            feasible=False,
            peak_temperature=352.4,
            temperature_gradient_rms=12.6,
            c01_temperature_violation=1.3,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=True,
            peak_temperature=347.9,
            temperature_gradient_rms=9.8,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            _vector(sink_start=0.24, sink_end=0.68, x_shift=0.015, y_shift=0.02),
            feasible=True,
            peak_temperature=344.8,
            temperature_gradient_rms=8.7,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    state = build_controller_state(
        parents,
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=9,
        candidate_operator_ids=("native_sbx_pm", "move_hottest_cluster_toward_sink", "repair_sink_budget"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 5,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        history=history,
        recent_window=2,
    )

    prompt_panels = state.metadata["prompt_panels"]
    assert prompt_panels["run_panel"]["first_feasible_eval"] == 3
    assert prompt_panels["run_panel"]["pareto_size"] == 1
    assert prompt_panels["regime_panel"]["phase"] == "post_feasible_preserve"
    assert prompt_panels["regime_panel"]["dominant_violation_family"] == "thermal_limit"
    assert prompt_panels["parent_panel"]["closest_to_feasible_parent"]["evaluation_index"] == 2
    assert prompt_panels["parent_panel"]["strongest_feasible_parent"]["evaluation_index"] == 3
    assert set(prompt_panels["operator_panel"]) == {
        "native_sbx_pm",
        "move_hottest_cluster_toward_sink",
        "repair_sink_budget",
    }
    assert prompt_panels["operator_panel"]["move_hottest_cluster_toward_sink"]["expected_peak_effect"] == "improve"


def test_operator_summary_exposes_entry_preserve_expand_fit_fields() -> None:
    parents = _parents()
    child_entry = _vector(sink_start=0.2, sink_end=0.64, x_shift=0.005, y_shift=0.01)
    child_expand = _vector(sink_start=0.19, sink_end=0.61, x_shift=0.02, y_shift=0.015)
    history = [
        _record(
            2,
            parents.primary,
            feasible=False,
            peak_temperature=352.4,
            temperature_gradient_rms=12.6,
            c01_temperature_violation=1.3,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=False,
            peak_temperature=349.1,
            temperature_gradient_rms=10.4,
            c01_temperature_violation=0.6,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            child_entry,
            feasible=True,
            peak_temperature=346.0,
            temperature_gradient_rms=9.2,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            5,
            child_expand,
            feasible=True,
            peak_temperature=343.9,
            temperature_gradient_rms=8.5,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=4,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("slide_sink", "local_refine"),
            selected_operator_id="slide_sink",
            metadata={"decision_index": 0, "fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=5,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("slide_sink", "local_refine"),
            selected_operator_id="slide_sink",
            metadata={"decision_index": 1, "fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="slide_sink",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in parents.primary.tolist()),
                tuple(float(value) for value in parents.secondary.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_entry.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=5,
            operator_id="slide_sink",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in child_entry.tolist()),
                tuple(float(value) for value in child_entry.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_expand.tolist()),
            metadata={},
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(child_entry, child_expand),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=9,
        candidate_operator_ids=("slide_sink", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 5,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=2,
    )

    row = state.metadata["prompt_panels"]["operator_panel"]["slide_sink"]
    assert row["entry_fit"] == "trusted"
    assert row["preserve_fit"] == "trusted"
    assert row["expand_fit"] == "trusted"
    assert row["recent_regression_risk"] == "low"
    assert row["frontier_evidence"] == "positive"
    assert row["dominant_violation_relief"] == "supported"


def test_summarize_operator_history_keeps_support_only_speculative_custom_as_weak() -> None:
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=4 + idx,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("slide_sink", "local_refine"),
            selected_operator_id="slide_sink",
            metadata={"decision_index": idx, "fallback_used": False},
        )
        for idx in range(3)
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4 + idx,
            operator_id="slide_sink",
            parent_count=2,
            parent_vectors=((0.2, 0.3, 0.4), (0.25, 0.35, 0.45)),
            proposal_vector=(0.21 + 0.01 * idx, 0.31 + 0.01 * idx, 0.41 + 0.01 * idx),
            metadata={},
        )
        for idx in range(3)
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=3,
    )

    assert summary["slide_sink"]["evidence_level"] == "speculative"
    assert summary["slide_sink"]["preserve_fit"] == "weak"
    assert summary["slide_sink"]["expand_fit"] == "weak"


def test_objective_stagnation_detects_tmax_stagnation() -> None:
    """When T_max is flat across 8 feasible evals but grad_rms improves, temperature_max is stagnant."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    history.append(
        _record(
            10,
            vec,
            feasible=True,
            peak_temperature=310.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        )
    )
    for i in range(11, 19):
        history.append(
            _record(
                i,
                vec,
                feasible=True,
                peak_temperature=310.0,
                temperature_gradient_rms=15.0 - 0.3 * (i - 10),
                c01_temperature_violation=0.0,
                panel_spread_violation=0.0,
            )
        )

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is True
    assert stagnation["temperature_max"]["evaluations_since_improvement"] >= 6
    assert stagnation["gradient_rms"]["stagnant"] is False


def test_objective_stagnation_no_stagnation_when_both_improve() -> None:
    """When both objectives improve recently, neither is stagnant."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    for i in range(10, 18):
        history.append(
            _record(
                i,
                vec,
                feasible=True,
                peak_temperature=310.0 - 0.5 * (i - 10),
                temperature_gradient_rms=15.0 - 0.3 * (i - 10),
                c01_temperature_violation=0.0,
                panel_spread_violation=0.0,
            )
        )

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is False
    assert stagnation["gradient_rms"]["stagnant"] is False


def test_objective_stagnation_empty_when_no_feasible() -> None:
    """Before any feasible solution, objective_stagnation should have no entries."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    for i in range(1, 6):
        history.append(
            _record(
                i,
                vec,
                feasible=False,
                peak_temperature=320.0,
                temperature_gradient_rms=20.0,
                c01_temperature_violation=5.0,
                panel_spread_violation=0.0,
            )
        )

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is False
    assert stagnation["gradient_rms"]["stagnant"] is False


def test_regime_panel_objective_balance_high_pressure() -> None:
    """When T_max stagnant and grad_rms improving, balance_pressure is high with peak_improve."""
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel

    run_state = {
        "first_feasible_eval": 10,
        "evaluations_used": 50,
        "peak_temperature": 307.0,
        "temperature_gradient_rms": 10.0,
    }
    progress_state = {
        "recent_no_progress_count": 0,
        "recent_frontier_stagnation_count": 2,
        "post_feasible_mode": "expand",
        "stable_preservation_streak": 0,
        "new_dominant_violation_family": False,
        "recent_dominant_violation_family": None,
        "recent_dominant_violation_persistence_count": 0,
        "expand_saturation_count": 0,
        "objective_stagnation": {
            "temperature_max": {
                "best_value": 307.0,
                "evaluations_since_improvement": 15,
                "stagnant": True,
            },
            "gradient_rms": {
                "best_value": 10.0,
                "evaluations_since_improvement": 2,
                "stagnant": False,
            },
        },
    }
    archive_state = {
        "recent_feasible_regression_count": 0,
        "recent_feasible_preservation_count": 2,
    }
    domain_regime = {"phase": "feasible_refine"}

    panel = build_prompt_regime_panel(
        run_state=run_state,
        progress_state=progress_state,
        archive_state=archive_state,
        domain_regime=domain_regime,
    )

    balance = panel["objective_balance"]
    assert balance["balance_pressure"] == "high"
    assert balance["preferred_effect"] == "peak_improve"
    assert "temperature_max" in balance["stagnant_objectives"]
    assert "gradient_rms" in balance["improving_objectives"]


def test_regime_panel_objective_balance_low_when_no_stagnation() -> None:
    """When no stagnation, balance_pressure is low."""
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel

    run_state = {
        "first_feasible_eval": 10,
        "evaluations_used": 50,
        "peak_temperature": 307.0,
        "temperature_gradient_rms": 10.0,
    }
    progress_state = {
        "recent_no_progress_count": 0,
        "recent_frontier_stagnation_count": 2,
        "post_feasible_mode": "expand",
        "stable_preservation_streak": 0,
        "new_dominant_violation_family": False,
        "recent_dominant_violation_family": None,
        "recent_dominant_violation_persistence_count": 0,
        "expand_saturation_count": 0,
        "objective_stagnation": {
            "temperature_max": {
                "best_value": 305.0,
                "evaluations_since_improvement": 1,
                "stagnant": False,
            },
            "gradient_rms": {
                "best_value": 10.0,
                "evaluations_since_improvement": 2,
                "stagnant": False,
            },
        },
    }
    archive_state = {
        "recent_feasible_regression_count": 0,
        "recent_feasible_preservation_count": 2,
    }
    domain_regime = {"phase": "feasible_refine"}

    panel = build_prompt_regime_panel(
        run_state=run_state,
        progress_state=progress_state,
        archive_state=archive_state,
        domain_regime=domain_regime,
    )

    balance = panel["objective_balance"]
    assert balance["balance_pressure"] == "low"
    assert balance["preferred_effect"] is None


def test_regime_panel_objective_balance_peak_pressure_when_both_stagnant_but_peak_lags_far_more() -> None:
    """When both objectives are stale but T_max lags much longer, bias back to peak improvement."""
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel

    run_state = {
        "first_feasible_eval": 10,
        "evaluations_used": 181,
        "peak_temperature": 305.4,
        "temperature_gradient_rms": 11.1,
    }
    progress_state = {
        "recent_no_progress_count": 20,
        "recent_frontier_stagnation_count": 8,
        "post_feasible_mode": "expand",
        "stable_preservation_streak": 0,
        "new_dominant_violation_family": False,
        "recent_dominant_violation_family": None,
        "recent_dominant_violation_persistence_count": 0,
        "expand_saturation_count": 0,
        "objective_stagnation": {
            "temperature_max": {
                "best_value": 305.4,
                "evaluations_since_improvement": 73,
                "stagnant": True,
            },
            "gradient_rms": {
                "best_value": 11.1,
                "evaluations_since_improvement": 8,
                "stagnant": True,
            },
        },
    }
    archive_state = {
        "recent_feasible_regression_count": 0,
        "recent_feasible_preservation_count": 4,
    }
    domain_regime = {"phase": "feasible_refine"}

    panel = build_prompt_regime_panel(
        run_state=run_state,
        progress_state=progress_state,
        archive_state=archive_state,
        domain_regime=domain_regime,
    )

    balance = panel["objective_balance"]
    assert balance["balance_pressure"] == "high"
    assert balance["preferred_effect"] == "peak_improve"
    assert balance["stagnant_objectives"] == ["temperature_max"]
    assert balance["improving_objectives"] == ["gradient_rms"]


def test_regime_panel_objective_balance_stays_balanced_when_both_stagnate_similarly() -> None:
    """Keep balanced pressure when both objectives are stale by a similar amount."""
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel

    run_state = {
        "first_feasible_eval": 10,
        "evaluations_used": 161,
        "peak_temperature": 305.4,
        "temperature_gradient_rms": 11.4,
    }
    progress_state = {
        "recent_no_progress_count": 18,
        "recent_frontier_stagnation_count": 7,
        "post_feasible_mode": "expand",
        "stable_preservation_streak": 0,
        "new_dominant_violation_family": False,
        "recent_dominant_violation_family": None,
        "recent_dominant_violation_persistence_count": 0,
        "expand_saturation_count": 0,
        "objective_stagnation": {
            "temperature_max": {
                "best_value": 305.4,
                "evaluations_since_improvement": 53,
                "stagnant": True,
            },
            "gradient_rms": {
                "best_value": 11.4,
                "evaluations_since_improvement": 49,
                "stagnant": True,
            },
        },
    }
    archive_state = {
        "recent_feasible_regression_count": 0,
        "recent_feasible_preservation_count": 4,
    }
    domain_regime = {"phase": "feasible_refine"}

    panel = build_prompt_regime_panel(
        run_state=run_state,
        progress_state=progress_state,
        archive_state=archive_state,
        domain_regime=domain_regime,
    )

    balance = panel["objective_balance"]
    assert balance["balance_pressure"] == "medium"
    assert balance["preferred_effect"] == "balanced"
    assert balance["stagnant_objectives"] == ["temperature_max", "gradient_rms"]
    assert balance["improving_objectives"] == []


def test_applicability_boost_slide_sink_under_peak_improve() -> None:
    """slide_sink applicability should be boosted when objective_balance says peak_improve."""
    from optimizers.operator_pool.state_builder import _build_operator_applicability_row

    summary_row = {
        "entry_fit": "weak",
        "preserve_fit": "weak",
        "expand_fit": "weak",
        "recent_regression_risk": "low",
        "frontier_evidence": "limited",
        "dominant_violation_relief": "supported",
    }
    regime_panel = {
        "phase": "post_feasible_expand",
        "frontier_pressure": "high",
        "preservation_pressure": "medium",
    }

    row_no_boost = _build_operator_applicability_row(
        "slide_sink",
        summary_row=summary_row,
        regime_panel=regime_panel,
    )
    assert row_no_boost["applicability"] == "low"

    objective_balance = {"preferred_effect": "peak_improve", "balance_pressure": "high"}
    row_boosted = _build_operator_applicability_row(
        "slide_sink",
        summary_row=summary_row,
        regime_panel=regime_panel,
        objective_balance=objective_balance,
    )
    assert row_boosted["applicability"] == "medium"


def test_applicability_no_boost_when_balance_low() -> None:
    """No applicability boost when balance_pressure is low."""
    from optimizers.operator_pool.state_builder import _build_operator_applicability_row

    summary_row = {
        "entry_fit": "weak",
        "preserve_fit": "weak",
        "expand_fit": "weak",
        "recent_regression_risk": "low",
        "frontier_evidence": "limited",
        "dominant_violation_relief": "supported",
    }
    regime_panel = {
        "phase": "post_feasible_expand",
        "frontier_pressure": "high",
        "preservation_pressure": "medium",
    }
    objective_balance = {"preferred_effect": None, "balance_pressure": "low"}
    row = _build_operator_applicability_row(
        "slide_sink",
        summary_row=summary_row,
        regime_panel=regime_panel,
        objective_balance=objective_balance,
    )
    assert row["applicability"] == "low"


def test_applicability_caps_weak_speculative_custom_peak_operator_under_balance_pressure() -> None:
    """Weakly evidenced speculative peak operators should not jump straight to high applicability."""
    from optimizers.operator_pool.state_builder import _build_operator_applicability_row

    summary_row = {
        "entry_fit": "weak",
        "preserve_fit": "trusted",
        "expand_fit": "supported",
        "recent_regression_risk": "low",
        "frontier_evidence": "limited",
        "dominant_violation_relief": "none",
    }
    regime_panel = {
        "phase": "post_feasible_expand",
        "frontier_pressure": "high",
        "preservation_pressure": "medium",
    }
    objective_balance = {"preferred_effect": "peak_improve", "balance_pressure": "high"}

    row = _build_operator_applicability_row(
        "slide_sink",
        summary_row=summary_row,
        regime_panel=regime_panel,
        objective_balance=objective_balance,
    )

    assert row["applicability"] == "medium"


def test_prompt_operator_panel_surfaces_unseen_peak_escape_candidates() -> None:
    from optimizers.operator_pool.state_builder import _build_prompt_operator_panel

    operator_summary = {
        "native_sbx_pm": {
            "entry_fit": "weak",
            "preserve_fit": "trusted",
            "expand_fit": "supported",
            "recent_regression_risk": "low",
            "frontier_evidence": "limited",
            "dominant_violation_relief": "none",
        },
        "slide_sink": {
            "entry_fit": "weak",
            "preserve_fit": "supported",
            "expand_fit": "supported",
            "recent_regression_risk": "low",
            "frontier_evidence": "limited",
            "dominant_violation_relief": "none",
            "operator_family": "speculative_custom",
        },
    }
    regime_panel = {
        "phase": "post_feasible_expand",
        "objective_balance": {
            "balance_pressure": "high",
            "preferred_effect": "peak_improve",
        },
    }

    panel = _build_prompt_operator_panel(
        operator_summary=operator_summary,
        candidate_operator_ids=(
            "native_sbx_pm",
            "slide_sink",
            "move_hottest_cluster_toward_sink",
            "repair_sink_budget",
        ),
        regime_panel=regime_panel,
    )

    assert "move_hottest_cluster_toward_sink" in panel
    assert "repair_sink_budget" in panel
    assert panel["move_hottest_cluster_toward_sink"]["applicability"] == "medium"
    assert panel["repair_sink_budget"]["applicability"] == "medium"
