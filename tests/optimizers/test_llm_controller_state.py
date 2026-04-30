from __future__ import annotations

import numpy as np
import pytest

from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.policy_kernel import PolicySnapshot
from optimizers.operator_pool.prompt_projection import build_prompt_projection
from optimizers.operator_pool.reflection import summarize_operator_history
from optimizers.operator_pool.state import ControllerState
from optimizers.operator_pool.state_builder import build_controller_state, _build_prompt_semantic_task_panel
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow
from optimizers.operator_pool.domain_state import build_prompt_regime_panel


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


def _penalty_record(
    evaluation_index: int,
    vector: np.ndarray,
    *,
    radiator_span_violation: float = 0.0,
    failure_reason: str = "cheap_constraint_violation",
) -> dict[str, object]:
    decision_vector = {
        variable_id: float(value)
        for variable_id, value in zip(_S1_VARIABLE_IDS, vector.tolist(), strict=True)
    }
    return {
        "evaluation_index": evaluation_index,
        "source": "optimizer",
        "feasible": False,
        "decision_vector": decision_vector,
        "objective_values": {
            "minimize_peak_temperature": 1.0e12,
            "minimize_temperature_gradient_rms": 1.0e12,
        },
        "constraint_values": {
            "radiator_span_budget": float(radiator_span_violation),
            "c01_peak_temperature_limit": 1.0e12,
            "panel_temperature_spread_limit": 1.0e12,
        },
        "evaluation_report": {},
        "failure_reason": failure_reason,
        "solver_skipped": True,
    }


def _build_phase_alignment_state(*, policy_phase: str) -> ControllerState:
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel
    from optimizers.operator_pool.state_builder import _build_retrieval_panel

    run_state = {
        "first_feasible_eval": 46,
        "evaluations_used": 82,
        "peak_temperature": 323.0,
        "temperature_gradient_rms": 14.8,
    }
    progress_state = {
        "phase": "post_feasible_progress",
        "first_feasible_found": True,
        "post_feasible_mode": "recover" if policy_phase == "post_feasible_recover" else "preserve",
        "recent_no_progress_count": 0,
        "recent_frontier_stagnation_count": 2,
        "stable_preservation_streak": 1,
        "new_dominant_violation_family": True,
        "recent_dominant_violation_family": "thermal_limit",
        "recent_dominant_violation_persistence_count": 2,
        "expand_saturation_count": 0,
        "objective_stagnation": {
            "temperature_max": {
                "best_value": 323.0,
                "evaluations_since_improvement": 3,
                "stagnant": False,
            },
            "gradient_rms": {
                "best_value": 14.8,
                "evaluations_since_improvement": 8,
                "stagnant": True,
            },
        },
    }
    archive_state = {
        "recent_feasible_regression_count": 1,
        "recent_feasible_preservation_count": 0,
    }
    domain_regime = {
        "phase": "feasible_refine",
        "dominant_constraint_family": "thermal_limit",
        "sink_budget_utilization": 0.91,
    }
    regime_panel = build_prompt_regime_panel(
        run_state=run_state,
        progress_state=progress_state,
        archive_state=archive_state,
        domain_regime=domain_regime,
    )
    retrieval_panel = _build_retrieval_panel(
        operator_summary={
            "local_refine": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 1,
                        "feasible_regression_count": 0,
                        "penalty_event_count": 0,
                        "avg_objective_delta": -0.05,
                        "avg_total_violation_delta": 0.0,
                    }
                }
            }
        },
        candidate_operator_ids=("local_refine",),
        regime_panel=regime_panel,
        spatial_panel={"sink_budget_bucket": "tight"},
    )
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=83,
        parent_count=2,
        vector_size=32,
        metadata={
            "candidate_operator_ids": ["local_refine"],
            "run_state": run_state,
            "progress_state": progress_state,
            "prompt_panels": {
                "regime_panel": regime_panel,
                "retrieval_panel": retrieval_panel,
            },
        },
    )


def _build_phase_alignment_snapshot(phase: str) -> PolicySnapshot:
    return PolicySnapshot(
        phase=phase,
        allowed_operator_ids=("local_refine",),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=(),
        candidate_annotations={"local_refine": {"operator_family": "local_refine"}},
    )


