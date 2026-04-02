from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from tests.optimizers.experiment_fixtures import create_mixed_run_root, create_mode_root_with_seed_bundles
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
    assert "Component Thermal Table" in html
    assert "Solver Diagnostics" in html
    assert "figures/layout.svg" in html
    assert "figures/temperature-field.svg" in html
    assert "figures/gradient-field.svg" in html
    assert (representative_root / "figures" / "layout.svg").exists()
    assert (representative_root / "figures" / "temperature-field.svg").exists()
    assert (representative_root / "figures" / "gradient-field.svg").exists()
    assert "<polygon" in layout_svg


def test_render_case_page_includes_comparison_navigation_when_run_has_comparison_root(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11,))
    representative_root = run_root / "raw" / "seeds" / "seed-11" / "representatives" / "knee"

    output_path = render_case_page(representative_root)
    html = output_path.read_text(encoding="utf-8")

    assert "Mode Overview" in html
    assert "Comparison Overview" in html
    assert "comparison/pages/index.html" in html


def test_layout_figure_uses_white_background_and_compact_legend(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    render_case_page(representative_root)
    svg = (representative_root / "figures" / "layout.svg").read_text(encoding="utf-8").lower()

    assert "fill='#ffffff'" in svg
    assert "legend" in svg


def test_layout_figure_moves_geometry_notes_out_of_svg(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    render_case_page(representative_root)
    svg = (representative_root / "figures" / "layout.svg").read_text(encoding="utf-8")
    html = (representative_root / "pages" / "index.html").read_text(encoding="utf-8")

    assert "Geometry Notes" not in svg
    assert "Component Thermal Table" in html


def test_field_figures_use_colorbars_and_white_background(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    render_case_page(representative_root)
    temperature_svg = (representative_root / "figures" / "temperature-field.svg").read_text(encoding="utf-8").lower()
    gradient_svg = (representative_root / "figures" / "gradient-field.svg").read_text(encoding="utf-8").lower()

    assert "fill='#ffffff'" in temperature_svg
    assert "colorbar" in temperature_svg
    assert "colorbar" in gradient_svg


def test_field_figures_do_not_embed_long_reading_guides(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    render_case_page(representative_root)
    svg = (representative_root / "figures" / "temperature-field.svg").read_text(encoding="utf-8")
    html = (representative_root / "pages" / "index.html").read_text(encoding="utf-8")

    assert "Interpretation" not in svg
    assert "Temperature Field" in html


def test_field_figure_svg_is_valid_xml(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    render_case_page(representative_root)
    svg = (representative_root / "figures" / "temperature-field.svg").read_text(encoding="utf-8")

    ET.fromstring(svg)
