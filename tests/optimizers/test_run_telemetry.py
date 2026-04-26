from __future__ import annotations

from optimizers.run_telemetry import build_evaluation_events, build_progress_timeline


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
            "solver_skipped": False,
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
        "solver_skipped",
        "timing",
    ):
        assert key in row, f"missing {key}"
    assert row["generation"] == 1
    assert row["eval_index"] == 0
    assert row["individual_id"] == "g001-i00"
    assert row["objectives"]["temperature_max"] == 315.0
    assert row["objectives"]["temperature_gradient_rms"] == 2.7
    assert row["status"] == "ok"
    assert row["solver_skipped"] is False


def test_build_evaluation_events_includes_cheap_failure_diagnostics() -> None:
    rows = build_evaluation_events(
        [
            {
                "evaluation_index": 2,
                "generation": 1,
                "source": "optimizer",
                "feasible": False,
                "solver_skipped": True,
                "failure_reason": "cheap_constraint_violation",
                "cheap_constraint_issues": [
                    "clearance_violation:c01-001:c02-001",
                    "clearance_violation:c03-001:c04-001",
                ],
                "objective_values": {"minimize_peak_temperature": 1.0e12},
                "constraint_values": {
                    "radiator_span_budget": 0.0,
                    "cheap_geometry_issue_count": 2.0,
                },
                "timing": {},
            },
        ],
        objective_definitions=[
            {"objective_id": "minimize_peak_temperature", "metric": "summary.temperature_max", "sense": "minimize"},
        ],
    )

    assert rows[0]["failure_reason"] == "cheap_constraint_violation"
    assert rows[0]["cheap_constraint_issue_count"] == 2
    assert rows[0]["cheap_constraint_issue_examples"] == [
        "clearance_violation:c01-001:c02-001",
        "clearance_violation:c03-001:c04-001",
    ]


def test_build_progress_timeline_skips_baseline_rows_and_uses_generation_fallback() -> None:
    timeline = build_progress_timeline(
        [
            {
                "evaluation_index": 1,
                "generation": 0,
                "source": "baseline",
                "feasible": True,
                "objective_values": {"minimize_peak_temperature": 330.0, "minimize_temperature_gradient_rms": 4.5},
                "constraint_values": {"radiator_span_budget": 0.0},
            },
            {
                "evaluation_index": 2,
                "generation": 1,
                "source": "optimizer",
                "feasible": False,
                "objective_values": {"minimize_peak_temperature": 320.0, "minimize_temperature_gradient_rms": 4.1},
                "constraint_values": {"radiator_span_budget": 0.2},
            },
            {
                "evaluation_index": 3,
                "generation": 1,
                "source": "optimizer",
                "feasible": True,
                "objective_values": {"minimize_peak_temperature": 310.0, "minimize_temperature_gradient_rms": 3.8},
                "constraint_values": {"radiator_span_budget": 0.0},
            },
        ]
    )

    assert [row["evaluation_index"] for row in timeline] == [2, 3]
    assert [row["generation_index"] for row in timeline] == [1, 1]
    assert timeline[-1]["first_feasible_eval_so_far"] == 3
    assert [row["pde_evaluation_index"] for row in timeline] == [1, 2]
    assert timeline[-1]["first_feasible_pde_eval_so_far"] == 2
    assert timeline[-1]["best_temperature_max_so_far"] == 310.0
    assert timeline[-1]["best_gradient_rms_so_far"] == 3.8
    assert timeline[-1]["budget_fraction"] == 1.0


def test_build_progress_timeline_accepts_evaluation_event_schema() -> None:
    timeline = build_progress_timeline(
        [
            {
                "generation": 1,
                "eval_index": 0,
                "objectives": {"temperature_max": 320.0, "temperature_gradient_rms": 4.0},
                "constraints": {"radiator_span_budget": 0.2},
                "status": "infeasible",
            },
            {
                "generation": 2,
                "eval_index": 1,
                "objectives": {"temperature_max": 308.0, "temperature_gradient_rms": 3.5},
                "constraints": {"radiator_span_budget": 0.0},
                "status": "ok",
            },
        ]
    )

    assert [row["evaluation_index"] for row in timeline] == [0, 1]
    assert timeline[-1]["first_feasible_eval_so_far"] == 1
    assert [row["pde_evaluation_index"] for row in timeline] == [1, 2]
    assert timeline[-1]["first_feasible_pde_eval_so_far"] == 2
    assert timeline[-1]["best_total_constraint_violation_so_far"] == 0.0
    assert timeline[-1]["best_temperature_max_so_far"] == 308.0