def test_prompt_regime_promotes_peak_budget_fill_when_collapsed_frontier_has_sink_headroom() -> None:
    panel = build_prompt_regime_panel(
        run_state={
            "first_feasible_eval": 9,
            "sink_budget_utilization": 0.965,
            "objective_extremes": {
                "min_peak_temperature": {
                    "evaluation_index": 102,
                    "sink_span": 0.3088,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.99,
                        "minimize_temperature_gradient_rms": 15.61,
                    },
                },
                "min_temperature_gradient_rms": {
                    "evaluation_index": 102,
                    "sink_span": 0.3088,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.99,
                        "minimize_temperature_gradient_rms": 15.61,
                    },
                },
            },
        },
        progress_state={
            "phase": "post_feasible_stagnation",
            "post_feasible_mode": "expand",
            "recent_frontier_stagnation_count": 8,
            "diversity_deficit_level": "high",
            "objective_stagnation": {
                "temperature_max": {
                    "best_value": 319.99,
                    "evaluations_since_improvement": 12,
                    "stagnant": True,
                },
                "gradient_rms": {
                    "best_value": 15.61,
                    "evaluations_since_improvement": 12,
                    "stagnant": True,
                },
            },
        },
        archive_state={
            "pareto_size": 1,
            "recent_feasible_regression_count": 0,
        },
        domain_regime={
            "phase": "feasible_refine",
            "sink_budget_utilization": 0.965,
        },
    )

    assert panel["objective_balance"]["preferred_effect"] == "peak_improve"
    assert panel["objective_balance"]["balance_pressure"] == "high"
    assert panel["objective_balance"]["balance_reason"] == "frontier_endpoint_peak_budget_fill"


def test_prompt_regime_keeps_balanced_when_collapsed_frontier_has_full_sink_budget() -> None:
    panel = build_prompt_regime_panel(
        run_state={
            "first_feasible_eval": 9,
            "sink_budget_utilization": 1.0,
            "objective_extremes": {
                "min_peak_temperature": {
                    "evaluation_index": 153,
                    "sink_span": 0.32,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.63,
                        "minimize_temperature_gradient_rms": 15.46,
                    },
                },
                "min_temperature_gradient_rms": {
                    "evaluation_index": 153,
                    "sink_span": 0.32,
                    "objective_summary": {
                        "minimize_peak_temperature": 319.63,
                        "minimize_temperature_gradient_rms": 15.46,
                    },
                },
            },
        },
        progress_state={
            "phase": "post_feasible_stagnation",
            "post_feasible_mode": "expand",
            "recent_frontier_stagnation_count": 8,
            "diversity_deficit_level": "high",
            "objective_stagnation": {
                "temperature_max": {
                    "best_value": 319.63,
                    "evaluations_since_improvement": 12,
                    "stagnant": True,
                },
                "gradient_rms": {
                    "best_value": 15.46,
                    "evaluations_since_improvement": 12,
                    "stagnant": True,
                },
            },
        },
        archive_state={
            "pareto_size": 1,
            "recent_feasible_regression_count": 0,
        },
        domain_regime={
            "phase": "feasible_refine",
            "sink_budget_utilization": 1.0,
        },
    )

    assert panel["objective_balance"]["preferred_effect"] == "balanced"
    assert panel["objective_balance"]["balance_pressure"] == "medium"
    assert "balance_reason" not in panel["objective_balance"]


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


def test_build_controller_state_exposes_pareto_objective_extremes_in_run_panel() -> None:
    history = [
        _record(
            1,
            _vector(sink_start=0.22, sink_end=0.54),
            feasible=True,
            peak_temperature=319.65,
            temperature_gradient_rms=16.15,
            c01_temperature_violation=-1.0,
            panel_spread_violation=-1.0,
        ),
        _record(
            2,
            _vector(sink_start=0.24, sink_end=0.56, x_shift=0.02),
            feasible=True,
            peak_temperature=321.02,
            temperature_gradient_rms=15.92,
            c01_temperature_violation=-1.0,
            panel_spread_violation=-1.0,
        ),
        _record(
            3,
            _vector(sink_start=0.20, sink_end=0.52, y_shift=0.02),
            feasible=True,
            peak_temperature=320.57,
            temperature_gradient_rms=16.03,
            c01_temperature_violation=-1.0,
            panel_spread_violation=-1.0,
        ),
    ]

    state = build_controller_state(
        _parents(),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=4,
        candidate_operator_ids=("vector_sbx_pm", "component_jitter_1"),
        metadata={
            "design_variable_ids": _S1_VARIABLE_IDS,
            "radiator_span_max": 0.48,
            "total_evaluation_budget": 200,
        },
        history=history,
    )

    run_panel = state.metadata["prompt_panels"]["run_panel"]
    extremes = run_panel["objective_extremes"]

    assert extremes["min_peak_temperature"]["evaluation_index"] == 1
    assert extremes["min_temperature_gradient_rms"]["evaluation_index"] == 2
    assert extremes["min_peak_temperature"]["objective_summary"][
        "minimize_peak_temperature"
    ] == pytest.approx(319.65)
    assert extremes["min_temperature_gradient_rms"]["objective_summary"][
        "minimize_temperature_gradient_rms"
    ] == pytest.approx(15.92)


