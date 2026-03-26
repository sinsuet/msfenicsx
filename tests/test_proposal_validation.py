from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from thermal_state.load_save import load_state
from validation.proposals import validate_proposal_against_state


def test_validate_proposal_rejects_conductivity_above_upper_bound():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    proposal = {
        "changes": [
            {
                "path": "materials.spreader_material.conductivity",
                "action": "set",
                "old": 90.0,
                "new": 2000.0,
                "reason": "unrealistically high conductivity",
            }
        ]
    }

    validation = validate_proposal_against_state(state, proposal)

    assert validation["valid"] is False
    assert any("conductivity" in reason for reason in validation["reasons"])


def test_validate_proposal_rejects_overlapping_components():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    proposal = {
        "changes": [
            {
                "path": "components.2.x0",
                "action": "set",
                "old": 0.25,
                "new": 0.46,
                "reason": "move spreader over the chip",
            },
            {
                "path": "components.2.y0",
                "action": "set",
                "old": 0.32,
                "new": 0.18,
                "reason": "move spreader over the chip",
            },
        ]
    }

    validation = validate_proposal_against_state(state, proposal)

    assert validation["valid"] is False
    assert any("overlap" in reason for reason in validation["reasons"])


def test_validate_proposal_accepts_reasonable_conductivity_update():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    proposal = {
        "changes": [
            {
                "path": "materials.spreader_material.conductivity",
                "action": "set",
                "old": 90.0,
                "new": 135.0,
                "reason": "realistic conductivity increase",
            }
        ]
    }

    validation = validate_proposal_against_state(state, proposal)

    assert validation["valid"] is True
    assert validation["reasons"] == []


def test_validate_proposal_allows_growth_inside_design_domain():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    proposal = {
        "changes": [
            {
                "path": "components.2.height",
                "action": "set",
                "old": 0.1,
                "new": 0.14,
                "reason": "grow spreader within the design domain",
            }
        ]
    }

    validation = validate_proposal_against_state(state, proposal)

    assert validation["valid"] is True
    assert validation["reasons"] == []


def test_validate_proposal_rejects_unregistered_change_path():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    proposal = {
        "changes": [
            {
                "path": "components.1.y0",
                "action": "set",
                "old": 0.2,
                "new": 0.18,
                "reason": "move chip vertically even though this path is not in the editable set",
            }
        ]
    }

    validation = validate_proposal_against_state(state, proposal)

    assert validation["valid"] is False
    assert any("not allowed" in reason for reason in validation["reasons"])


def test_validate_proposal_accepts_registered_heat_source_update():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    proposal = {
        "changes": [
            {
                "path": "heat_sources.0.value",
                "action": "set",
                "old": 15000.0,
                "new": 18000.0,
                "reason": "explore a higher load within the registered variable range",
            }
        ]
    }

    validation = validate_proposal_against_state(state, proposal)

    assert validation["valid"] is True
