from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from thermal_state.load_save import load_state


def test_baseline_state_loads_and_validates():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")

    assert state.geometry["type"] == "multirect_2d"
    assert [component.name for component in state.components] == [
        "base_plate",
        "chip",
        "heat_spreader",
    ]
    assert state.materials["chip_material"].conductivity == 45.0
    assert state.mesh["nx"] == 36
    assert state.geometry["design_domain"]["height"] == 0.5


def test_baseline_state_includes_si_units_and_reference_conditions():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")

    assert state.units["temperature"] == "degC"
    assert state.units["conductivity"] == "W/(m*K)"
    assert state.reference_conditions["ambient_temperature"] == 25.0
    assert state.reference_conditions["cold_sink_temperature"] == 25.0


def test_baseline_constraint_uses_engineering_temperature_limit():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")

    assert state.constraints[0].name == "chip_max_temperature"
    assert state.constraints[0].value == 85.0