def test_retrieval_query_phase_uses_recover_when_policy_phase_is_recover() -> None:
    state = _build_phase_alignment_state(policy_phase="post_feasible_recover")

    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]

    assert retrieval_panel["query_regime"]["phase"] == "post_feasible_recover"


def test_prompt_projection_does_not_silently_disagree_with_retrieval_phase() -> None:
    state = _build_phase_alignment_state(policy_phase="post_feasible_recover")

    metadata = build_prompt_projection(
        state,
        candidate_operator_ids=state.metadata["candidate_operator_ids"],
        original_candidate_operator_ids=state.metadata["candidate_operator_ids"],
        policy_snapshot=_build_phase_alignment_snapshot("post_feasible_recover"),
        guardrail=None,
    )

    assert (
        metadata["prompt_panels"]["regime_panel"]["phase"]
        == metadata["prompt_panels"]["retrieval_panel"]["query_regime"]["phase"]
    )


def test_retrieval_query_phase_keeps_prefeasible_convert_explicit() -> None:
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel
    from optimizers.operator_pool.state_builder import _build_retrieval_panel

    regime_panel = build_prompt_regime_panel(
        run_state={
            "first_feasible_eval": None,
            "evaluations_used": 32,
            "peak_temperature": 348.0,
            "temperature_gradient_rms": 11.3,
        },
        progress_state={
            "phase": "prefeasible_progress",
            "first_feasible_found": False,
            "prefeasible_mode": "convert",
            "recent_no_progress_count": 4,
            "evaluations_since_near_feasible_improvement": 4,
            "recent_dominant_violation_family": "thermal_limit",
            "recent_dominant_violation_persistence_count": 3,
        },
        archive_state={
            "recent_feasible_regression_count": 0,
            "recent_feasible_preservation_count": 0,
        },
        domain_regime={
            "phase": "near_feasible",
            "dominant_constraint_family": "thermal_limit",
            "sink_budget_utilization": 0.98,
        },
    )

    retrieval_panel = _build_retrieval_panel(
        operator_summary={},
        candidate_operator_ids=("repair_sink_budget",),
        regime_panel=regime_panel,
        spatial_panel={"sink_budget_bucket": "full_sink"},
    )

    assert retrieval_panel["query_regime"]["phase"] == "prefeasible_convert"
    assert retrieval_panel["query_regime"]["phase_fallbacks"] == ["prefeasible_search"]


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
    assert state.metadata["generation_local_memory"]["route_family_counts"] == {
        "sink_retarget": {"accepted_count": 2, "accepted_share": 1.0}
    }
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


def test_build_controller_state_emits_semantic_task_panel() -> None:
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
        candidate_operator_ids=("vector_sbx_pm", "sink_shift", "sink_resize", "component_block_translate_2_4"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 5,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=[
            ControllerTraceRow(
                generation_index=1,
                evaluation_index=5,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("sink_shift", "component_subspace_sbx"),
                selected_operator_id="sink_shift",
                metadata={"decision_index": 1, "fallback_used": False, "policy_phase": "post_feasible_expand"},
            ),
            ControllerTraceRow(
                generation_index=1,
                evaluation_index=6,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("sink_shift", "component_subspace_sbx"),
                selected_operator_id="component_subspace_sbx",
                metadata={"decision_index": 2, "fallback_used": False, "policy_phase": "post_feasible_expand"},
            ),
        ],
        history=history,
        recent_window=2,
    )

    semantic_task_panel = state.metadata["prompt_panels"]["semantic_task_panel"]
    assert semantic_task_panel["active_bottleneck"] == "balanced_portfolio"
    assert semantic_task_panel["stage_focus"] == "post_feasible_preserve"
    assert semantic_task_panel["recommended_task_order"][:2] == ["baseline_reset", "sink_budget_shape"]
    assert semantic_task_panel["task_operator_candidates"]["sink_budget_shape"] == ["sink_resize"]
    assert semantic_task_panel["task_operator_candidates"]["baseline_reset"] == ["vector_sbx_pm"]


