from __future__ import annotations

import pytest

from optimizers.run_telemetry import build_evaluation_events


def test_build_evaluation_events_derives_compact_constraint_fields() -> None:
    rows = build_evaluation_events(
        run_id="panel-four-component-hot-cold-benchmark-b11-run",
        mode_id="nsga2_raw",
        seed=7,
        history=[
            {
                "evaluation_index": 1,
                "source": "baseline",
                "feasible": False,
                "decision_vector": {"processor_x": 0.22, "processor_y": 0.51},
                "objective_values": {
                    "minimize_hot_pa_peak": 302.0,
                    "maximize_cold_battery_min": 255.0,
                    "minimize_radiator_resource": 0.48,
                },
                "constraint_values": {
                    "cold_battery_floor": 2.5,
                    "hot_pa_limit": 0.25,
                    "hot_component_spread_limit": -0.1,
                },
                "case_reports": {},
            },
            {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {"processor_x": 0.24, "processor_y": 0.53},
                "objective_values": {
                    "minimize_hot_pa_peak": 299.0,
                    "maximize_cold_battery_min": 259.0,
                    "minimize_radiator_resource": 0.44,
                },
                "constraint_values": {
                    "cold_battery_floor": 0.0,
                    "hot_pa_limit": -0.2,
                    "hot_component_spread_limit": -0.1,
                },
                "case_reports": {},
            },
        ],
        objectives=(
            {"objective_id": "minimize_hot_pa_peak", "sense": "minimize"},
            {"objective_id": "maximize_cold_battery_min", "sense": "maximize"},
            {"objective_id": "minimize_radiator_resource", "sense": "minimize"},
        ),
        generation_rows=[
            {"generation_index": 1, "num_evaluations_so_far": 2},
        ],
    )

    assert rows[0]["total_constraint_violation"] == pytest.approx(2.75)
    assert rows[0]["dominant_violation_constraint_id"] == "cold_battery_floor"
    assert rows[0]["dominant_violation_constraint_family"] == "cold_dominant"
    assert rows[0]["violation_count"] == 2
    assert rows[0]["pareto_membership_after_eval"] is False
    assert rows[1]["entered_feasible_region"] is True
    assert rows[1]["pareto_membership_after_eval"] is True
