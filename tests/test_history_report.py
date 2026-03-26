from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from orchestration.history_report import collect_history_summary, write_history_summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_collect_history_summary_reads_run_metadata(tmp_path):
    run_dir = tmp_path / "run_0001"
    (run_dir / "outputs" / "figures").mkdir(parents=True)
    (run_dir / "outputs" / "figures" / "overview.html").write_text("<html>overview</html>", encoding="utf-8")
    (run_dir / "outputs" / "figures" / "temperature.html").write_text("<html>temperature</html>", encoding="utf-8")
    _write_json(
        run_dir / "evaluation.json",
        {
            "feasible": False,
            "temperature_max": 0.2572,
            "violations": [{"name": "chip_max_temperature"}],
            "objective_summary": {"chip_max_temperature": 0.2572},
        },
    )
    _write_json(
        run_dir / "proposal.json",
        {
            "decision_summary": "increase spreader conductivity",
            "changes": [{"path": "materials.spreader_material.conductivity", "new": 135.0}],
            "model_info": {"provider": "dashscope", "model": "qwen3.5-plus"},
        },
    )
    _write_json(
        run_dir / "proposal_validation.json",
        {"valid": True, "reasons": []},
    )
    _write_json(
        run_dir / "decision.json",
        {"status": "proposal_applied"},
    )

    summary = collect_history_summary(tmp_path)

    assert summary["runs"][0]["run_id"] == "run_0001"
    assert summary["runs"][0]["status"] == "proposal_applied"
    assert summary["runs"][0]["feasible"] is False
    assert summary["runs"][0]["chip_max_temperature"] == 0.2572
    assert summary["runs"][0]["validation_valid"] is True
    assert summary["runs"][0]["decision_summary"] == "increase spreader conductivity"
    assert summary["runs"][0]["overview_html"].endswith("overview.html")
    assert summary["runs"][0]["temperature_max"] == 0.2572


def test_collect_history_summary_falls_back_to_summary_txt_for_legacy_runs(tmp_path):
    run_dir = tmp_path / "run_0003"
    (run_dir / "outputs" / "data").mkdir(parents=True)
    _write_json(
        run_dir / "evaluation.json",
        {
            "feasible": False,
            "objective_summary": {"chip_max_temperature": 0.257134},
        },
    )
    _write_json(run_dir / "proposal.json", {"decision_summary": "legacy run", "changes": []})
    _write_json(run_dir / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_dir / "decision.json", {"status": "proposal_applied"})
    (run_dir / "outputs" / "data" / "summary.txt").write_text(
        "num_cells: 956\n"
        "num_vertices: 548\n"
        "temperature_min: 0.000000\n"
        "temperature_max: 0.257134\n",
        encoding="utf-8",
    )

    summary = collect_history_summary(tmp_path)

    assert summary["runs"][0]["temperature_max"] == 0.257134


def test_collect_history_summary_reads_temperature_with_units_from_summary_txt(tmp_path):
    run_dir = tmp_path / "run_0004"
    (run_dir / "outputs" / "data").mkdir(parents=True)
    _write_json(
        run_dir / "evaluation.json",
        {
            "feasible": False,
            "objective_summary": {"chip_max_temperature": 89.301304},
        },
    )
    _write_json(run_dir / "proposal.json", {"decision_summary": "si units run", "changes": []})
    _write_json(run_dir / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_dir / "decision.json", {"status": "proposal_applied"})
    (run_dir / "outputs" / "data" / "summary.txt").write_text(
        "num_cells: 956\n"
        "num_vertices: 548\n"
        "temperature_min (degC): 25.000000\n"
        "temperature_max (degC): 89.301304\n",
        encoding="utf-8",
    )

    summary = collect_history_summary(tmp_path)

    assert summary["runs"][0]["temperature_min"] == 25.0
    assert summary["runs"][0]["temperature_max"] == 89.301304


def test_write_history_summary_creates_json_file(tmp_path):
    run_dir = tmp_path / "run_0002"
    _write_json(run_dir / "evaluation.json", {"feasible": True, "objective_summary": {"chip_max_temperature": 0.19}})
    _write_json(run_dir / "proposal.json", {"decision_summary": "keep current design", "changes": []})
    _write_json(run_dir / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_dir / "decision.json", {"status": "feasible"})

    output_path = write_history_summary(tmp_path)

    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runs"][0]["run_id"] == "run_0002"


def test_collect_history_summary_includes_rich_llm_details_and_effect_link(tmp_path):
    run_1 = tmp_path / "run_0001"
    run_2 = tmp_path / "run_0002"
    (run_1 / "outputs" / "figures").mkdir(parents=True)
    (run_2 / "outputs" / "figures").mkdir(parents=True)
    (run_1 / "outputs" / "figures" / "overview.html").write_text("<html>overview-1</html>", encoding="utf-8")
    (run_1 / "outputs" / "figures" / "temperature.html").write_text("<html>temperature-1</html>", encoding="utf-8")
    (run_2 / "outputs" / "figures" / "overview.html").write_text("<html>overview-2</html>", encoding="utf-8")
    (run_2 / "outputs" / "figures" / "temperature.html").write_text("<html>temperature-2</html>", encoding="utf-8")
    (run_1 / "state.yaml").write_text("components: []\nmaterials: {}\n", encoding="utf-8")
    (run_1 / "next_state.yaml").write_text("components: []\nmaterials: {}\n", encoding="utf-8")

    _write_json(
        run_1 / "evaluation.json",
        {
            "feasible": False,
            "violations": [{"name": "chip_max_temperature", "limit": 85.0, "actual": 89.3}],
            "temperature_max": 89.3,
            "objective_summary": {"chip_max_temperature": 89.3},
        },
    )
    _write_json(
        run_1 / "proposal.json",
        {
            "decision_summary": "switch to base conductivity",
            "changes": [
                {
                    "path": "materials.base_material.conductivity",
                    "action": "set",
                    "old": 12.0,
                    "new": 24.0,
                    "reason": "open the heat path to the cold boundaries",
                }
            ],
            "expected_effects": ["lower chip max temperature"],
            "risk_notes": ["may still need another step"],
            "model_info": {"provider": "dashscope", "model": "qwen3.5-plus"},
        },
    )
    _write_json(run_1 / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_1 / "decision.json", {"iteration": 1, "status": "proposal_applied"})

    _write_json(
        run_2 / "evaluation.json",
        {
            "feasible": True,
            "temperature_max": 58.6,
            "objective_summary": {"chip_max_temperature": 58.6},
        },
    )
    _write_json(run_2 / "proposal.json", {"decision_summary": "hold", "changes": []})
    _write_json(run_2 / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_2 / "decision.json", {"iteration": 2, "status": "feasible"})

    summary = collect_history_summary(tmp_path)

    first_run = summary["runs"][0]
    assert first_run["iteration"] == 1
    assert first_run["constraint_limit"] == 85.0
    assert first_run["chip_max_before"] == 89.3
    assert first_run["chip_max_after"] == 58.6
    assert first_run["delta_chip_max"] == -30.700000000000003
    assert first_run["expected_effects"] == ["lower chip max temperature"]
    assert first_run["risk_notes"] == ["may still need another step"]
    assert first_run["changes"][0]["reason"] == "open the heat path to the cold boundaries"
    assert first_run["state_path"].endswith("state.yaml")
    assert first_run["next_state_path"].endswith("next_state.yaml")
    assert first_run["effect_observed_in_run"] == "run_0002"
    assert first_run["next_overview_html"].endswith("overview.html")
