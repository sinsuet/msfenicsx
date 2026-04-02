from __future__ import annotations

from pathlib import Path

from tests.optimizers.experiment_fixtures import create_mode_root_with_seed_bundles
from visualization.case_pages import render_case_page


def test_render_case_page_writes_layout_temperature_and_gradient_sections(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    output_path = render_case_page(representative_root)
    html = output_path.read_text(encoding="utf-8")
    layout_svg = (representative_root / "figures" / "layout.svg").read_text(encoding="utf-8")

    assert output_path.exists()
    assert "Temperature Field" in html
    assert "Gradient Magnitude" in html
    assert "Constraint Margins" in html
    assert "figures/layout.svg" in html
    assert (representative_root / "figures" / "layout.svg").exists()
    assert "<polygon" in layout_svg
