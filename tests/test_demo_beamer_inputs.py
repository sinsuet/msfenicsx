from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from orchestration.demo_beamer import build_demo_beamer


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_demo_beamer_inputs_builder_exports_required_sections(tmp_path):
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
                    "validation_status": "valid",
                    "changed_paths": ["materials.spreader_material.conductivity"],
                    "change_categories": ["material"],
                    "llm_decision_summary": "increase spreader conductivity",
                }
            ]
        },
    )

    tex_path = tmp_path / "slides" / "demo_workflow_beamer.tex"
    result = build_demo_beamer(runs_root=runs_root, output_path=tex_path)
    beamer_source = tex_path.read_text(encoding="utf-8")

    assert Path(result["tex_path"]).exists()
    assert "问题定义" in beamer_source
    assert "ZhaochengLi" in beamer_source
    assert "中科院微小卫星创新院" in beamer_source
    assert "整体 workflow" in beamer_source
    assert "LLM 可修改参数：材料与载荷" in beamer_source
    assert "物理模型与数学形式" in beamer_source
    assert "代表性单跑：15轮温度轨迹" in beamer_source
    assert "代表性单跑：LLM 在关键轮次看到了什么" in beamer_source
    assert "代表性单跑：为什么会切换到 base\\_k" in beamer_source
    assert "代表性单跑：关键 proposal 与执行动作" in beamer_source
    assert "代表性单跑：关键动作兑现后的效果" in beamer_source
    assert "10组 15轮正式实验：全组轨迹" in beamer_source
    assert "第一次使用 base\\_k 的轮次" in beamer_source
    assert "官方 10 轮总体趋势" not in beamer_source