def test_post_feasible_expand_semantic_panel_keeps_sink_stabilizer_before_gate() -> None:
    semantic_task_panel = _build_prompt_semantic_task_panel(
        candidate_operator_ids=(
            "vector_sbx_pm",
            "sink_resize",
            "component_block_translate_2_4",
            "component_jitter_1",
        ),
        regime_panel={
            "phase": "post_feasible_expand",
            "dominant_violation_family": "thermal_limit",
            "frontier_pressure": "high",
            "preservation_pressure": "medium",
            "run_feasible_rate": 0.42,
            "recent_frontier_stagnation_count": 4,
        },
        spatial_panel={
            "sink_budget_bucket": "full_sink",
            "hotspot_inside_sink_window": True,
            "nearest_neighbor_gap_min": 0.08,
        },
        recent_decisions=(
            {"selected_operator_id": "sink_resize"},
            {"selected_operator_id": "component_jitter_1"},
            {"selected_operator_id": "component_block_translate_2_4"},
            {"selected_operator_id": "sink_resize"},
        ),
    )

    assert semantic_task_panel["stage_focus"] == "post_feasible_expand"
    assert semantic_task_panel["active_bottleneck"] != "sink_budget_pressure"
    assert semantic_task_panel["recommended_task_order"][:4] == [
        "semantic_block_move",
        "local_polish",
        "sink_budget_shape",
        "baseline_reset",
    ]


def test_post_feasible_expand_semantic_panel_prioritizes_exploitation_after_sink_gate() -> None:
    semantic_task_panel = _build_prompt_semantic_task_panel(
        candidate_operator_ids=(
            "vector_sbx_pm",
            "sink_resize",
            "component_block_translate_2_4",
            "component_jitter_1",
        ),
        regime_panel={
            "phase": "post_feasible_expand",
            "dominant_violation_family": "thermal_limit",
            "frontier_pressure": "high",
            "preservation_pressure": "medium",
            "run_feasible_rate": 0.56,
            "recent_frontier_stagnation_count": 8,
        },
        spatial_panel={
            "sink_budget_bucket": "full_sink",
            "hotspot_inside_sink_window": True,
            "nearest_neighbor_gap_min": 0.08,
        },
        recent_decisions=(
            {"selected_operator_id": "component_jitter_1"},
            {"selected_operator_id": "component_block_translate_2_4"},
            {"selected_operator_id": "component_jitter_1"},
            {"selected_operator_id": "component_block_translate_2_4"},
        ),
    )

    assert semantic_task_panel["stage_focus"] == "post_feasible_expand"
    assert semantic_task_panel["active_bottleneck"] != "sink_budget_pressure"
    assert semantic_task_panel["recommended_task_order"][:2] == ["semantic_block_move", "local_polish"]
    assert semantic_task_panel["recommended_task_order"].index("sink_budget_shape") > semantic_task_panel[
        "recommended_task_order"
    ].index("local_polish")


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


def test_summarize_operator_history_excludes_penalty_coded_prefeasible_transitions_from_entry_credit() -> None:
    base_parent = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.0, y_shift=0.0)
    penalty_child = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.02, y_shift=0.02)
    recovered_child = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.01, y_shift=0.01)
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("local_refine",),
            selected_operator_id="local_refine",
            metadata={"decision_index": 0, "fallback_used": False, "policy_phase": "prefeasible_convert"},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=4,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("local_refine",),
            selected_operator_id="local_refine",
            metadata={"decision_index": 1, "fallback_used": False, "policy_phase": "prefeasible_convert"},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=3,
            operator_id="local_refine",
            parent_count=1,
            parent_vectors=(tuple(float(value) for value in base_parent.tolist()),),
            proposal_vector=tuple(float(value) for value in penalty_child.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in penalty_child.tolist()),
                tuple(float(value) for value in base_parent.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in recovered_child.tolist()),
            metadata={},
        ),
    ]
    history = [
        _record(
            2,
            base_parent,
            feasible=False,
            peak_temperature=330.0,
            temperature_gradient_rms=16.0,
            c01_temperature_violation=0.8,
            panel_spread_violation=0.0,
        ),
        _penalty_record(3, penalty_child),
        _record(
            4,
            recovered_child,
            feasible=False,
            peak_temperature=327.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.4,
            panel_spread_violation=0.0,
        ),
    ]

    summary = summarize_operator_history(
        controller_trace,
        operator_trace,
        recent_window=4,
        history=history,
        design_variable_ids=list(_S1_VARIABLE_IDS),
        sink_budget_limit=0.48,
    )

    row = summary["local_refine"]
    assert row["near_feasible_improvement_count"] == 0
    assert row["dominant_violation_relief_count"] == 0
    assert row["avg_total_violation_delta"] == pytest.approx(0.0)
    credit = row["credit_by_regime"][("prefeasible_convert", "thermal_limit", "full_sink")]
    assert credit["avg_total_violation_delta"] == pytest.approx(0.0)
    assert credit["penalty_event_count"] == 2


