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