def test_build_progress_timeline_tracks_solver_attempts_separately_from_optimizer_index() -> None:
    timeline = build_progress_timeline(
        [
            {
                "evaluation_index": 1,
                "generation": 0,
                "source": "baseline",
                "feasible": False,
                "objective_values": {"minimize_peak_temperature": 340.0, "minimize_temperature_gradient_rms": 20.0},
                "constraint_values": {"radiator_span_budget": 0.5},
            },
            {
                "evaluation_index": 2,
                "generation": 1,
                "source": "optimizer",
                "feasible": False,
                "solver_skipped": True,
                "failure_reason": "cheap_constraint_violation",
                "objective_values": {"minimize_peak_temperature": 1.0e12, "minimize_temperature_gradient_rms": 1.0e12},
                "constraint_values": {"radiator_span_budget": 0.3},
            },
            {
                "evaluation_index": 3,
                "generation": 1,
                "source": "optimizer",
                "feasible": False,
                "solver_skipped": False,
                "objective_values": {"minimize_peak_temperature": 325.0, "minimize_temperature_gradient_rms": 11.0},
                "constraint_values": {"radiator_span_budget": 0.1},
            },
            {
                "evaluation_index": 4,
                "generation": 2,
                "source": "optimizer",
                "feasible": True,
                "solver_skipped": False,
                "objective_values": {"minimize_peak_temperature": 309.0, "minimize_temperature_gradient_rms": 8.7},
                "constraint_values": {"radiator_span_budget": 0.0},
            },
        ]
    )

    assert [row["evaluation_index"] for row in timeline] == [2, 3, 4]
    assert [row["solver_skipped"] for row in timeline] == [True, False, False]
    assert [row["pde_attempted"] for row in timeline] == [False, True, True]
    assert [row["pde_evaluation_index"] for row in timeline] == [0, 1, 2]
    assert timeline[-1]["first_feasible_eval_so_far"] == 4
    assert timeline[-1]["first_feasible_pde_eval_so_far"] == 2


def test_build_progress_timeline_carries_current_values_and_status() -> None:
    timeline = build_progress_timeline(
        [
            {
                "generation": 1,
                "eval_index": 0,
                "objectives": {"temperature_max": 321.0, "temperature_gradient_rms": 11.5},
                "constraints": {"radiator_span_budget": 0.4},
                "status": "infeasible",
            },
            {
                "generation": 2,
                "eval_index": 1,
                "objectives": {"temperature_max": 309.0, "temperature_gradient_rms": 8.8},
                "constraints": {"radiator_span_budget": 0.0},
                "status": "ok",
            },
        ]
    )

    assert timeline[0]["status"] == "infeasible"
    assert timeline[0]["current_temperature_max"] == 321.0
    assert timeline[0]["current_gradient_rms"] == 11.5
    assert timeline[0]["current_total_constraint_violation"] == 0.4
    assert timeline[1]["status"] == "ok"
    assert timeline[1]["current_temperature_max"] == 309.0
    assert timeline[1]["best_temperature_max_so_far"] == 309.0


def test_build_progress_timeline_sanitizes_failed_sentinel_values() -> None:
    timeline = build_progress_timeline(
        [
            {
                "generation": 1,
                "eval_index": 0,
                "objectives": {"temperature_max": 1.0e12, "temperature_gradient_rms": 1.0e12},
                "constraints": {"radiator_span_budget": 1.0e12},
                "status": "failed",
            }
        ]
    )

    assert timeline[0]["status"] == "failed"
    assert timeline[0]["current_temperature_max"] is None
    assert timeline[0]["current_gradient_rms"] is None
    assert timeline[0]["current_total_constraint_violation"] is None
    assert timeline[0]["best_total_constraint_violation_so_far"] is None
