from __future__ import annotations

from optimizers.run_telemetry import build_evaluation_events


def test_build_evaluation_events_new_schema_has_required_fields() -> None:
    from optimizers.run_telemetry import build_evaluation_events

    history = [
        {
            "evaluation_index": 1,
            "generation": 0,
            "source": "baseline",
            "feasible": True,
            "objective_values": {"temperature_max": 330.0, "temperature_gradient_rms": 3.2},
            "constraint_values": {"total_radiator_span": 0.6, "radiator_span_max": 0.8, "violation": 0.0},
        },
        {
            "evaluation_index": 2,
            "generation": 1,
            "source": "optimizer",
            "feasible": True,
            "objective_values": {"temperature_max": 315.0, "temperature_gradient_rms": 2.7},
            "constraint_values": {"total_radiator_span": 0.6, "radiator_span_max": 0.8, "violation": 0.0},
            "timing": {"cheap_ms": 1.2, "solve_ms": 850.0},
        },
    ]
    objective_definitions = [
        {"objective_id": "minimize_peak_temperature", "metric": "summary.temperature_max", "sense": "minimize"},
        {
            "objective_id": "minimize_temperature_gradient_rms",
            "metric": "summary.temperature_gradient_rms",
            "sense": "minimize",
        },
    ]
    # history records use objective_id keys; the builder must re-key onto the
    # spec's metric suffix so analytics see ``temperature_max`` rather than
    # ``minimize_peak_temperature``.
    history[1]["objective_values"] = {
        "minimize_peak_temperature": 315.0,
        "minimize_temperature_gradient_rms": 2.7,
    }
    rows = build_evaluation_events(history, objective_definitions=objective_definitions)
    assert len(rows) == 1
    row = rows[0]
    for key in (
        "decision_id",
        "generation",
        "eval_index",
        "individual_id",
        "objectives",
        "constraints",
        "status",
        "timing",
    ):
        assert key in row, f"missing {key}"
    assert row["generation"] == 1
    assert row["eval_index"] == 0
    assert row["individual_id"] == "g001-i00"
    assert row["objectives"]["temperature_max"] == 315.0
    assert row["objectives"]["temperature_gradient_rms"] == 2.7
    assert row["status"] == "ok"