def test_build_controller_state_retrieval_panel_exposes_penalty_count_without_huge_prefeasible_delta() -> None:
    base_parent = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.0, y_shift=0.0)
    penalty_child = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.02, y_shift=0.02)
    recovered_child = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.01, y_shift=0.01)
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"decision_index": 0, "fallback_used": False, "policy_phase": "prefeasible_convert"},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=4,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"decision_index": 1, "fallback_used": False, "policy_phase": "prefeasible_convert"},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=3,
            operator_id="local_refine",
            parent_count=1,
            parent_vectors=(tuple(float(value) for value in base_parent.tolist()),),
            proposal_vector=tuple(float(value) for value in penalty_child.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="local_refine",
            parent_count=2,
            parent_vectors=(
                tuple(float(value) for value in penalty_child.tolist()),
                tuple(float(value) for value in base_parent.tolist()),
            ),
            proposal_vector=tuple(float(value) for value in recovered_child.tolist()),
            metadata={},
        ),
    ]
    history = [
        _record(
            2,
            base_parent,
            feasible=False,
            peak_temperature=330.0,
            temperature_gradient_rms=16.0,
            c01_temperature_violation=0.8,
            panel_spread_violation=0.0,
        ),
        _penalty_record(3, penalty_child),
        _record(
            4,
            recovered_child,
            feasible=False,
            peak_temperature=327.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.4,
            panel_spread_violation=0.0,
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(recovered_child, base_parent),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=5,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 2,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=4,
    )

    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    matched = retrieval_panel["matched_episodes"][0]
    assert matched["route_family"] == "stable_local"
    assert matched["evidence"]["avg_total_violation_delta"] == pytest.approx(0.0)
    assert matched["evidence"]["penalty_event_count"] == 2
    assert all(match["evidence"]["penalty_event_count"] == 0 for match in retrieval_panel["positive_matches"])
    assert retrieval_panel["negative_matches"][0]["evidence"]["penalty_event_count"] == 2


def test_build_controller_state_penalty_mixed_credit_stays_out_of_positive_retrieval_matches() -> None:
    base_parent = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.0, y_shift=0.0)
    penalty_child = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.02, y_shift=0.02)
    improved_child = _vector(sink_start=0.22, sink_end=0.70, x_shift=0.01, y_shift=0.01)
    controller_trace = [
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=3,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"decision_index": 0, "fallback_used": False, "policy_phase": "prefeasible_convert"},
        ),
        ControllerTraceRow(
            generation_index=1,
            evaluation_index=4,
            family="genetic",
            backbone="nsga2",
            controller_id="llm",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
            selected_operator_id="local_refine",
            metadata={"decision_index": 1, "fallback_used": False, "policy_phase": "prefeasible_convert"},
        ),
    ]
    operator_trace = [
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=3,
            operator_id="local_refine",
            parent_count=1,
            parent_vectors=(tuple(float(value) for value in base_parent.tolist()),),
            proposal_vector=tuple(float(value) for value in penalty_child.tolist()),
            metadata={},
        ),
        OperatorTraceRow(
            generation_index=1,
            evaluation_index=4,
            operator_id="local_refine",
            parent_count=1,
            parent_vectors=(tuple(float(value) for value in base_parent.tolist()),),
            proposal_vector=tuple(float(value) for value in improved_child.tolist()),
            metadata={},
        ),
    ]
    history = [
        _record(
            2,
            base_parent,
            feasible=False,
            peak_temperature=330.0,
            temperature_gradient_rms=16.0,
            c01_temperature_violation=0.8,
            panel_spread_violation=0.0,
        ),
        _penalty_record(3, penalty_child),
        _record(
            4,
            improved_child,
            feasible=False,
            peak_temperature=327.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.3,
            panel_spread_violation=0.0,
        ),
    ]

    state = build_controller_state(
        ParentBundle.from_vectors(improved_child, base_parent),
        family="genetic",
        backbone="nsga2",
        generation_index=2,
        evaluation_index=5,
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        metadata={
            "design_variable_ids": list(_S1_VARIABLE_IDS),
            "decision_index": 2,
            "total_evaluation_budget": 20,
            "radiator_span_max": 0.48,
        },
        controller_trace=controller_trace,
        operator_trace=operator_trace,
        history=history,
        recent_window=4,
    )

    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    matched = retrieval_panel["matched_episodes"][0]
    assert matched["evidence"]["avg_total_violation_delta"] < 0.0
    assert matched["evidence"]["penalty_event_count"] == 1
    assert all(match["evidence"]["penalty_event_count"] == 0 for match in retrieval_panel["positive_matches"])
    assert retrieval_panel["negative_matches"][0]["evidence"]["penalty_event_count"] == 1


