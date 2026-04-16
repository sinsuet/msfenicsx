from __future__ import annotations

from optimizers.run_telemetry import build_evaluation_events


def test_build_evaluation_events_new_schema_has_required_fields() -> None:
    from optimizers.run_telemetry import build_evaluation_events

    history = [
        {
            "generation": 0,
            "individuals": [
                {
                    "individual_id": "g000-i00",
                    "status": "ok",
                    "objectives": {"temperature_max": 315.0, "temperature_gradient_rms": 2.7},
                    "constraints": {
                        "total_radiator_span": 0.6,
                        "radiator_span_max": 0.8,
                        "violation": 0.0,
                    },
                    "timing": {"cheap_ms": 1.2, "solve_ms": 850.0},
                    "decision_id": "g000-e0000-d00",
                }
            ],
        }
    ]
    rows = build_evaluation_events(history)
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
    assert row["objectives"]["temperature_max"] == 315.0
    assert row["status"] == "ok"


