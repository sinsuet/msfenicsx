from pathlib import Path
import sys

import numpy as np
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from msfenicsx_viz import default_component_layout, summarize_values_by_component


def test_default_component_layout_contains_expected_regions():
    layout = default_component_layout()
    assert [part.name for part in layout] == ["base_plate", "chip", "heat_spreader"]


def test_component_summary_returns_min_max_mean():
    names = ["base_plate", "chip", "heat_spreader"]
    labels = np.array([1, 1, 2, 2, 3, 3], dtype=np.int32)
    values = np.array([0.1, 0.2, 0.8, 0.9, 0.4, 0.6], dtype=float)

    summary = summarize_values_by_component(names, labels, values)

    assert summary["base_plate"]["min"] == 0.1
    assert summary["base_plate"]["max"] == 0.2
    assert np.isclose(summary["chip"]["mean"], 0.85)
    assert summary["heat_spreader"]["count"] == 2


def test_multicomponent_example_generates_visual_outputs(tmp_path):
    example_path = ROOT / "examples" / "02_multicomponent_steady_heat.py"
    spec = importlib.util.spec_from_file_location("multicomponent_example", example_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    result = module.run_example(output_root=tmp_path, nx=12, ny=6)

    expected_files = [
        result["layout_png"],
        result["mesh_png"],
        result["subdomains_png"],
        result["temperature_png"],
        result["temperature_html"],
        result["overview_html"],
        result["summary_txt"],
    ]
    for path in expected_files:
        assert Path(path).exists()

    summary_text = Path(result["summary_txt"]).read_text(encoding="utf-8")
    assert "base_plate" in summary_text
    assert "chip" in summary_text
    assert "heat_spreader" in summary_text

    overview_text = Path(result["overview_html"]).read_text(encoding="utf-8")
    assert "Physics" in overview_text
    assert "base_plate" in overview_text
    assert "heat_spreader" in overview_text
    assert "Cold boundaries" in overview_text
