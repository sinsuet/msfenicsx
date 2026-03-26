from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from orchestration.optimize_loop import run_optimization_loop


def test_optimize_loop_runs_one_iteration(tmp_path):
    result = run_optimization_loop(
        state_path=ROOT / "states" / "baseline_multicomponent.yaml",
        runs_root=tmp_path,
        max_iters=1,
        dry_run_llm=True,
    )

    run_dir = tmp_path / "run_0001"

    assert result["iterations"] == 1
    assert run_dir.exists()
    assert (run_dir / "state.yaml").exists()
    assert (run_dir / "evaluation.json").exists()
    assert (run_dir / "proposal.json").exists()
    assert (run_dir / "outputs").exists()

    evaluation = json.loads((run_dir / "evaluation.json").read_text(encoding="utf-8"))
    proposal = json.loads((run_dir / "proposal.json").read_text(encoding="utf-8"))

    assert evaluation["feasible"] is False
    assert proposal["changes"]


def test_optimize_loop_rejects_invalid_proposal_and_records_validation(tmp_path, monkeypatch):
    import orchestration.optimize_loop as optimize_loop

    def fake_propose_next_changes(**kwargs):
        return {
            "decision_summary": "push conductivity too high",
            "changes": [
                {
                    "path": "materials.spreader_material.conductivity",
                    "action": "set",
                    "old": 90.0,
                    "new": 2000.0,
                    "reason": "invalid test proposal",
                }
            ],
            "expected_effects": ["lower temperature"],
            "risk_notes": ["invalid on purpose"],
            "model_info": {"provider": "test", "model": "stub"},
        }

    monkeypatch.setattr(optimize_loop, "propose_next_changes", fake_propose_next_changes)

    result = run_optimization_loop(
        state_path=ROOT / "states" / "baseline_multicomponent.yaml",
        runs_root=tmp_path,
        max_iters=1,
        dry_run_llm=False,
        max_invalid_proposals=1,
    )

    run_dir = tmp_path / "run_0001"
    validation = json.loads((run_dir / "proposal_validation.json").read_text(encoding="utf-8"))
    decision = json.loads((run_dir / "decision.json").read_text(encoding="utf-8"))

    assert result["status"] == "invalid_proposal_limit"
    assert validation["valid"] is False
    assert any("conductivity" in reason for reason in validation["reasons"])
    assert decision["status"] == "invalid_proposal"
    assert not (run_dir / "next_state.yaml").exists()


def test_optimize_loop_feeds_invalid_reasons_into_next_llm_call(tmp_path, monkeypatch):
    import orchestration.optimize_loop as optimize_loop

    history_summaries = []
    calls = {"count": 0}

    def fake_propose_next_changes(**kwargs):
        calls["count"] += 1
        history_summaries.append(kwargs["history_summary"])
        if calls["count"] == 1:
            return {
                "decision_summary": "invalid first try",
                "changes": [
                    {
                        "path": "materials.spreader_material.conductivity",
                        "action": "set",
                        "old": 90.0,
                        "new": 2000.0,
                        "reason": "invalid test proposal",
                    }
                ],
                "expected_effects": ["lower temperature"],
                "risk_notes": ["invalid on purpose"],
                "model_info": {"provider": "test", "model": "stub"},
            }
        return {
            "decision_summary": "second try",
            "changes": [
                {
                    "path": "materials.spreader_material.conductivity",
                    "action": "set",
                    "old": 90.0,
                    "new": 135.0,
                    "reason": "valid follow-up proposal",
                }
            ],
            "expected_effects": ["lower temperature"],
            "risk_notes": [],
            "model_info": {"provider": "test", "model": "stub"},
        }

    monkeypatch.setattr(optimize_loop, "propose_next_changes", fake_propose_next_changes)

    result = run_optimization_loop(
        state_path=ROOT / "states" / "baseline_multicomponent.yaml",
        runs_root=tmp_path,
        max_iters=2,
        dry_run_llm=False,
        max_invalid_proposals=2,
    )

    assert result["iterations"] == 2
    assert len(history_summaries) == 2
    assert "invalid proposal" in history_summaries[1]
    assert "conductivity must stay within [0.1, 500.0]" in history_summaries[1]


