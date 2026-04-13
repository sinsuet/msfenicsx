from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

from core.generator.layout_metrics import build_layout_context, measure_layout_quality
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


def test_render_case_page_surfaces_layout_realism_metrics_from_case_provenance(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"
    case_path = representative_root / "case.yaml"
    case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    case_payload["provenance"] = {
        "layout_metrics": {
            "active_deck_occupancy": 0.401,
            "bbox_fill_ratio": 0.392,
            "nearest_neighbor_gap_mean": 0.011,
        }
    }
    case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

    output_path = render_case_page(representative_root)
    html = output_path.read_text(encoding="utf-8")

    assert "Active Deck Occupancy" in html
    assert "BBox Fill Ratio" in html
    assert "0.401" in html


def test_render_case_page_recomputes_layout_metrics_from_representative_case_geometry(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"
    case_path = representative_root / "case.yaml"
    case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    case_payload["panel_domain"] = {"width": 1.0, "height": 0.8}
    case_payload["components"] = [
        {
            "component_id": "c01-001",
            "role": "logic_board_01",
            "shape": "rect",
            "pose": {"x": 0.25, "y": 0.25, "rotation_deg": 0.0},
            "geometry": {"width": 0.12, "height": 0.09},
            "material_ref": "electronics_housing",
        },
        {
            "component_id": "c02-001",
            "role": "logic_board_02",
            "shape": "rect",
            "pose": {"x": 0.62, "y": 0.50, "rotation_deg": 0.0},
            "geometry": {"width": 0.14, "height": 0.10},
            "material_ref": "electronics_housing",
        },
    ]
    template_payload = yaml.safe_load(Path("/home/hymn/msfenicsx/scenarios/templates/s1_typical.yaml").read_text(encoding="utf-8"))
    case_payload["provenance"] = {
        "source_template_id": "s1_typical",
        "layout_context": build_layout_context(
            placement_region=template_payload["placement_regions"][0],
            active_deck=template_payload["generation_rules"]["layout_strategy"]["zones"]["active_deck"],
            dense_core=template_payload["generation_rules"]["layout_strategy"]["zones"].get("dense_core"),
        ),
        "layout_metrics": {
            "active_deck_occupancy": 0.999,
            "bbox_fill_ratio": 0.999,
            "nearest_neighbor_gap_mean": 0.999,
        },
    }
    case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

    expected_metrics = measure_layout_quality(
        case_payload,
        placement_region=template_payload["placement_regions"][0],
        active_deck=template_payload["generation_rules"]["layout_strategy"]["zones"]["active_deck"],
    )

    output_path = render_case_page(representative_root)
    html = output_path.read_text(encoding="utf-8")

    assert f"{expected_metrics.bbox_fill_ratio:.3f}" in html
    assert "0.999" not in html


def test_render_case_page_surfaces_background_cooling_and_heat_source_counts(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    output_path = render_case_page(representative_root)
    html = output_path.read_text(encoding="utf-8")

    assert "Ambient Temperature" in html
    assert "Background Boundary Cooling" in html
    assert "Active Heat Sources" in html
