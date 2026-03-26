import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from llm_adapters.dashscope_qwen import (
    build_change_prompt,
    parse_change_proposal,
    propose_next_changes,
)
from thermal_state.load_save import load_state


def test_dashscope_adapter_parses_structured_change_proposal():
    raw = """
    {
      "decision_summary": "increase heat spreading near the chip",
      "changes": [],
      "expected_effects": ["lower chip max temperature"],
      "risk_notes": ["layout width increases"]
    }
    """

    parsed = parse_change_proposal(raw)

    assert parsed["changes"] == []
    assert parsed["decision_summary"] == "increase heat spreading near the chip"


def test_dashscope_adapter_parses_first_json_object_when_trailing_text_present():
    raw = """
    ```json
    {
      "decision_summary": "increase spreader width first",
      "changes": [],
      "expected_effects": ["lower chip max temperature"],
      "risk_notes": []
    }
    ```
    I chose this because the spreader is still too narrow near the heat source.
    """

    parsed = parse_change_proposal(raw)

    assert parsed["decision_summary"] == "increase spreader width first"
    assert parsed["expected_effects"] == ["lower chip max temperature"]


def test_dashscope_adapter_writes_raw_response_before_parse_failure(tmp_path, monkeypatch):
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    evaluation = {
        "feasible": False,
        "violations": [{"name": "chip_max_temperature", "actual": 89.3, "limit": 85.0}],
        "objective_summary": {"chip_max_temperature": 89.3},
        "priority_actions": ["lower chip peak temperature"],
    }
    response_payload = {
        "choices": [
            {
                "message": {
                    "content": "not valid json at all",
                }
            }
        ],
        "usage": {"total_tokens": 123},
    }

    monkeypatch.setattr(
        "llm_adapters.dashscope_qwen._post_chat_completion",
        lambda **kwargs: response_payload,
    )
    monkeypatch.setattr(
        "llm_adapters.dashscope_qwen.load_system_prompt",
        lambda path=None: "system prompt",
    )

    try:
        propose_next_changes(
            state=state,
            evaluation=evaluation,
            history_summary="run_0006 violated chip_max_temperature",
            output_dir=tmp_path,
            api_key="test-key",
        )
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("Expected JSONDecodeError for malformed LLM output")

    assert (tmp_path / "prompt.txt").exists()
    assert (tmp_path / "raw_response.json").exists()
    assert "not valid json at all" in (tmp_path / "raw_response.json").read_text(encoding="utf-8")


def test_dashscope_prompt_contains_state_and_evaluation_context():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    evaluation = {
        "feasible": False,
        "violations": [{"name": "chip_max_temperature", "actual": 89.3, "limit": 85.0}],
        "objective_summary": {"chip_max_temperature": 89.3},
        "priority_actions": ["lower chip peak temperature"],
    }

    prompt = build_change_prompt(
        state=state,
        evaluation=evaluation,
        history_summary="run_0001 violated chip_max_temperature",
    )

    assert "chip_max_temperature" in prompt
    assert "run_0001 violated chip_max_temperature" in prompt
    assert "base_plate" in prompt
    assert "changes" in prompt


def test_dashscope_prompt_includes_invalid_proposal_feedback():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    evaluation = {
        "feasible": False,
        "violations": [{"name": "chip_max_temperature", "actual": 89.3, "limit": 85.0}],
        "objective_summary": {"chip_max_temperature": 89.3},
        "priority_actions": ["lower chip peak temperature"],
    }

    prompt = build_change_prompt(
        state=state,
        evaluation=evaluation,
        history_summary=(
            "run_0009 invalid proposal: "
            "conductivity must stay within [0.1, 500.0], got 2000.000000"
        ),
    )

    assert "invalid proposal" in prompt
    assert "conductivity must stay within [0.1, 500.0]" in prompt


def test_dashscope_prompt_includes_editable_variable_registry():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    evaluation = {
        "feasible": False,
        "violations": [{"name": "chip_max_temperature", "actual": 89.3, "limit": 85.0}],
        "objective_summary": {"chip_max_temperature": 89.3},
        "priority_actions": ["lower chip peak temperature"],
    }

    prompt = build_change_prompt(
        state=state,
        evaluation=evaluation,
        history_summary="run_0012 violated chip_max_temperature",
    )

    assert "Editable variables" in prompt
    assert "materials.spreader_material.conductivity" in prompt
    assert "components.2.height" in prompt
    assert "heat_sources.0.value" in prompt


def test_dashscope_prompt_includes_variable_strategy_metadata():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    evaluation = {
        "feasible": False,
        "violations": [{"name": "chip_max_temperature", "actual": 89.3, "limit": 85.0}],
        "objective_summary": {"chip_max_temperature": 89.3},
        "priority_actions": ["lower chip peak temperature"],
    }

    prompt = build_change_prompt(
        state=state,
        evaluation=evaluation,
        history_summary="run_0013 plateau detected",
    )

    assert "Priority=1" in prompt
    assert "Role=primary" in prompt
    assert "JointChanges=allowed" in prompt
    assert "RecommendedDirection=increase" in prompt
