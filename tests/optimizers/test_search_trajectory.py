from optimizers.analytics.search_trajectory import build_search_trajectory


def _record(
    evaluation_index: int,
    generation: int,
    *,
    x: float,
    y: float,
    temperature: float,
    gradient: float,
    feasible: bool = True,
    violation: float = 0.0,
) -> dict:
    return {
        "evaluation_index": evaluation_index,
        "generation": generation,
        "source": "optimizer",
        "feasible": feasible,
        "decision_vector": {"c01_x": x, "c01_y": y},
        "objective_values": {
            "minimize_peak_temperature": temperature,
            "minimize_temperature_gradient_rms": gradient,
        },
        "constraint_values": {"radiator_span_budget": violation},
    }


def test_build_search_trajectory_selects_weighted_representatives_and_marks_shared_nodes() -> None:
    history = [
        {"evaluation_index": 0, "generation": 0, "source": "baseline"},
        _record(1, 0, x=0.100, y=0.100, temperature=330.0, gradient=14.0),
        _record(2, 0, x=0.500, y=0.500, temperature=320.0, gradient=20.0),
        _record(3, 1, x=0.110, y=0.100, temperature=329.0, gradient=13.0),
        _record(4, 1, x=0.500, y=0.500, temperature=319.0, gradient=12.0),
    ]

    result = build_search_trajectory(history, bin_width=0.05)

    assert len(result.nodes) == 2
    assert len(result.edges) == 5
    shared_nodes = [row for row in result.nodes if row["vector_count"] > 1]
    assert len(shared_nodes) == 2
    assert {row["vector_id"] for row in result.metrics if row["scope"] == "vector"} == {
        "V1",
        "V2",
        "V3",
        "V4",
        "V5",
    }
    overall = next(row for row in result.metrics if row["scope"] == "overall")
    assert overall["num_nodes"] == 2
    assert overall["num_edges"] == 5
    assert overall["shared_nodes"] == 2
    assert overall["pareto_nodes"] == 1


def test_build_search_trajectory_uses_infeasible_low_violation_records_when_generation_has_no_feasible_records() -> None:
    history = [
        _record(
            1,
            0,
            x=0.100,
            y=0.100,
            temperature=1.0e12,
            gradient=1.0e12,
            feasible=False,
            violation=3.0,
        ),
        _record(
            2,
            0,
            x=0.200,
            y=0.200,
            temperature=1.0e12,
            gradient=1.0e12,
            feasible=False,
            violation=1.0,
        ),
        _record(3, 1, x=0.250, y=0.250, temperature=340.0, gradient=30.0, feasible=True),
    ]

    result = build_search_trajectory(history, bin_width=0.05)

    assert result.nodes
    start_rows = [row for row in result.nodes if row["first_generation"] == 0]
    assert start_rows
    assert min(row["representative_evaluation_index"] for row in start_rows) == 2
