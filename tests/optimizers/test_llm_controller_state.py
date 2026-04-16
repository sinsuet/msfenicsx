from __future__ import annotations

import numpy as np
import pytest

from optimizers.operator_pool.domain_state import build_progress_state, build_prompt_regime_panel
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


def _sink_aligned_compact_vector(*, sink_start: float = 0.18, sink_end: float = 0.72) -> np.ndarray:
    positions = [
        (0.39, 0.18),
        (0.505, 0.18),
        (0.39, 0.295),
        (0.505, 0.295),
        (0.18, 0.18),
        (0.74, 0.18),
        (0.18, 0.34),
        (0.74, 0.34),
        (0.18, 0.50),
        (0.74, 0.50),
        (0.18, 0.66),
        (0.74, 0.66),
        (0.30, 0.50),
        (0.60, 0.50),
        (0.46, 0.66),
    ]
    values: list[float] = []
    for x_value, y_value in positions:
        values.extend([x_value, y_value])
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
    assert "native_sbx_pm" in prompt_panels["operator_panel"]
    assert "move_hottest_cluster_toward_sink" in prompt_panels["operator_panel"]
    assert "repair_sink_budget" in prompt_panels["operator_panel"]
    assert "applicability" in prompt_panels["operator_panel"]["native_sbx_pm"]


