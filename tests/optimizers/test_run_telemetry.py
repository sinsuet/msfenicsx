from __future__ import annotations

import pytest

from optimizers.run_telemetry import build_evaluation_events, build_progress_timeline


def test_build_evaluation_events_derives_compact_constraint_fields() -> None:
    rows = build_evaluation_events(
        run_id="s1_typical-b11-run",
        mode_id="nsga2_raw",
        seed=7,
        history=[
            {
                "evaluation_index": 1,
                "source": "baseline",
                "feasible": False,
                "decision_vector": {"c01_x": 0.22, "c01_y": 0.51},
                "objective_values": {
                    "minimize_peak_temperature": 302.0,
                    "minimize_temperature_gradient_rms": 9.8,
                },
                "constraint_values": {
                    "radiator_span_budget": 2.5,
                    "c01_peak_temperature_limit": 0.25,
                    "layout_spacing": -0.1,
                },
                "evaluation_report": {"feasible": False},
            },
            {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {"c01_x": 0.24, "c01_y": 0.53},
                "objective_values": {
                    "minimize_peak_temperature": 299.0,
                    "minimize_temperature_gradient_rms": 8.2,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.0,
                    "c01_peak_temperature_limit": -0.2,
                    "layout_spacing": -0.1,
                },
                "evaluation_report": {"feasible": True},
            },
        ],
        objectives=(
            {"objective_id": "minimize_peak_temperature", "sense": "minimize"},
            {"objective_id": "minimize_temperature_gradient_rms", "sense": "minimize"},
        ),
        generation_rows=[
            {"generation_index": 1, "num_evaluations_so_far": 2},
        ],
    )

    assert rows[0]["total_constraint_violation"] == pytest.approx(2.75)
    assert rows[0]["dominant_violation_constraint_id"] == "radiator_span_budget"
    assert rows[0]["dominant_violation_constraint_family"] == "sink_budget"
    assert rows[0]["violation_count"] == 2
    assert rows[0]["pareto_membership_after_eval"] is False
    assert rows[1]["entered_feasible_region"] is True
    assert rows[1]["pareto_membership_after_eval"] is True


def test_build_progress_timeline_uses_optimizer_only_feasibility_when_baseline_is_feasible() -> None:
    evaluation_rows = build_evaluation_events(
        run_id="s1_typical-b11-run",
        mode_id="nsga2_raw",
        seed=7,
        history=[
            {
                "evaluation_index": 1,
                "source": "baseline",
                "feasible": True,
                "decision_vector": {"c01_x": 0.22, "c01_y": 0.51},
                "objective_values": {
                    "minimize_peak_temperature": 298.0,
                    "minimize_temperature_gradient_rms": 7.8,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.0,
                    "c01_peak_temperature_limit": -0.2,
                },
                "evaluation_report": {"feasible": True},
            },
            {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": False,
                "decision_vector": {"c01_x": 0.24, "c01_y": 0.53},
                "objective_values": {
                    "minimize_peak_temperature": 305.0,
                    "minimize_temperature_gradient_rms": 9.2,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.1,
                    "c01_peak_temperature_limit": 0.3,
                },
                "evaluation_report": {"feasible": False},
            },
            {
                "evaluation_index": 3,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {"c01_x": 0.26, "c01_y": 0.55},
                "objective_values": {
                    "minimize_peak_temperature": 299.0,
                    "minimize_temperature_gradient_rms": 8.2,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.0,
                    "c01_peak_temperature_limit": -0.1,
                },
                "evaluation_report": {"feasible": True},
            },
        ],
        objectives=(
            {"objective_id": "minimize_peak_temperature", "sense": "minimize"},
            {"objective_id": "minimize_temperature_gradient_rms", "sense": "minimize"},
        ),
    )

    assert evaluation_rows[0]["entered_feasible_region"] is False
    assert evaluation_rows[1]["feasibility_phase"] == "prefeasible"
    assert evaluation_rows[2]["entered_feasible_region"] is True

    timeline = build_progress_timeline(evaluation_rows)

    assert timeline[0]["feasible_count_so_far"] == 0
    assert timeline[0]["feasible_rate_so_far"] == pytest.approx(0.0)
    assert timeline[0]["best_temperature_max_so_far"] is None
    assert timeline[-1]["feasible_count_so_far"] == 1
    assert timeline[-1]["feasible_rate_so_far"] == pytest.approx(0.5)
    assert timeline[-1]["first_feasible_eval_so_far"] == 3
    assert timeline[-1]["best_temperature_max_so_far"] == pytest.approx(299.0)
