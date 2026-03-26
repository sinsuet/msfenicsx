from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from orchestration.demo_figures import build_demo_figures


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_demo_figures_builder_generates_trend_pngs(tmp_path):
    runs_root = tmp_path / "official_10_iter"
    _write_json(
        runs_root / "demo_summary.json",
        {
            "runs": [
                {
                    "run_id": "run_0001",
                    "iteration": 1,
                    "chip_max_before": 89.3,
                    "chip_max_after": 88.7,
                    "delta_chip_max": -0.6,
                    "change_categories": ["material"],
                },
                {
                    "run_id": "run_0002",
                    "iteration": 2,
                    "chip_max_before": 88.7,
                    "chip_max_after": 88.2,
                    "delta_chip_max": -0.5,
                    "change_categories": ["geometry", "material"],
                },
            ]
        },
    )

    result = build_demo_figures(runs_root)
    figures_dir = runs_root / "figures"

    assert (figures_dir / "chip_max_trend.png").exists()
    assert (figures_dir / "delta_trend.png").exists()
    assert (figures_dir / "category_timeline.png").exists()
    assert Path(result["chip_max_trend"]).exists()