def test_build_controller_state_emits_spatial_motif_panel() -> None:
    parents = ParentBundle.from_vectors(
        _vector(sink_start=0.10, sink_end=0.28, x_shift=0.08, y_shift=0.01),
        _vector(sink_start=0.12, sink_end=0.30, x_shift=0.06, y_shift=0.0),
    )
    history = [
        _record(
            2,
            parents.primary,
            feasible=True,
            peak_temperature=347.2,
            temperature_gradient_rms=9.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=True,
            peak_temperature=346.8,
            temperature_gradient_rms=9.5,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    state = build_controller_state(
        parents,
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=7,
        candidate_operator_ids=("slide_sink", "move_hottest_cluster_toward_sink", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 4,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        history=history,
        recent_window=2,
    )

    spatial_panel = state.metadata["prompt_panels"]["spatial_panel"]
    assert spatial_panel["hotspot_to_sink_offset"] > 0.05
    assert spatial_panel["hotspot_inside_sink_window"] is False
    assert spatial_panel["local_congestion_pair"]["component_ids"]
    assert spatial_panel["nearest_neighbor_gap_min"] > 0.0
    assert spatial_panel["sink_budget_bucket"] == "available"


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


def test_build_controller_state_emits_operator_applicability_fields() -> None:
    parents = ParentBundle.from_vectors(
        _vector(sink_start=0.10, sink_end=0.28, x_shift=0.08, y_shift=0.01),
        _vector(sink_start=0.12, sink_end=0.30, x_shift=0.06, y_shift=0.0),
    )
    child = _vector(sink_start=0.18, sink_end=0.36, x_shift=0.065, y_shift=0.01)
    history = [
        _record(
            2,
            parents.primary,
            feasible=True,
            peak_temperature=347.2,
            temperature_gradient_rms=9.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=True,
            peak_temperature=346.8,
            temperature_gradient_rms=9.5,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            child,
            feasible=True,
            peak_temperature=344.9,
            temperature_gradient_rms=8.8,
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
            candidate_operator_ids=("slide_sink", "reduce_local_congestion", "local_refine"),
            selected_operator_id="slide_sink",
            metadata={"decision_index": 0, "fallback_used": False},
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
            proposal_vector=tuple(float(value) for value in child.tolist()),
            metadata={},
        ),
    ]

    state = build_controller_state(
        parents,
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=7,
        candidate_operator_ids=("slide_sink", "reduce_local_congestion", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 4,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=2,
    )

    row = state.metadata["prompt_panels"]["operator_panel"]["slide_sink"]
    assert row["applicability"] == "high"
    assert row["expected_peak_effect"] == "improve"
    assert row["expected_gradient_effect"] in {"improve", "neutral"}
    assert row["expected_feasibility_risk"] in {"low", "medium"}
    assert row["spatial_match_reason"]


def test_reflection_summary_tracks_credit_by_phase_family_and_sink_bucket() -> None:
    parents = ParentBundle.from_vectors(
        _vector(sink_start=0.06, sink_end=0.53, x_shift=0.04, y_shift=0.0),
        _vector(sink_start=0.05, sink_end=0.52, x_shift=0.03, y_shift=0.0),
    )
    child = _vector(sink_start=0.08, sink_end=0.55, x_shift=0.055, y_shift=0.01)
    history = [
        _record(
            2,
            parents.primary,
            feasible=True,
            peak_temperature=347.2,
            temperature_gradient_rms=9.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=True,
            peak_temperature=346.8,
            temperature_gradient_rms=9.6,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            child,
            feasible=True,
            peak_temperature=344.5,
            temperature_gradient_rms=8.8,
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
            metadata={"fallback_used": False},
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
            proposal_vector=tuple(float(value) for value in child.tolist()),
            metadata={},
        ),
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=2,
        history=history,
        design_variable_ids=_S1_VARIABLE_IDS,
        sink_budget_limit=0.48,
    )

    row = summary["slide_sink"]
    assert "credit_by_regime" in row
    assert ("post_feasible_expand", "thermal_limit", "full_sink") in row["credit_by_regime"]


def test_build_controller_state_emits_retrieved_episode_panel() -> None:
    parents = ParentBundle.from_vectors(
        _vector(sink_start=0.07, sink_end=0.54, x_shift=0.05, y_shift=0.0),
        _vector(sink_start=0.08, sink_end=0.55, x_shift=0.045, y_shift=0.0),
    )
    child_expand = _vector(sink_start=0.09, sink_end=0.56, x_shift=0.06, y_shift=0.01)
    child_hold = _vector(sink_start=0.09, sink_end=0.56, x_shift=0.062, y_shift=0.01)
    history = [
        _record(
            2,
            parents.primary,
            feasible=True,
            peak_temperature=347.8,
            temperature_gradient_rms=10.1,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=True,
            peak_temperature=347.1,
            temperature_gradient_rms=9.8,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            child_expand,
            feasible=True,
            peak_temperature=344.9,
            temperature_gradient_rms=8.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            5,
            child_hold,
            feasible=True,
            peak_temperature=345.2,
            temperature_gradient_rms=9.1,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            6,
            _vector(sink_start=0.10, sink_end=0.57, x_shift=0.061, y_shift=0.015),
            feasible=True,
            peak_temperature=345.1,
            temperature_gradient_rms=9.0,
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
            proposal_vector=tuple(float(value) for value in child_expand.tolist()),
            metadata={},
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(child_hold, _vector(sink_start=0.10, sink_end=0.57, x_shift=0.061, y_shift=0.015)),
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=9,
        candidate_operator_ids=("slide_sink", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 6,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=2,
    )

    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    assert retrieval_panel["query_regime"]["phase"] == "post_feasible_expand"
    assert retrieval_panel["matched_episodes"]


def test_build_controller_state_emits_positive_and_negative_retrieval_matches() -> None:
    parents = ParentBundle.from_vectors(
        _vector(sink_start=0.07, sink_end=0.54, x_shift=0.05, y_shift=0.0),
        _vector(sink_start=0.08, sink_end=0.55, x_shift=0.045, y_shift=0.0),
    )
    child_expand = _vector(sink_start=0.09, sink_end=0.56, x_shift=0.06, y_shift=0.01)
    child_hold = _vector(sink_start=0.09, sink_end=0.56, x_shift=0.062, y_shift=0.01)
    child_regress = _vector(sink_start=0.11, sink_end=0.58, x_shift=0.065, y_shift=0.02)
    history = [
        _record(
            2,
            parents.primary,
            feasible=True,
            peak_temperature=347.8,
            temperature_gradient_rms=10.1,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parents.secondary,
            feasible=True,
            peak_temperature=347.1,
            temperature_gradient_rms=9.8,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            child_expand,
            feasible=True,
            peak_temperature=344.9,
            temperature_gradient_rms=8.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            5,
            child_hold,
            feasible=True,
            peak_temperature=345.2,
            temperature_gradient_rms=9.1,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            6,
            _vector(sink_start=0.10, sink_end=0.57, x_shift=0.061, y_shift=0.015),
            feasible=True,
            peak_temperature=345.1,
            temperature_gradient_rms=9.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            7,
            child_regress,
            feasible=False,
            peak_temperature=348.7,
            temperature_gradient_rms=9.7,
            c01_temperature_violation=0.5,
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
            generation_index=2,
            evaluation_index=7,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("slide_sink", "local_refine"),
            selected_operator_id="local_refine",
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
            proposal_vector=tuple(float(value) for value in child_expand.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=2,
            evaluation_index=7,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in child_hold.tolist()),
                tuple(float(value) for value in child_hold.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_regress.tolist()),
            metadata={},
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(child_hold, _vector(sink_start=0.10, sink_end=0.57, x_shift=0.061, y_shift=0.015)),
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=9,
        candidate_operator_ids=("slide_sink", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 6,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=2,
    )

    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    assert retrieval_panel["positive_matches"]
    assert retrieval_panel["negative_matches"]


def test_build_prompt_regime_panel_marks_recover_exit_ready_after_stable_preservation() -> None:
    regime_panel = build_prompt_regime_panel(
        run_state={
            "first_feasible_eval": 45,
        },
        progress_state={
            "post_feasible_mode": "recover",
            "recent_dominant_violation_family": "thermal_limit",
            "recent_dominant_violation_persistence_count": 0,
            "recent_frontier_stagnation_count": 1,
            "stable_preservation_streak": 3,
            "new_dominant_violation_family": False,
        },
        archive_state={
            "recent_feasible_regression_count": 0,
            "recent_feasible_preservation_count": 3,
        },
        domain_regime={
            "phase": "feasible_refine",
            "dominant_constraint_family": "thermal_limit",
            "sink_budget_utilization": 0.9,
        },
    )

    assert regime_panel["recover_exit_ready"] is True


def test_build_progress_state_prefers_expand_when_regressions_do_not_dominate_recent_preservations() -> None:
    history = [
        _record(
            1,
            _vector(sink_start=0.12, sink_end=0.54, x_shift=0.000, y_shift=0.000),
            feasible=True,
            peak_temperature=312.0,
            temperature_gradient_rms=16.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            2,
            _vector(sink_start=0.12, sink_end=0.55, x_shift=0.004, y_shift=0.002),
            feasible=True,
            peak_temperature=309.0,
            temperature_gradient_rms=14.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            _vector(sink_start=0.12, sink_end=0.56, x_shift=0.007, y_shift=0.004),
            feasible=True,
            peak_temperature=308.0,
            temperature_gradient_rms=12.5,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            _vector(sink_start=0.12, sink_end=0.56, x_shift=0.010, y_shift=0.006),
            feasible=False,
            peak_temperature=348.0,
            temperature_gradient_rms=10.0,
            c01_temperature_violation=0.6,
            panel_spread_violation=0.0,
        ),
        _record(
            5,
            _vector(sink_start=0.12, sink_end=0.56, x_shift=0.012, y_shift=0.008),
            feasible=False,
            peak_temperature=347.4,
            temperature_gradient_rms=9.8,
            c01_temperature_violation=0.5,
            panel_spread_violation=0.0,
        ),
        _record(
            6,
            _vector(sink_start=0.12, sink_end=0.56, x_shift=0.014, y_shift=0.010),
            feasible=True,
            peak_temperature=311.5,
            temperature_gradient_rms=15.7,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            7,
            _vector(sink_start=0.12, sink_end=0.56, x_shift=0.016, y_shift=0.012),
            feasible=True,
            peak_temperature=311.2,
            temperature_gradient_rms=15.5,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    progress_state = build_progress_state(history=history)

    assert progress_state["phase"] == "post_feasible_stagnation"
    assert progress_state["post_feasible_mode"] == "expand"
    assert progress_state["recent_frontier_stagnation_count"] >= 2
    assert progress_state["stable_preservation_streak"] == 2


def test_build_progress_state_tracks_new_dominant_violation_family() -> None:
    history = [
        _record(
            1,
            _vector(sink_start=0.12, sink_end=0.54, x_shift=0.000, y_shift=0.000),
            feasible=True,
            peak_temperature=312.0,
            temperature_gradient_rms=16.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            2,
            _vector(sink_start=0.12, sink_end=0.54, x_shift=0.004, y_shift=0.002),
            feasible=False,
            peak_temperature=347.0,
            temperature_gradient_rms=9.8,
            c01_temperature_violation=0.7,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            _vector(sink_start=0.03, sink_end=0.57, x_shift=0.006, y_shift=0.003),
            feasible=False,
            peak_temperature=334.0,
            temperature_gradient_rms=12.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    progress_state = build_progress_state(history=history)

    assert progress_state["recent_dominant_violation_family"] == "sink_budget"
    assert progress_state["new_dominant_violation_family"] is True


def test_build_controller_state_prefers_spread_when_hotspot_is_sink_aligned_in_expand_mode() -> None:
    parent_primary = _sink_aligned_compact_vector()
    parent_secondary = _vector(sink_start=0.20, sink_end=0.68, x_shift=0.01, y_shift=0.01)
    child_expand = _sink_aligned_compact_vector(sink_start=0.19, sink_end=0.71)
    child_hold = _sink_aligned_compact_vector(sink_start=0.19, sink_end=0.71)
    history = [
        _record(
            2,
            parent_primary,
            feasible=True,
            peak_temperature=346.8,
            temperature_gradient_rms=9.6,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parent_secondary,
            feasible=True,
            peak_temperature=346.1,
            temperature_gradient_rms=9.2,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            child_expand,
            feasible=True,
            peak_temperature=344.7,
            temperature_gradient_rms=8.8,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            5,
            child_hold,
            feasible=True,
            peak_temperature=344.9,
            temperature_gradient_rms=8.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            6,
            _sink_aligned_compact_vector(sink_start=0.20, sink_end=0.70),
            feasible=True,
            peak_temperature=345.0,
            temperature_gradient_rms=9.0,
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
            candidate_operator_ids=("spread_hottest_cluster", "move_hottest_cluster_toward_sink", "native_sbx_pm"),
            selected_operator_id="spread_hottest_cluster",
            metadata={"fallback_used": False},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=5,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("spread_hottest_cluster", "move_hottest_cluster_toward_sink", "native_sbx_pm"),
            selected_operator_id="move_hottest_cluster_toward_sink",
            metadata={"fallback_used": False},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="spread_hottest_cluster",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in parent_primary.tolist()),
                tuple(float(value) for value in parent_secondary.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_expand.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=5,
            operator_id="move_hottest_cluster_toward_sink",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in parent_primary.tolist()),
                tuple(float(value) for value in parent_secondary.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_hold.tolist()),
            metadata={},
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(parent_primary, parent_secondary),
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=9,
        candidate_operator_ids=("spread_hottest_cluster", "move_hottest_cluster_toward_sink", "native_sbx_pm"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 6,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=2,
    )

    spatial_panel = state.metadata["prompt_panels"]["spatial_panel"]
    spread_row = state.metadata["prompt_panels"]["operator_panel"]["spread_hottest_cluster"]
    move_row = state.metadata["prompt_panels"]["operator_panel"]["move_hottest_cluster_toward_sink"]

    assert state.metadata["prompt_panels"]["regime_panel"]["phase"] == "post_feasible_expand"
    assert spatial_panel["hotspot_inside_sink_window"] is True
    assert spatial_panel["hottest_cluster_compactness"] < 0.13
    assert spatial_panel["nearest_neighbor_gap_min"] > 0.11
    assert spread_row["applicability"] == "high"
    assert "bounded spread" in spread_row["spatial_match_reason"]
    assert "already sits inside the sink corridor" in move_row["spatial_match_reason"]


def test_build_controller_state_keeps_unseen_semantic_candidates_in_operator_panel() -> None:
    parent_primary = _sink_aligned_compact_vector()
    parent_secondary = _vector(sink_start=0.20, sink_end=0.68, x_shift=0.01, y_shift=0.01)
    history = [
        _record(
            2,
            parent_primary,
            feasible=True,
            peak_temperature=346.8,
            temperature_gradient_rms=9.6,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parent_secondary,
            feasible=True,
            peak_temperature=346.1,
            temperature_gradient_rms=9.2,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            _sink_aligned_compact_vector(sink_start=0.19, sink_end=0.71),
            feasible=True,
            peak_temperature=344.7,
            temperature_gradient_rms=8.8,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            5,
            _sink_aligned_compact_vector(sink_start=0.19, sink_end=0.71),
            feasible=True,
            peak_temperature=344.9,
            temperature_gradient_rms=8.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            6,
            _sink_aligned_compact_vector(sink_start=0.20, sink_end=0.70),
            feasible=True,
            peak_temperature=345.0,
            temperature_gradient_rms=9.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(parent_primary, parent_secondary),
        family="genetic",
        backbone="nsga2",
        generation_index=3,
        evaluation_index=9,
        candidate_operator_ids=("spread_hottest_cluster", "move_hottest_cluster_toward_sink", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 6,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=[],
        operator_trace=[],
        history=history,
        recent_window=2,
    )

    operator_panel = state.metadata["prompt_panels"]["operator_panel"]
    assert state.metadata["prompt_panels"]["regime_panel"]["phase"] == "post_feasible_expand"
    assert "spread_hottest_cluster" in operator_panel
    assert "move_hottest_cluster_toward_sink" in operator_panel
    assert operator_panel["spread_hottest_cluster"]["applicability"] == "high"


def test_build_controller_state_emits_expand_budget_credit_fields() -> None:
    parent_primary = _sink_aligned_compact_vector(sink_start=0.18, sink_end=0.70)
    parent_secondary = _sink_aligned_compact_vector(sink_start=0.20, sink_end=0.68)
    child_regress_1 = _sink_aligned_compact_vector(sink_start=0.19, sink_end=0.69)
    child_regress_2 = _sink_aligned_compact_vector(sink_start=0.19, sink_end=0.69)
    child_frontier = _sink_aligned_compact_vector(sink_start=0.18, sink_end=0.71)
    child_preserve_1 = _sink_aligned_compact_vector(sink_start=0.18, sink_end=0.70)
    child_preserve_2 = _sink_aligned_compact_vector(sink_start=0.18, sink_end=0.69)
    history = [
        _record(
            2,
            parent_primary,
            feasible=True,
            peak_temperature=347.1,
            temperature_gradient_rms=9.6,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            3,
            parent_secondary,
            feasible=True,
            peak_temperature=346.5,
            temperature_gradient_rms=9.3,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            4,
            child_regress_1,
            feasible=False,
            peak_temperature=346.0,
            temperature_gradient_rms=9.1,
            c01_temperature_violation=0.35,
            panel_spread_violation=0.0,
        ),
        _record(
            5,
            child_regress_2,
            feasible=False,
            peak_temperature=345.8,
            temperature_gradient_rms=9.0,
            c01_temperature_violation=0.25,
            panel_spread_violation=0.0,
        ),
        _record(
            6,
            child_frontier,
            feasible=True,
            peak_temperature=344.1,
            temperature_gradient_rms=8.4,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            7,
            child_preserve_1,
            feasible=True,
            peak_temperature=344.6,
            temperature_gradient_rms=8.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            8,
            child_preserve_2,
            feasible=True,
            peak_temperature=344.8,
            temperature_gradient_rms=9.0,
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
            candidate_operator_ids=("spread_hottest_cluster", "smooth_high_gradient_band", "local_refine"),
            selected_operator_id="spread_hottest_cluster",
            phase="post_feasible_expand",
            metadata={"fallback_used": False, "policy_phase": "post_feasible_expand"},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=5,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("spread_hottest_cluster", "smooth_high_gradient_band", "local_refine"),
            selected_operator_id="spread_hottest_cluster",
            phase="post_feasible_expand",
            metadata={"fallback_used": False, "policy_phase": "post_feasible_expand"},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=6,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("spread_hottest_cluster", "smooth_high_gradient_band", "local_refine"),
            selected_operator_id="smooth_high_gradient_band",
            phase="post_feasible_expand",
            metadata={"fallback_used": False, "policy_phase": "post_feasible_expand"},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="spread_hottest_cluster",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in parent_primary.tolist()),
                tuple(float(value) for value in parent_secondary.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_regress_1.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=5,
            operator_id="spread_hottest_cluster",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in parent_primary.tolist()),
                tuple(float(value) for value in parent_secondary.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_regress_2.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=6,
            operator_id="smooth_high_gradient_band",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in parent_primary.tolist()),
                tuple(float(value) for value in parent_secondary.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in child_frontier.tolist()),
            metadata={},
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(parent_primary, parent_secondary),
        family="genetic",
        backbone="nsga2",
        generation_index=4,
        evaluation_index=11,
        candidate_operator_ids=("spread_hottest_cluster", "smooth_high_gradient_band", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 7,
            "total_evaluation_budget": 24,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=3,
    )

    operator_panel = state.metadata["prompt_panels"]["operator_panel"]
    spread_row = operator_panel["spread_hottest_cluster"]
    smooth_row = operator_panel["smooth_high_gradient_band"]

    assert state.metadata["prompt_panels"]["regime_panel"]["phase"] == "post_feasible_expand"
    assert spread_row["recent_expand_preserve_credit"] == 0
    assert spread_row["recent_expand_regression_credit"] == 2
    assert spread_row["recent_expand_frontier_credit"] == 0
    assert spread_row["expand_budget_status"] == "throttled"
    assert smooth_row["recent_expand_preserve_credit"] == 0
    assert smooth_row["recent_expand_regression_credit"] == 0
    assert smooth_row["recent_expand_frontier_credit"] == 1
    assert smooth_row["expand_budget_status"] == "preferred"


def test_build_progress_state_tracks_expand_saturation_count() -> None:
    """After many consecutive evals in expand phase without frontier add, expand_saturation_count rises."""
    history = [
        _record(
            1,
            _vector(sink_start=0.12, sink_end=0.54, x_shift=0.000, y_shift=0.000),
            feasible=True,
            peak_temperature=312.0,
            temperature_gradient_rms=16.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            2,
            _vector(sink_start=0.12, sink_end=0.55, x_shift=0.004, y_shift=0.002),
            feasible=True,
            peak_temperature=309.0,
            temperature_gradient_rms=14.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]
    # Add many feasible preservations that never improve the frontier
    for eval_idx in range(3, 35):
        history.append(
            _record(
                eval_idx,
                _vector(
                    sink_start=0.12,
                    sink_end=0.55,
                    x_shift=0.004 + 0.0001 * eval_idx,
                    y_shift=0.002 + 0.0001 * eval_idx,
                ),
                feasible=True,
                peak_temperature=310.0 + 0.01 * eval_idx,
                temperature_gradient_rms=14.5 + 0.01 * eval_idx,
                c01_temperature_violation=0.0,
                panel_spread_violation=0.0,
            )
        )

    progress_state = build_progress_state(history=history)

    assert "expand_saturation_count" in progress_state
    assert progress_state["expand_saturation_count"] >= 20
    assert progress_state["post_feasible_mode"] == "expand"


def test_objective_stagnation_detects_tmax_stagnation():
    """When T_max is flat across 8 feasible evals but grad_rms improves, temperature_max is stagnant."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    history.append(_record(
        10, vec, feasible=True,
        peak_temperature=310.0, temperature_gradient_rms=15.0,
        c01_temperature_violation=0.0, panel_spread_violation=0.0,
    ))
    for i in range(11, 19):
        history.append(_record(
            i, vec, feasible=True,
            peak_temperature=310.0, temperature_gradient_rms=15.0 - 0.3 * (i - 10),
            c01_temperature_violation=0.0, panel_spread_violation=0.0,
        ))

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is True
    assert stagnation["temperature_max"]["evaluations_since_improvement"] >= 6
    assert stagnation["gradient_rms"]["stagnant"] is False


def test_objective_stagnation_no_stagnation_when_both_improve():
    """When both objectives improve recently, neither is stagnant."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    for i in range(10, 18):
        history.append(_record(
            i, vec, feasible=True,
            peak_temperature=310.0 - 0.5 * (i - 10),
            temperature_gradient_rms=15.0 - 0.3 * (i - 10),
            c01_temperature_violation=0.0, panel_spread_violation=0.0,
        ))

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is False
    assert stagnation["gradient_rms"]["stagnant"] is False


def test_objective_stagnation_empty_when_no_feasible():
    """Before any feasible solution, objective_stagnation should have no stagnant entries."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    for i in range(1, 6):
        history.append(_record(
            i, vec, feasible=False,
            peak_temperature=320.0, temperature_gradient_rms=20.0,
            c01_temperature_violation=5.0, panel_spread_violation=0.0,
        ))

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is False
    assert stagnation["gradient_rms"]["stagnant"] is False