def test_retrieval_panel_surfaces_route_family_credit_by_regime() -> None:
    from optimizers.operator_pool.state_builder import _build_retrieval_panel

    retrieval_panel = _build_retrieval_panel(
        operator_summary={
            "repair_sink_budget": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 1,
                        "feasible_regression_count": 0,
                        "penalty_event_count": 0,
                        "avg_objective_delta": -0.05,
                        "avg_total_violation_delta": 0.0,
                    }
                }
            },
            "slide_sink": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 0,
                        "feasible_regression_count": 1,
                        "penalty_event_count": 0,
                        "avg_objective_delta": 0.07,
                        "avg_total_violation_delta": 0.0,
                    }
                }
            },
        },
        candidate_operator_ids=("repair_sink_budget", "slide_sink"),
        regime_panel={
            "phase": "post_feasible_recover",
            "dominant_violation_family": "thermal_limit",
        },
        spatial_panel={"sink_budget_bucket": "tight"},
    )

    assert retrieval_panel["route_family_credit"] == {
        "positive_families": ["budget_guard"],
        "negative_families": ["sink_retarget"],
        "handoff_families": [],
    }


def test_retrieval_panel_marks_stable_local_handoff_window() -> None:
    from optimizers.operator_pool.state_builder import _build_retrieval_panel

    retrieval_panel = _build_retrieval_panel(
        operator_summary={
            "local_refine": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 1,
                        "feasible_regression_count": 1,
                        "penalty_event_count": 0,
                        "avg_objective_delta": -0.02,
                        "avg_total_violation_delta": 0.0,
                    }
                }
            }
        },
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        regime_panel={
            "phase": "post_feasible_recover",
            "dominant_violation_family": "thermal_limit",
        },
        spatial_panel={"sink_budget_bucket": "tight"},
    )

    assert retrieval_panel["route_family_credit"] == {
        "positive_families": ["stable_local"],
        "negative_families": ["stable_local"],
        "handoff_families": ["stable_local"],
    }
    assert retrieval_panel["stable_local_handoff_active"] is True


def test_retrieval_panel_keeps_stable_local_handoff_when_only_fallback_episode_is_positive() -> None:
    from optimizers.operator_pool.state_builder import _build_retrieval_panel

    retrieval_panel = _build_retrieval_panel(
        operator_summary={
            "native_sbx_pm": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 0,
                        "feasible_regression_count": 1,
                        "penalty_event_count": 0,
                        "avg_objective_delta": 0.08,
                        "avg_total_violation_delta": 0.12,
                    }
                }
            },
            "local_refine": {
                "credit_by_regime": {
                    ("post_feasible_preserve", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 0,
                        "feasible_regression_count": 0,
                        "penalty_event_count": 0,
                        "avg_objective_delta": 0.0,
                        "avg_total_violation_delta": -0.05,
                    }
                }
            },
        },
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        regime_panel={
            "phase": "post_feasible_recover",
            "dominant_violation_family": "thermal_limit",
        },
        spatial_panel={"sink_budget_bucket": "tight"},
    )

    assert retrieval_panel["positive_matches"][0]["route_family"] == "stable_local"
    assert retrieval_panel["route_family_credit"] == {
        "positive_families": [],
        "negative_families": ["stable_local"],
        "handoff_families": ["stable_local"],
    }
    assert retrieval_panel["stable_local_handoff_active"] is True


