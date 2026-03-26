from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from orchestration.demo_summary import collect_demo_summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_demo_summary_links_run_n_proposal_to_run_n_plus_1_effect(tmp_path):
    run_1 = tmp_path / "run_0001"
    run_2 = tmp_path / "run_0002"

    _write_json(
        run_1 / "evaluation.json",
        {
            "feasible": False,
            "violations": [{"name": "chip_max_temperature", "limit": 85.0, "actual": 89.3}],
            "objective_summary": {"chip_max_temperature": 89.3},
        },
    )
    _write_json(
        run_1 / "proposal.json",
        {
            "decision_summary": "increase spreader conductivity",
            "changes": [
                {
                    "path": "materials.spreader_material.conductivity",
                    "old": 90.0,
                    "new": 126.0,
                }
            ],
        },
    )
    _write_json(run_1 / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_1 / "decision.json", {"iteration": 1, "status": "proposal_applied"})

    _write_json(
        run_2 / "evaluation.json",
        {
            "feasible": False,
            "violations": [{"name": "chip_max_temperature", "limit": 85.0, "actual": 88.7}],
            "objective_summary": {"chip_max_temperature": 88.7},
        },
    )
    _write_json(run_2 / "proposal.json", {"decision_summary": "next step", "changes": []})
    _write_json(run_2 / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_2 / "decision.json", {"iteration": 2, "status": "proposal_applied"})

    summary = collect_demo_summary(tmp_path)

    assert summary["runs"][0]["run_id"] == "run_0001"
    assert summary["runs"][0]["chip_max_before"] == 89.3
    assert summary["runs"][0]["chip_max_after"] == 88.7
    assert summary["runs"][0]["delta_chip_max"] == -0.5999999999999943
    assert summary["runs"][0]["validation_status"] == "valid"
    assert summary["runs"][0]["changed_paths"] == ["materials.spreader_material.conductivity"]
    assert summary["runs"][0]["change_categories"] == ["material"]
