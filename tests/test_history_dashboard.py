from pathlib import Path
import importlib.util
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_example_module():
    example_path = ROOT / "examples" / "04_build_history_dashboard.py"
    spec = importlib.util.spec_from_file_location("history_dashboard_example", example_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_history_dashboard_builder_generates_html_and_summary(tmp_path):
    run_dir = tmp_path / "run_0001"
    (run_dir / "outputs" / "figures").mkdir(parents=True)
    (run_dir / "outputs" / "figures" / "overview.html").write_text("<html>overview</html>", encoding="utf-8")
    (run_dir / "outputs" / "figures" / "temperature.html").write_text("<html>temperature</html>", encoding="utf-8")
    (run_dir / "state.yaml").write_text("components: []\nmaterials: {}\n", encoding="utf-8")
    _write_json(
        run_dir / "evaluation.json",
        {
            "feasible": False,
            "temperature_max": 0.2572,
            "objective_summary": {"chip_max_temperature": 0.2572},
        },
    )
    _write_json(
        run_dir / "proposal.json",
        {
            "decision_summary": "increase spreader conductivity",
            "changes": [
                {
                    "path": "materials.spreader_material.conductivity",
                    "old": 90.0,
                    "new": 135.0,
                    "reason": "improve lateral spreading",
                }
            ],
            "expected_effects": ["lower chip max temperature"],
            "risk_notes": ["may saturate quickly"],
            "model_info": {"provider": "dashscope", "model": "qwen3.5-plus"},
        },
    )
    _write_json(run_dir / "proposal_validation.json", {"valid": True, "reasons": []})
    _write_json(run_dir / "decision.json", {"iteration": 1, "status": "proposal_applied"})

    module = _load_example_module()
    result = module.run_example(runs_root=tmp_path)

    history_html = Path(result["history_html"])
    history_summary = Path(result["history_summary"])

    assert history_html.exists()
    assert history_summary.exists()

    html_text = history_html.read_text(encoding="utf-8")
    assert "run_0001" in html_text
    assert "chip_max_temperature" in html_text
    assert "proposal_applied" in html_text
    assert "lower chip max temperature" in html_text
    assert "improve lateral spreading" in html_text


def test_history_dashboard_builder_generates_group_index_for_grouped_runs(tmp_path):
    group_01_run = tmp_path / "group_01" / "run_0001"
    group_02_run = tmp_path / "group_02" / "run_0001"

    for run_dir, chip_max in ((group_01_run, 89.3), (group_02_run, 58.6)):
        (run_dir / "outputs" / "figures").mkdir(parents=True)
        (run_dir / "outputs" / "figures" / "overview.html").write_text("<html>overview</html>", encoding="utf-8")
        (run_dir / "outputs" / "figures" / "temperature.html").write_text("<html>temperature</html>", encoding="utf-8")
        (run_dir / "state.yaml").write_text("components: []\nmaterials: {}\n", encoding="utf-8")
        _write_json(
            run_dir / "evaluation.json",
            {
                "feasible": chip_max <= 85.0,
                "temperature_max": chip_max,
                "objective_summary": {"chip_max_temperature": chip_max},
            },
        )
        _write_json(
            run_dir / "proposal.json",
            {
                "decision_summary": "single step",
                "changes": [{"path": "materials.base_material.conductivity", "new": 24.0}],
            },
        )
        _write_json(run_dir / "proposal_validation.json", {"valid": True, "reasons": []})
        _write_json(run_dir / "decision.json", {"iteration": 1, "status": "proposal_applied"})

    module = _load_example_module()
    result = module.run_example(runs_root=tmp_path)

    history_html = Path(result["history_html"])
    history_summary = Path(result["history_summary"])

    assert history_html.exists()
    assert history_summary.exists()
    assert (tmp_path / "group_01" / "history.html").exists()
    assert (tmp_path / "group_02" / "history.html").exists()

    html_text = history_html.read_text(encoding="utf-8")
    assert "group_01" in html_text
    assert "group_02" in html_text
    assert "Thermal Optimization History Collection" in html_text