def test_retrieval_panel_exposes_visibility_floor_from_positive_matches_even_when_family_credit_is_mixed() -> None:
    from optimizers.operator_pool.state_builder import _build_retrieval_panel

    retrieval_panel = _build_retrieval_panel(
        operator_summary={
            "native_sbx_pm": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 0,
                        "feasible_regression_count": 1,
                        "penalty_event_count": 0,
                        "avg_objective_delta": 0.05,
                        "avg_total_violation_delta": 0.02,
                    }
                }
            },
            "local_refine": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 1,
                        "feasible_regression_count": 1,
                        "penalty_event_count": 0,
                        "avg_objective_delta": -0.01,
                        "avg_total_violation_delta": -0.03,
                    }
                }
            },
        },
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        regime_panel={
            "phase": "post_feasible_recover",
            "dominant_violation_family": "thermal_limit",
        },
        spatial_panel={"sink_budget_bucket": "tight"},
    )

    assert retrieval_panel["positive_match_families"] == ["stable_local"]
    assert retrieval_panel["visibility_floor_families"] == ["stable_local"]


def test_build_progress_state_uses_recent_violation_pressure_not_any_historical_family_switch() -> None:
    from optimizers.operator_pool.domain_state import build_progress_state

    history = [
        _record(
            40,
            _vector(),
            feasible=True,
            peak_temperature=320.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            41,
            _vector(sink_start=0.10, sink_end=0.70),
            feasible=False,
            peak_temperature=321.0,
            temperature_gradient_rms=15.3,
            c01_temperature_violation=0.05,
            panel_spread_violation=0.0,
        ),
        _record(
            42,
            _vector(),
            feasible=False,
            peak_temperature=320.8,
            temperature_gradient_rms=15.2,
            c01_temperature_violation=0.3,
            panel_spread_violation=0.0,
        ),
        _record(
            43,
            _vector(),
            feasible=True,
            peak_temperature=320.1,
            temperature_gradient_rms=15.1,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            44,
            _vector(),
            feasible=True,
            peak_temperature=320.2,
            temperature_gradient_rms=15.2,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            45,
            _vector(),
            feasible=True,
            peak_temperature=319.5,
            temperature_gradient_rms=14.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    progress = build_progress_state(history=history)

    assert progress["recent_violation_family_switch_count"] == 0
    assert progress["recover_pressure_level"] == "low"
    assert progress["recover_exit_ready"] is True
    assert progress["post_feasible_mode"] == "preserve"


def test_build_progress_state_tracks_preserve_dwell_after_recover_cools() -> None:
    from optimizers.operator_pool.domain_state import build_progress_state

    history = [
        _record(
            40,
            _vector(),
            feasible=True,
            peak_temperature=320.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            41,
            _vector(sink_start=0.12, sink_end=0.68),
            feasible=False,
            peak_temperature=321.2,
            temperature_gradient_rms=15.4,
            c01_temperature_violation=0.08,
            panel_spread_violation=0.0,
        ),
        _record(
            42,
            _vector(),
            feasible=True,
            peak_temperature=319.9,
            temperature_gradient_rms=14.9,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    progress = build_progress_state(history=history)

    assert progress["post_feasible_mode"] == "preserve"
    assert progress["preserve_dwell_count"] == 1
    assert progress["preserve_dwell_remaining"] == 2


def test_build_progress_state_keeps_preserve_dwell_live_across_one_regression() -> None:
    from optimizers.operator_pool.domain_state import build_progress_state

    history = [
        _record(
            40,
            _vector(),
            feasible=True,
            peak_temperature=320.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            41,
            _vector(sink_start=0.12, sink_end=0.68),
            feasible=False,
            peak_temperature=321.3,
            temperature_gradient_rms=15.5,
            c01_temperature_violation=0.08,
            panel_spread_violation=0.0,
        ),
        _record(
            42,
            _vector(),
            feasible=True,
            peak_temperature=320.1,
            temperature_gradient_rms=15.1,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            43,
            _vector(sink_start=0.10, sink_end=0.66),
            feasible=False,
            peak_temperature=321.0,
            temperature_gradient_rms=15.4,
            c01_temperature_violation=0.05,
            panel_spread_violation=0.0,
        ),
    ]

    progress = build_progress_state(history=history)

    assert progress["recover_pressure_level"] == "medium"
    assert progress["post_feasible_mode"] == "preserve"
    assert progress["preserve_dwell_count"] == 1
    assert progress["preserve_dwell_remaining"] == 2


def test_build_progress_state_sets_recover_release_ready_when_preserve_signal_offsets_bounded_regression() -> None:
    from optimizers.operator_pool.domain_state import build_progress_state

    history = [
        _record(
            40,
            _vector(),
            feasible=True,
            peak_temperature=320.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            41,
            _vector(sink_start=0.12, sink_end=0.68),
            feasible=False,
            peak_temperature=321.3,
            temperature_gradient_rms=15.5,
            c01_temperature_violation=0.08,
            panel_spread_violation=0.0,
        ),
        _record(
            42,
            _vector(),
            feasible=True,
            peak_temperature=320.1,
            temperature_gradient_rms=15.1,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            43,
            _vector(sink_start=0.10, sink_end=0.66),
            feasible=False,
            peak_temperature=321.0,
            temperature_gradient_rms=15.4,
            c01_temperature_violation=0.05,
            panel_spread_violation=0.0,
        ),
    ]

    progress = build_progress_state(history=history)

    assert progress["recover_pressure_level"] == "medium"
    assert progress["recover_release_ready"] is True


def test_build_progress_state_sets_diversity_deficit_medium_for_two_point_stagnant_front() -> None:
    from optimizers.operator_pool.domain_state import build_progress_state

    history = [
        _record(
            40,
            _vector(),
            feasible=True,
            peak_temperature=320.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            41,
            _vector(x_shift=0.01),
            feasible=True,
            peak_temperature=319.8,
            temperature_gradient_rms=15.2,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            42,
            _vector(x_shift=0.02),
            feasible=True,
            peak_temperature=320.1,
            temperature_gradient_rms=15.3,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            43,
            _vector(x_shift=0.03),
            feasible=True,
            peak_temperature=320.2,
            temperature_gradient_rms=15.4,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            44,
            _vector(x_shift=0.04),
            feasible=True,
            peak_temperature=320.3,
            temperature_gradient_rms=15.5,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    progress = build_progress_state(history=history)

    assert progress["diversity_deficit_level"] == "medium"


def test_build_progress_state_promotes_preserve_to_expand_after_dwell_completes() -> None:
    from optimizers.operator_pool.domain_state import build_progress_state

    history = [
        _record(
            40,
            _vector(),
            feasible=True,
            peak_temperature=320.0,
            temperature_gradient_rms=15.0,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            41,
            _vector(),
            feasible=True,
            peak_temperature=320.2,
            temperature_gradient_rms=15.2,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            42,
            _vector(),
            feasible=True,
            peak_temperature=320.3,
            temperature_gradient_rms=15.3,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
        _record(
            43,
            _vector(),
            feasible=True,
            peak_temperature=320.4,
            temperature_gradient_rms=15.4,
            c01_temperature_violation=0.0,
            panel_spread_violation=0.0,
        ),
    ]

    progress = build_progress_state(history=history)

    assert progress["preserve_dwell_remaining"] == 0
    assert progress["post_feasible_mode"] == "expand"


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


def test_prompt_operator_panel_exposes_structured_primitive_effects() -> None:
    from optimizers.operator_pool.state_builder import _build_prompt_operator_panel

    panel = _build_prompt_operator_panel(
        operator_summary={},
        candidate_operator_ids=(
            "component_block_translate_2_4",
            "component_subspace_sbx",
        ),
        regime_panel={
            "phase": "post_feasible_expand",
            "frontier_pressure": "high",
            "objective_balance": {
                "balance_pressure": "high",
                "preferred_effect": "peak_improve",
            },
        },
    )

    block_row = panel["component_block_translate_2_4"]
    subspace_row = panel["component_subspace_sbx"]
    assert block_row["expected_peak_effect"] == "improve"
    assert block_row["expected_gradient_effect"] == "neutral"
    assert block_row["applicability"] == "medium"
    assert subspace_row["expected_peak_effect"] == "diversify"
    assert subspace_row["expected_gradient_effect"] == "diversify"


def test_prompt_operator_panel_lists_structured_diversify_candidate_under_balanced_pressure() -> None:
    from optimizers.operator_pool.state_builder import _build_prompt_operator_panel

    panel = _build_prompt_operator_panel(
        operator_summary={},
        candidate_operator_ids=("component_subspace_sbx",),
        regime_panel={
            "phase": "post_feasible_expand",
            "frontier_pressure": "high",
            "objective_balance": {
                "balance_pressure": "medium",
                "preferred_effect": "balanced",
            },
        },
    )

    assert panel["component_subspace_sbx"]["applicability"] == "medium"
