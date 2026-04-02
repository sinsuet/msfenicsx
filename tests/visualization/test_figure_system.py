from __future__ import annotations

import importlib.util
import xml.etree.ElementTree as ET


def test_scientific_figure_canvas_uses_white_background() -> None:
    assert importlib.util.find_spec("visualization.figure_theme") is not None

    from visualization.figure_theme import build_scientific_canvas

    svg = build_scientific_canvas(title="demo", width=800, height=600, body="")

    assert "fill='#ffffff'" in svg.lower()


def test_wrap_text_lines_respect_width_and_max_lines() -> None:
    assert importlib.util.find_spec("visualization.figure_text") is not None

    from visualization.figure_text import wrap_text_lines

    lines = wrap_text_lines(
        "c01-001: x=[0.27, 0.35], y=[0.61, 0.67]",
        max_chars=18,
        max_lines=2,
    )

    assert len(lines) == 2
    assert lines[-1].endswith("...")


def test_render_colorbar_panel_writes_scale_labels() -> None:
    assert importlib.util.find_spec("visualization.figure_axes") is not None

    from visualization.figure_axes import render_colorbar_panel

    svg = render_colorbar_panel(
        title="Temperature",
        value_min=300.0,
        value_max=305.0,
        x=0.0,
        y=0.0,
        width=60.0,
        height=220.0,
    )

    assert "300.000" in svg
    assert "305.000" in svg


def test_svg_text_escapes_font_family_for_valid_xml() -> None:
    from visualization.static_assets import svg_text

    payload = (
        "<svg xmlns='http://www.w3.org/2000/svg'>"
        + svg_text(
            10.0,
            20.0,
            "demo",
            font_family="Arial, Helvetica, 'DejaVu Sans', sans-serif",
        )
        + "</svg>"
    )

    ET.fromstring(payload)
