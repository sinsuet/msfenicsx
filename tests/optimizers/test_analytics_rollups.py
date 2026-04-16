"""Roll up evaluation events into per-generation summaries."""

from __future__ import annotations


def test_rollup_per_generation_counts_and_objectives() -> None:
    from optimizers.analytics.rollups import rollup_per_generation

    events = [
        {
            "generation": 0,
            "status": "ok",
            "objectives": {"temperature_max": 320.0, "temperature_gradient_rms": 3.0},
        },
        {
            "generation": 0,
            "status": "ok",
            "objectives": {"temperature_max": 310.0, "temperature_gradient_rms": 2.5},
        },
        {
            "generation": 0,
            "status": "infeasible_cheap",
            "objectives": None,
        },
        {
            "generation": 1,
            "status": "ok",
            "objectives": {"temperature_max": 305.0, "temperature_gradient_rms": 2.2},
        },
    ]
    rows = rollup_per_generation(events, reference_point=(330.0, 5.0))
    assert [r["generation"] for r in rows] == [0, 1]
    assert rows[0]["num_feasible"] == 2
    assert rows[0]["num_infeasible"] == 1
    assert rows[0]["population_size"] == 3
    assert rows[0]["hypervolume"] > 0.0
    assert rows[1]["hypervolume"] >= rows[0]["hypervolume"]  # monotone on this data


def test_rollup_per_generation_empty_input() -> None:
    from optimizers.analytics.rollups import rollup_per_generation

    assert rollup_per_generation([], reference_point=(1.0, 1.0)) == []