def test_optimize_loop_adds_strategy_shift_hint_after_stagnation(tmp_path, monkeypatch):
    import orchestration.optimize_loop as optimize_loop

    history_summaries = []
    chip_temps = iter([0.3000, 0.2992, 0.2987])

    def fake_run_case_from_state(state, output_root):
        Path(output_root).mkdir(parents=True, exist_ok=True)
        return {
            "metrics": {
                "temperature_min": 0.0,
                "temperature_max": 1.0,
                "mesh": {"num_cells": 100},
            }
        }

    def fake_evaluate_case(state, metrics):
        return {
            "feasible": False,
            "violations": [{"name": "chip_max_temperature", "actual": 0.3, "limit": 0.2}],
            "objective_summary": {"chip_max_temperature": next(chip_temps)},
            "priority_actions": ["lower chip peak temperature"],
            "temperature_min": 0.0,
            "temperature_max": 1.0,
            "mesh": {"num_cells": 100},
        }

    def fake_propose_next_changes(**kwargs):
        history_summaries.append(kwargs["history_summary"])
        return {
            "decision_summary": "keep adjusting spreader conductivity",
            "changes": [
                {
                    "path": "materials.spreader_material.conductivity",
                    "action": "set",
                    "old": 90.0,
                    "new": 120.0,
                    "reason": "small material-side adjustment",
                }
            ],
            "expected_effects": ["lower chip max temperature"],
            "risk_notes": [],
            "model_info": {"provider": "test", "model": "stub"},
        }

    monkeypatch.setattr(optimize_loop, "run_case_from_state", fake_run_case_from_state)
    monkeypatch.setattr(optimize_loop, "evaluate_case", fake_evaluate_case)
    monkeypatch.setattr(optimize_loop, "propose_next_changes", fake_propose_next_changes)

    result = run_optimization_loop(
        state_path=ROOT / "states" / "baseline_multicomponent.yaml",
        runs_root=tmp_path,
        max_iters=3,
        dry_run_llm=False,
    )

    assert result["iterations"] == 3
    assert len(history_summaries) == 3
    assert "strategy shift suggestion" in history_summaries[2]
    assert "try geometry variables or a coordinated multi-variable change" in history_summaries[2]


def test_optimize_loop_can_continue_after_feasible_when_enabled(tmp_path, monkeypatch):
    import orchestration.optimize_loop as optimize_loop

    objective_values = iter([84.5, 83.8])
    proposal_calls = {"count": 0}

    def fake_run_case_from_state(state, output_root):
        Path(output_root).mkdir(parents=True, exist_ok=True)
        return {
            "metrics": {
                "temperature_min": 25.0,
                "temperature_max": 85.0,
                "mesh": {"num_cells": 100},
            }
        }

    def fake_evaluate_case(state, metrics):
        value = next(objective_values)
        return {
            "feasible": True,
            "violations": [],
            "objective_summary": {"chip_max_temperature": value},
            "priority_actions": [],
            "temperature_min": 25.0,
            "temperature_max": value,
            "mesh": {"num_cells": 100},
        }

    def fake_propose_next_changes(**kwargs):
        proposal_calls["count"] += 1
        return {
            "decision_summary": "keep improving a feasible design",
            "changes": [
                {
                    "path": "materials.spreader_material.conductivity",
                    "action": "set",
                    "old": 90.0 if proposal_calls["count"] == 1 else 120.0,
                    "new": 120.0 if proposal_calls["count"] == 1 else 144.0,
                    "reason": "continue reducing chip max temperature",
                }
            ],
            "expected_effects": ["lower chip max temperature while staying feasible"],
            "risk_notes": [],
            "model_info": {"provider": "test", "model": "stub"},
        }

    monkeypatch.setattr(optimize_loop, "run_case_from_state", fake_run_case_from_state)
    monkeypatch.setattr(optimize_loop, "evaluate_case", fake_evaluate_case)
    monkeypatch.setattr(optimize_loop, "propose_next_changes", fake_propose_next_changes)

    result = run_optimization_loop(
        state_path=ROOT / "states" / "baseline_multicomponent.yaml",
        runs_root=tmp_path,
        max_iters=2,
        dry_run_llm=False,
        continue_when_feasible=True,
    )

    assert result["iterations"] == 2
    assert result["status"] == "max_iters_reached"
    assert proposal_calls["count"] == 2
