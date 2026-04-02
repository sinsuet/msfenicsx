from __future__ import annotations

import pytest

from optimizers.run_telemetry import build_evaluation_events


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
