from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from evaluator.report import evaluate_case
from thermal_state.load_save import load_state


def test_evaluator_reports_chip_temp_violation():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")

    evaluation = evaluate_case(
        state=state,
        metrics={
            "temperature_min": 25.0,
            "temperature_max": 92.0,
            "component_summary": {
                "chip": {"min": 88.0, "max": 92.0, "mean": 90.0},
                "base_plate": {"min": 25.0, "max": 80.0, "mean": 54.0},
            },
            "mesh": {"num_cells": 956},
        },
    )

    assert evaluation["feasible"] is False
    assert evaluation["violations"][0]["name"] == "chip_max_temperature"
    assert evaluation["violations"][0]["actual"] == 92.0
    assert evaluation["violations"][0]["limit"] == 85.0
    assert evaluation["objective_summary"]["chip_max_temperature"] == 92.0
    assert evaluation["temperature_max"] == 92.0
    assert evaluation["temperature_min"] == 25.0
    assert evaluation["mesh"]["num_cells"] == 956


def test_evaluator_marks_case_feasible_when_constraint_is_satisfied():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")

    evaluation = evaluate_case(
        state=state,
        metrics={
            "temperature_min": 25.0,
            "temperature_max": 84.0,
            "component_summary": {
                "chip": {"min": 76.0, "max": 84.0, "mean": 80.0},
            },
            "mesh": {"num_cells": 400},
        },
    )

    assert evaluation["feasible"] is True
    assert evaluation["violations"] == []
    assert evaluation["objective_summary"]["chip_max_temperature"] == 84.0
    assert evaluation["temperature_max"] == 84.0
