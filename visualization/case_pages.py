"""Single-case page renderers for representative thermal bundles."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from core.generator.layout_metrics import build_layout_context, measure_case_layout_metrics
from visualization.figure_axes import render_colorbar_panel
from visualization.figure_text import wrap_text_lines
from visualization.figure_theme import SCIENTIFIC_COLORS, SCIENTIFIC_FONT_FAMILY, build_scientific_canvas
from visualization.static_assets import (
    dashboard_style,
    html_metric_grid,
    html_section,
    html_table,
    load_json,
    svg_circle,
    svg_line,
    svg_polygon,
    svg_rect,
    svg_text,
    write_dashboard,
    write_svg,
)

_THERMAL_PALETTE = (
    (33, 64, 95),
    (96, 141, 120),
    (233, 183, 109),
    (181, 84, 56),
)
_GRADIENT_PALETTE = (
    (29, 53, 87),
    (82, 123, 184),
    (145, 187, 222),
    (230, 147, 97),
)
_CONTOUR_CASES = {
    0: (),
    1: (("bottom", "left"),),
    2: (("right", "bottom"),),
    3: (("right", "left"),),
    4: (("top", "right"),),
    5: (("top", "left"), ("right", "bottom")),
    6: (("top", "bottom"),),
    7: (("top", "left"),),
    8: (("top", "left"),),
    9: (("top", "bottom"),),
    10: (("top", "right"), ("bottom", "left")),
    11: (("top", "right"),),
    12: (("right", "left"),),
    13: (("right", "bottom"),),
    14: (("bottom", "left"),),
    15: (),
}


def render_case_page(representative_root: str | Path) -> Path:
    root = Path(representative_root)
    field_view = load_json(root / "summaries" / "field_view.json")
    case_payload = _load_yaml(root / "case.yaml")
    solution_payload = _load_yaml(root / "solution.yaml")
    evaluation_payload = _load_yaml(root / "evaluation.yaml") if (root / "evaluation.yaml").exists() else {}
    case_id = str(case_payload.get("case_meta", {}).get("case_id", root.name))
    representative_id = root.name
    figures_root = root / "figures"
    temperature_grid = _load_grid(root / "fields" / "temperature_grid.npz")
    gradient_grid = _load_grid(root / "fields" / "gradient_magnitude_grid.npz")

    write_svg(figures_root / "layout.svg", _render_layout_figure(case_id, field_view, solution_payload, case_payload))
    write_svg(
        figures_root / "temperature-field.svg",
        _render_field_figure(
            title=f"{case_id} Temperature Field",
            values=temperature_grid,
            field_payload=dict(field_view.get("temperature", {})),
            field_view=field_view,
            case_payload=case_payload,
            palette=_THERMAL_PALETTE,
            hotspot=dict(field_view.get("temperature", {}).get("hotspot", {})),
            show_contours=False,
        ),
    )
    write_svg(
        figures_root / "temperature-contours.svg",
        _render_field_figure(
            title=f"{case_id} Temperature Contours",
            values=temperature_grid,
            field_payload=dict(field_view.get("temperature", {})),
            field_view=field_view,
            case_payload=case_payload,
            palette=_THERMAL_PALETTE,
            hotspot=dict(field_view.get("temperature", {}).get("hotspot", {})),
            show_contours=True,
        ),
    )
    write_svg(
        figures_root / "gradient-field.svg",
        _render_field_figure(
            title=f"{case_id} Gradient Magnitude",
            values=gradient_grid,
            field_payload=dict(field_view.get("gradient_magnitude", {})),
            field_view=field_view,
            case_payload=case_payload,
            palette=_GRADIENT_PALETTE,
            hotspot={},
            show_contours=False,
        ),
    )

    layout_component_rows = _build_layout_component_rows(field_view)
    sink_rows = _build_sink_rows(field_view)
    layout_metric_rows = _build_layout_metric_rows(case_payload)
    component_rows = _build_component_rows(solution_payload, field_view)
    global_metric_rows = _build_metric_rows(solution_payload, evaluation_payload)
    constraint_rows = _build_constraint_rows(evaluation_payload)
    diagnostic_rows = _build_diagnostic_rows(case_payload, solution_payload, evaluation_payload)

    output_path = root / "pages" / "index.html"
    mode_page_href = _relative_href(output_path.parent, root.parents[3] / "pages" / "index.html")
    comparison_root = root.parents[4] / "comparison"
    comparison_index = comparison_root / "pages" / "index.html"
    comparison_progress = comparison_root / "pages" / "progress.html"
    links = [f"<a href='{mode_page_href}'>Mode Overview</a>"]
    if comparison_root.is_dir():
        links.append(f"<a href='{_relative_href(output_path.parent, comparison_index)}'>Comparison Overview</a>")
        links.append(f"<a href='{_relative_href(output_path.parent, comparison_progress)}'>Comparison Progress</a>")

    body = (
        "<main>"
        f"<section class='hero'><h1>{case_id} / {representative_id}</h1>"
        "<p>Single-case physical-field view for the representative solution bundle.</p>"
        + html_metric_grid(
            [
                ("Peak Temperature", _format_scalar(solution_payload.get("summary_metrics", {}).get("temperature_max"))),
                (
                    "Gradient RMS",
                    _format_scalar(solution_payload.get("summary_metrics", {}).get("temperature_gradient_rms")),
                ),
                ("Feasible", _format_bool(evaluation_payload.get("feasible"))),
                ("Hotspot", _format_hotspot(field_view.get("temperature", {}).get("hotspot", {}))),
            ]
        )
        + "</section>"
        + html_section(
            "Layout View",
            _figure_grid(
                [
                    ("../figures/layout.svg", "Real component footprints, sink span, and hotspot reference in panel coordinates."),
                ]
            )
            + html_table(
                ["Layout Metric", "Value"],
                layout_metric_rows or [["No layout metrics", "n/a"]],
            )
            + html_table(
                ["Component", "Bounds"],
                layout_component_rows or [["No components", "n/a"]],
            )
            + html_table(
                ["Sink", "Edge"],
                sink_rows or [["No sinks", "n/a"]],
            ),
        )
        + html_section(
            "Temperature Field",
            _figure_grid(
                [
                    ("../figures/temperature-field.svg", "Temperature raster with shared domain coordinates and component overlay."),
                ]
            )
            + html_metric_grid(
                [
                    ("Grid Shape", _format_grid_shape(field_view.get("temperature", {}).get("grid_shape"))),
                    ("Min", _format_scalar(field_view.get("temperature", {}).get("min"))),
                    ("Max", _format_scalar(field_view.get("temperature", {}).get("max"))),
                ]
            ),
        )
        + html_section(
            "Temperature Contour Overlay",
            _figure_grid(
                [
                    ("../figures/temperature-contours.svg", "Contour levels overlaid on the sampled temperature field."),
                ]
            ),
        )
        + html_section(
            "Gradient Magnitude",
            _figure_grid(
                [
                    ("../figures/gradient-field.svg", "Gradient magnitude raster over the same panel domain for direct comparison."),
                ]
            )
            + html_metric_grid(
                [
                    ("Grid Shape", _format_grid_shape(field_view.get("gradient_magnitude", {}).get("grid_shape"))),
                    ("Min", _format_scalar(field_view.get("gradient_magnitude", {}).get("min"))),
                    ("Max", _format_scalar(field_view.get("gradient_magnitude", {}).get("max"))),
                ]
            ),
        )
        + html_section(
            "Component Thermal Table",
            html_table(
                ["Component", "Bounds", "Temp Min", "Temp Mean", "Temp Max"],
                component_rows or [["No components", "", "n/a", "n/a", "n/a"]],
            ),
        )
        + html_section(
            "Global Metrics",
            html_table(["Metric", "Value"], global_metric_rows or [["No metrics", "n/a"]]),
        )
        + html_section(
            "Constraint Margins",
            html_table(
                ["Constraint", "Relation", "Actual", "Limit", "Margin", "Satisfied"],
                constraint_rows or [["No constraints", "", "", "", "", ""]],
            ),
        )
        + html_section(
            "Solver Diagnostics",
            html_table(["Signal", "Value"], diagnostic_rows or [["No diagnostics", "n/a"]]),
        )
        + html_section(
            "Links",
            "<div class='inline-links'>" + "".join(links) + "</div>",
        )
        + "</main>"
    )
    return write_dashboard(output_path, f"{case_id} Case Page", body, style=dashboard_style())


def _render_layout_figure(
    case_id: str,
    field_view: dict[str, Any],
    solution_payload: dict[str, Any],
    case_payload: dict[str, Any],
) -> str:
    width = 980
    height = 620
    frame_x = 60.0
    frame_y = 104.0
    frame_width = 720.0
    frame_height = 470.0
    domain_width, domain_height = _resolve_panel_domain(field_view, case_payload)
    layout = dict(field_view.get("layout", {}))
    components = list(layout.get("components", []))
    line_sinks = list(layout.get("line_sinks", []))
    hotspot = dict(field_view.get("temperature", {}).get("hotspot", {}))
    parts = [
        svg_text(
            60.0,
            40.0,
            f"{case_id} layout",
            fill=SCIENTIFIC_COLORS["ink"],
            size=24,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            60.0,
            64.0,
            (
                f"Components: {len(components)}   "
                f"Sinks: {len(line_sinks)}   "
                f"Domain: {domain_width:.2f} x {domain_height:.2f}   "
                f"Peak: {_format_scalar(solution_payload.get('summary_metrics', {}).get('temperature_max'))}"
            ),
            fill=SCIENTIFIC_COLORS["muted"],
            size=12,
            weight="500",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            808.0,
            42.0,
            "Legend",
            fill=SCIENTIFIC_COLORS["ink"],
            size=13,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_rect(frame_x, frame_y, frame_width, frame_height, fill="#ffffff", stroke="#9a9a9a", stroke_width=1.2, rx=6.0),
    ]
    parts.extend(_render_layout_legend())
    parts.extend(_render_layout_overlay(components, line_sinks, hotspot, domain_width, domain_height, frame_x, frame_y, frame_width, frame_height))
    return build_scientific_canvas(
        title=f"{case_id} layout",
        width=width,
        height=height,
        body="".join(parts),
    )


def _render_field_figure(
    *,
    title: str,
    values: np.ndarray | None,
    field_payload: dict[str, Any],
    field_view: dict[str, Any],
    case_payload: dict[str, Any],
    palette: tuple[tuple[int, int, int], ...],
    hotspot: dict[str, Any],
    show_contours: bool,
) -> str:
    width = 980
    height = 680
    frame_x = 72.0
    frame_y = 120.0
    frame_width = 620.0
    frame_height = 500.0
    inset = 12.0
    domain_width, domain_height = _resolve_panel_domain(field_view, case_payload)
    sampled = _downsample_grid(values, max_rows=36, max_cols=42) if values is not None else None
    value_min = (
        float(field_payload.get("min"))
        if field_payload.get("min") is not None
        else float(np.min(sampled))
        if sampled is not None
        else 0.0
    )
    value_max = (
        float(field_payload.get("max"))
        if field_payload.get("max") is not None
        else float(np.max(sampled))
        if sampled is not None
        else 0.0
    )
    annotation_rows = _build_field_annotation_rows(
        field_payload=field_payload,
        domain_width=domain_width,
        domain_height=domain_height,
        hotspot=hotspot,
        show_contours=show_contours,
    )
    parts = [
        svg_text(
            72.0,
            42.0,
            title,
            fill=SCIENTIFIC_COLORS["ink"],
            size=24,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            72.0,
            66.0,
            "Shared panel coordinates with component, sink, and hotspot overlays.",
            fill=SCIENTIFIC_COLORS["muted"],
            size=12,
            weight="500",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            frame_x,
            96.0,
            "Field Map",
            fill=SCIENTIFIC_COLORS["ink"],
            size=13,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            752.0,
            96.0,
            "Scale and Annotations",
            fill=SCIENTIFIC_COLORS["ink"],
            size=13,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_rect(
            frame_x,
            frame_y,
            frame_width,
            frame_height,
            fill="#ffffff",
            stroke=SCIENTIFIC_COLORS["panel_stroke"],
            stroke_width=1.2,
            rx=6.0,
        ),
    ]
    if sampled is None:
        parts.append(
            svg_text(
                frame_x + frame_width / 2.0,
                frame_y + frame_height / 2.0,
                "No sampled grid available for this bundle.",
                fill=SCIENTIFIC_COLORS["muted"],
                size=15,
                weight="500",
                anchor="middle",
                font_family=SCIENTIFIC_FONT_FAMILY,
            )
        )
    else:
        parts.append(
            _render_heatmap_cells(
                sampled,
                x=frame_x + inset,
                y=frame_y + inset,
                width=frame_width - 2.0 * inset,
                height=frame_height - 2.0 * inset,
                palette=palette,
                value_min=value_min,
                value_max=value_max,
            )
        )
        if show_contours:
            parts.append(
                _render_contours(
                    sampled,
                    levels=[float(level) for level in field_payload.get("contour_levels", [])],
                    x=frame_x + inset,
                    y=frame_y + inset,
                    width=frame_width - 2.0 * inset,
                    height=frame_height - 2.0 * inset,
                )
            )
    parts.extend(
        _render_layout_overlay(
            list(dict(field_view.get("layout", {})).get("components", [])),
            list(dict(field_view.get("layout", {})).get("line_sinks", [])),
            hotspot,
            domain_width,
            domain_height,
            frame_x,
            frame_y,
            frame_width,
            frame_height,
            stroke_only=True,
        )
    )
    parts.extend(
        [
            svg_text(
                frame_x,
                frame_y + frame_height + 28.0,
                "x = 0.00",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            svg_text(
                frame_x + frame_width,
                frame_y + frame_height + 28.0,
                f"x = {domain_width:.2f}",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                anchor="end",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            svg_text(
                frame_x - 12.0,
                frame_y + frame_height + 4.0,
                "y = 0.00",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                anchor="end",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            svg_text(
                frame_x - 12.0,
                frame_y + 4.0,
                f"y = {domain_height:.2f}",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                anchor="end",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
        ]
    )
    parts.append(
        render_colorbar_panel(
            title=_field_scale_title(title),
            value_min=value_min,
            value_max=value_max,
            x=752.0,
            y=132.0,
            width=132.0,
            height=250.0,
        )
    )
    parts.extend(_render_field_overlay_legend(752.0, 414.0, include_hotspot=bool(hotspot)))
    parts.append(
        svg_text(
            752.0,
            508.0,
            "Summary",
            fill=SCIENTIFIC_COLORS["ink"],
            size=13,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        )
    )
    for index, row in enumerate(annotation_rows):
        parts.append(
            svg_text(
                752.0,
                532.0 + float(index) * 18.0,
                row,
                fill=SCIENTIFIC_COLORS["muted"],
                size=12,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            )
        )
    return build_scientific_canvas(
        title=title,
        width=width,
        height=height,
        body="".join(parts),
    )


def _field_scale_title(title: str) -> str:
    lower_title = title.lower()
    if "gradient" in lower_title:
        return "Gradient"
    if "temperature" in lower_title:
        return "Temperature"
    return "Field"


def _build_field_annotation_rows(
    *,
    field_payload: dict[str, Any],
    domain_width: float,
    domain_height: float,
    hotspot: dict[str, Any],
    show_contours: bool,
) -> list[str]:
    rows = [
        f"Domain {domain_width:.2f} x {domain_height:.2f}",
        f"Grid {_format_grid_shape(field_payload.get('grid_shape'))}",
        f"Range {_format_scalar(field_payload.get('min'))} to {_format_scalar(field_payload.get('max'))}",
    ]
    if hotspot:
        rows.append(f"Hotspot {_format_hotspot(hotspot)}")
        if hotspot.get("value") is not None:
            rows.append(f"Peak {_format_scalar(hotspot.get('value'))}")
    if show_contours:
        contour_values = ", ".join(_format_scalar(level) for level in field_payload.get("contour_levels", [])[:4])
        if contour_values:
            rows.extend(wrap_text_lines(f"Contours {contour_values}", max_chars=28, max_lines=2))
    return rows[:6]


def _render_field_overlay_legend(x: float, y: float, *, include_hotspot: bool) -> list[str]:
    items = [
        ("component footprint", "footprint"),
        ("sink boundary", "line"),
    ]
    if include_hotspot:
        items.append(("hotspot", "spot"))
    parts: list[str] = [
        svg_text(
            x,
            y,
            "Overlay",
            fill=SCIENTIFIC_COLORS["ink"],
            size=13,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        )
    ]
    for index, (label, kind) in enumerate(items):
        row_y = y + 26.0 + float(index) * 20.0
        if kind == "footprint":
            parts.append(svg_polygon(_legend_footprint_points(x, row_y - 6.0), fill="none", stroke="#7b3b27", stroke_width=1.4))
        elif kind == "line":
            parts.append(svg_line(x, row_y - 5.0, x + 16.0, row_y - 5.0, stroke="#2a9d8f", stroke_width=3.0))
        else:
            parts.append(svg_circle(x + 8.0, row_y - 5.0, 5.0, fill="#ffffff", stroke="#6f1d1b", stroke_width=1.6))
            parts.append(svg_circle(x + 8.0, row_y - 5.0, 1.8, fill="#6f1d1b"))
        parts.append(
            svg_text(
                x + 24.0,
                row_y,
                label,
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            )
        )
    return parts


def _render_layout_legend() -> list[str]:
    legend_x = 808.0
    base_y = 58.0
    items = [
        ("component footprint", "#d7b29d", "#7b3b27", "footprint"),
        ("sink", "#2a9d8f", "#2a9d8f", "line"),
        ("hotspot", "#ffffff", "#6f1d1b", "spot"),
    ]
    parts: list[str] = []
    for index, (label, fill, stroke, kind) in enumerate(items):
        row_y = base_y + float(index) * 20.0
        if kind == "footprint":
            parts.append(svg_polygon(_legend_footprint_points(legend_x, row_y - 5.0), fill=fill, stroke=stroke, stroke_width=1.2))
        elif kind == "line":
            parts.append(svg_line(legend_x, row_y - 4.0, legend_x + 16.0, row_y - 4.0, stroke=stroke, stroke_width=3.0))
        else:
            parts.append(svg_circle(legend_x + 8.0, row_y - 4.0, 5.0, fill=fill, stroke=stroke, stroke_width=1.6))
            parts.append(svg_circle(legend_x + 8.0, row_y - 4.0, 1.8, fill=stroke))
        parts.append(
            svg_text(
                legend_x + 24.0,
                row_y,
                label,
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            )
        )
    return parts


def _render_heatmap_cells(
    values: np.ndarray,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    palette: tuple[tuple[int, int, int], ...],
    value_min: float | None,
    value_max: float | None,
) -> str:
    rows, cols = values.shape
    cell_width = width / float(max(1, cols))
    cell_height = height / float(max(1, rows))
    resolved_min = float(np.min(values)) if value_min is None else float(value_min)
    resolved_max = float(np.max(values)) if value_max is None else float(value_max)
    parts: list[str] = []
    for row in range(rows):
        for col in range(cols):
            parts.append(
                svg_rect(
                    x + float(col) * cell_width,
                    y + float(row) * cell_height,
                    cell_width + 0.2,
                    cell_height + 0.2,
                    fill=_color_for_value(float(values[row, col]), resolved_min, resolved_max, palette),
                )
            )
    return "".join(parts)


def _render_layout_overlay(
    components: list[dict[str, Any]],
    line_sinks: list[dict[str, Any]],
    hotspot: dict[str, Any],
    domain_width: float,
    domain_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
    *,
    stroke_only: bool = False,
) -> list[str]:
    parts: list[str] = []
    for component in components:
        bounds = dict(component.get("bounds", {}))
        outline = _project_outline(
            component,
            domain_width=domain_width,
            domain_height=domain_height,
            frame_x=frame_x,
            frame_y=frame_y,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        if outline:
            parts.append(
                svg_polygon(
                    outline,
                    fill="none" if stroke_only else "#b5543855",
                    stroke="#7b3b27",
                    stroke_width=1.6,
                )
            )
        else:
            x0, y0, width, height = _project_bounds(bounds, domain_width, domain_height, frame_x, frame_y, frame_width, frame_height)
            parts.append(
                svg_rect(
                    x0,
                    y0,
                    width,
                    height,
                    fill="none" if stroke_only else "#b5543855",
                    stroke="#7b3b27",
                    stroke_width=1.6,
                    rx=6.0,
                )
            )
        label = str(component.get("component_id", ""))
        if label:
            label_x, label_y = _project_label_point(bounds, domain_width, domain_height, frame_x, frame_y, frame_width, frame_height)
            parts.append(svg_text(label_x, label_y, label, fill="#2f4858", size=11, weight="700", anchor="middle"))
    for line_sink in line_sinks:
        parts.extend(_render_sink(line_sink, domain_width, domain_height, frame_x, frame_y, frame_width, frame_height))
    if hotspot:
        hotspot_x = frame_x + frame_width * (float(hotspot.get("x", 0.0)) / max(domain_width, 1e-9))
        hotspot_y = frame_y + frame_height * (1.0 - float(hotspot.get("y", 0.0)) / max(domain_height, 1e-9))
        parts.append(svg_circle(hotspot_x, hotspot_y, 7.5, fill="#fff8f0", stroke="#6f1d1b", stroke_width=2.0))
        parts.append(svg_circle(hotspot_x, hotspot_y, 2.5, fill="#6f1d1b"))
    return parts


def _render_sink(
    line_sink: dict[str, Any],
    domain_width: float,
    domain_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> list[str]:
    edge = str(line_sink.get("edge", "top"))
    sink_color = "#2a9d8f"
    stroke_width = 6.0
    if edge in {"top", "bottom"}:
        start_x = frame_x + frame_width * (float(line_sink.get("start_x", 0.0)) / max(domain_width, 1e-9))
        end_x = frame_x + frame_width * (float(line_sink.get("end_x", 0.0)) / max(domain_width, 1e-9))
        y = frame_y if edge == "top" else frame_y + frame_height
        return [svg_line(start_x, y, end_x, y, stroke=sink_color, stroke_width=stroke_width)]
    start_y = frame_y + frame_height * (1.0 - float(line_sink.get("start_y", 0.0)) / max(domain_height, 1e-9))
    end_y = frame_y + frame_height * (1.0 - float(line_sink.get("end_y", domain_height)) / max(domain_height, 1e-9))
    x = frame_x if edge == "left" else frame_x + frame_width
    return [svg_line(x, start_y, x, end_y, stroke=sink_color, stroke_width=stroke_width)]


def _render_contours(
    values: np.ndarray,
    *,
    levels: list[float],
    x: float,
    y: float,
    width: float,
    height: float,
) -> str:
    if values.shape[0] < 2 or values.shape[1] < 2 or not levels:
        return ""
    row_count = values.shape[0] - 1
    col_count = values.shape[1] - 1
    cell_width = width / float(max(1, col_count))
    cell_height = height / float(max(1, row_count))
    parts: list[str] = []
    for level_index, level in enumerate(levels[:6]):
        stroke = _color_for_ratio(level_index / float(max(1, len(levels) - 1)), _THERMAL_PALETTE)
        for row in range(row_count):
            for col in range(col_count):
                cell = (
                    float(values[row, col]),
                    float(values[row, col + 1]),
                    float(values[row + 1, col + 1]),
                    float(values[row + 1, col]),
                )
                code = (
                    (1 if cell[0] >= level else 0) * 8
                    + (1 if cell[1] >= level else 0) * 4
                    + (1 if cell[2] >= level else 0) * 2
                    + (1 if cell[3] >= level else 0)
                )
                for start_edge, end_edge in _CONTOUR_CASES[code]:
                    start_x, start_y = _edge_midpoint(start_edge, x, y, cell_width, cell_height, col, row)
                    end_x, end_y = _edge_midpoint(end_edge, x, y, cell_width, cell_height, col, row)
                    parts.append(svg_line(start_x, start_y, end_x, end_y, stroke=stroke, stroke_width=1.4))
    return "".join(parts)


def _edge_midpoint(
    edge: str,
    x: float,
    y: float,
    cell_width: float,
    cell_height: float,
    col: int,
    row: int,
) -> tuple[float, float]:
    left = x + float(col) * cell_width
    top = y + float(row) * cell_height
    if edge == "top":
        return (left + cell_width / 2.0, top)
    if edge == "right":
        return (left + cell_width, top + cell_height / 2.0)
    if edge == "bottom":
        return (left + cell_width / 2.0, top + cell_height)
    return (left, top + cell_height / 2.0)


def _build_component_rows(solution_payload: dict[str, Any], field_view: dict[str, Any]) -> list[list[str]]:
    rows_by_component = {
        str(row.get("component_id", "")): row
        for row in solution_payload.get("component_summaries", [])
        if row.get("component_id")
    }
    layout_components = {
        str(component.get("component_id", "")): component
        for component in dict(field_view.get("layout", {})).get("components", [])
        if component.get("component_id")
    }
    component_ids = sorted(set(rows_by_component) | set(layout_components))
    return [
        [
            component_id,
            _format_bounds(dict(layout_components.get(component_id, {}).get("bounds", {}))),
            _format_scalar(rows_by_component.get(component_id, {}).get("temperature_min")),
            _format_scalar(rows_by_component.get(component_id, {}).get("temperature_mean")),
            _format_scalar(rows_by_component.get(component_id, {}).get("temperature_max")),
        ]
        for component_id in component_ids
    ]


def _build_layout_component_rows(field_view: dict[str, Any]) -> list[list[str]]:
    components = list(dict(field_view.get("layout", {})).get("components", []))
    return [
        [
            str(component.get("component_id", "")),
            _format_bounds(dict(component.get("bounds", {}))),
        ]
        for component in components
    ]


def _build_layout_metric_rows(case_payload: dict[str, Any]) -> list[list[str]]:
    layout_metrics = _resolved_layout_metrics(case_payload)
    ordered_metrics = [
        ("Active Deck Occupancy", layout_metrics.get("active_deck_occupancy")),
        ("BBox Fill Ratio", layout_metrics.get("bbox_fill_ratio")),
        ("Nearest Neighbor Gap", layout_metrics.get("nearest_neighbor_gap_mean")),
        ("Centroid Dispersion", layout_metrics.get("centroid_dispersion")),
        ("Component Area Ratio", layout_metrics.get("component_area_ratio")),
        ("Largest Dense-Core Void", layout_metrics.get("largest_dense_core_void_ratio")),
    ]
    return [[label, _format_scalar(value)] for label, value in ordered_metrics if value is not None]


def _build_sink_rows(field_view: dict[str, Any]) -> list[list[str]]:
    line_sinks = list(dict(field_view.get("layout", {})).get("line_sinks", []))
    return [
        [
            str(line_sink.get("feature_id", "")),
            str(line_sink.get("edge", "")),
        ]
        for line_sink in line_sinks
    ]


def _build_metric_rows(solution_payload: dict[str, Any], evaluation_payload: dict[str, Any]) -> list[list[str]]:
    summary_metrics = dict(solution_payload.get("summary_metrics", {}))
    metric_values = dict(evaluation_payload.get("metric_values", {}))
    ordered_metrics = [
        ("summary.temperature_max", summary_metrics.get("temperature_max")),
        ("summary.temperature_gradient_rms", summary_metrics.get("temperature_gradient_rms")),
        ("summary.temperature_mean", summary_metrics.get("temperature_mean")),
        ("summary.temperature_min", summary_metrics.get("temperature_min")),
        ("case.total_radiator_span", metric_values.get("case.total_radiator_span")),
        ("case.component_count", metric_values.get("case.component_count")),
        ("solver.iterations", metric_values.get("solver.iterations")),
    ]
    return [[label, _format_scalar(value)] for label, value in ordered_metrics if value is not None]


def _build_constraint_rows(evaluation_payload: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for report in evaluation_payload.get("constraint_reports", []):
        actual = report.get("actual")
        limit = report.get("limit")
        margin = report.get("margin")
        if margin is None:
            margin = _compute_margin(report)
        rows.append(
            [
                str(report.get("constraint_id", "")),
                str(report.get("relation", "")),
                _format_scalar(actual),
                _format_scalar(limit),
                _format_scalar(margin),
                _format_bool(report.get("satisfied")),
            ]
        )
    return rows


def _build_diagnostic_rows(
    case_payload: dict[str, Any],
    solution_payload: dict[str, Any],
    evaluation_payload: dict[str, Any],
) -> list[list[str]]:
    diagnostics = dict(solution_payload.get("solver_diagnostics", {}))
    evaluation_meta = dict(evaluation_payload.get("evaluation_meta", {}))
    physics = dict(case_payload.get("physics", {}))
    background = dict(physics.get("background_boundary_cooling", {}))
    active_heat_sources = sum(1 for load in case_payload.get("loads", []) if float(load.get("total_power", 0.0)) > 0.0)
    rows = [
        ["Solver", str(diagnostics.get("solver", "n/a"))],
        ["Converged", _format_bool(diagnostics.get("converged"))],
        ["Iterations", _format_scalar(diagnostics.get("iterations"))],
        ["Evaluation Spec", str(evaluation_meta.get("spec_id", "n/a"))],
        ["Feasible", _format_bool(evaluation_payload.get("feasible"))],
        ["Ambient Temperature", _format_scalar(physics.get("ambient_temperature"))],
        [
            "Background Boundary Cooling",
            f"h={_format_scalar(background.get('transfer_coefficient'))}, eps={_format_scalar(background.get('emissivity'))}",
        ],
        ["Active Heat Sources", _format_scalar(active_heat_sources)],
    ]
    return rows


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_grid(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    with np.load(path) as payload:
        values = payload.get("values")
        if values is None:
            return None
        return np.asarray(values, dtype=np.float64)


def _resolve_panel_domain(field_view: dict[str, Any], case_payload: dict[str, Any]) -> tuple[float, float]:
    panel_domain = dict(case_payload.get("panel_domain", {}))
    if panel_domain.get("width") is not None and panel_domain.get("height") is not None:
        return float(panel_domain["width"]), float(panel_domain["height"])
    panel_domain = dict(field_view.get("panel_domain", {}))
    return float(panel_domain.get("width", 1.0)), float(panel_domain.get("height", 1.0))


def _resolved_layout_metrics(case_payload: dict[str, Any]) -> dict[str, float]:
    recomputed = _recompute_layout_metrics(case_payload)
    if recomputed is not None:
        return recomputed
    provenance = dict(case_payload.get("provenance", {}))
    return dict(provenance.get("layout_metrics", {}))


def _recompute_layout_metrics(case_payload: dict[str, Any]) -> dict[str, float] | None:
    provenance = case_payload.get("provenance", {})
    if isinstance(provenance, dict):
        layout_context = provenance.get("layout_context")
        if isinstance(layout_context, dict):
            metrics = measure_case_layout_metrics(case_payload, layout_context=layout_context)
            if metrics is not None:
                return metrics
    layout_context = _load_case_layout_context(case_payload)
    if layout_context is None:
        return None
    return measure_case_layout_metrics(case_payload, layout_context=layout_context)


def _load_case_template_payload(case_payload: dict[str, Any]) -> dict[str, Any] | None:
    provenance = dict(case_payload.get("provenance", {}))
    case_meta = dict(case_payload.get("case_meta", {}))
    template_id = provenance.get("source_template_id") or case_meta.get("scenario_id")
    if not isinstance(template_id, str) or not template_id:
        return None
    repo_root = Path(__file__).resolve().parents[1]
    template_path = repo_root / "scenarios" / "templates" / f"{template_id}.yaml"
    if not template_path.exists():
        return None
    return _load_yaml(template_path)


def _load_case_layout_context(case_payload: dict[str, Any]) -> dict[str, dict[str, float]] | None:
    panel_domain = case_payload.get("panel_domain")
    if not isinstance(panel_domain, dict):
        return None
    template_payload = _load_case_template_payload(case_payload)
    if template_payload is None:
        return None
    placement_regions = template_payload.get("placement_regions", [])
    placement_region = placement_regions[0] if placement_regions else {
        "x_min": 0.0,
        "x_max": float(panel_domain.get("width", 0.0)),
        "y_min": 0.0,
        "y_max": float(panel_domain.get("height", 0.0)),
    }
    zones = dict(dict(template_payload.get("generation_rules", {})).get("layout_strategy", {}).get("zones", {}))
    return build_layout_context(
        placement_region=placement_region,
        active_deck=zones.get("active_deck"),
        dense_core=zones.get("dense_core"),
    )


def _project_bounds(
    bounds: dict[str, Any],
    domain_width: float,
    domain_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> tuple[float, float, float, float]:
    x_min = float(bounds.get("x_min", 0.0))
    x_max = float(bounds.get("x_max", x_min))
    y_min = float(bounds.get("y_min", 0.0))
    y_max = float(bounds.get("y_max", y_min))
    x0 = frame_x + frame_width * (x_min / max(domain_width, 1e-9))
    y0 = frame_y + frame_height * (1.0 - y_max / max(domain_height, 1e-9))
    width = frame_width * ((x_max - x_min) / max(domain_width, 1e-9))
    height = frame_height * ((y_max - y_min) / max(domain_height, 1e-9))
    return x0, y0, max(width, 2.0), max(height, 2.0)


def _project_point(
    x_value: float,
    y_value: float,
    domain_width: float,
    domain_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> tuple[float, float]:
    return (
        frame_x + frame_width * (x_value / max(domain_width, 1.0e-9)),
        frame_y + frame_height * (1.0 - y_value / max(domain_height, 1.0e-9)),
    )


def _project_outline(
    component: dict[str, Any],
    *,
    domain_width: float,
    domain_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> list[tuple[float, float]]:
    outline = component.get("outline")
    if not isinstance(outline, list):
        return []
    projected: list[tuple[float, float]] = []
    for point in outline:
        if not isinstance(point, list | tuple) or len(point) < 2:
            continue
        projected.append(
            _project_point(
                float(point[0]),
                float(point[1]),
                domain_width,
                domain_height,
                frame_x,
                frame_y,
                frame_width,
                frame_height,
            )
        )
    return projected


def _project_label_point(
    bounds: dict[str, Any],
    domain_width: float,
    domain_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> tuple[float, float]:
    x_center = 0.5 * (float(bounds.get("x_min", 0.0)) + float(bounds.get("x_max", 0.0)))
    y_center = 0.5 * (float(bounds.get("y_min", 0.0)) + float(bounds.get("y_max", 0.0)))
    projected_x, projected_y = _project_point(
        x_center,
        y_center,
        domain_width,
        domain_height,
        frame_x,
        frame_y,
        frame_width,
        frame_height,
    )
    return projected_x, projected_y + 4.0


def _downsample_grid(values: np.ndarray, *, max_rows: int, max_cols: int) -> np.ndarray:
    row_indices = _select_indices(values.shape[0], max_rows)
    col_indices = _select_indices(values.shape[1], max_cols)
    return values[np.ix_(row_indices, col_indices)]


def _select_indices(size: int, target: int) -> np.ndarray:
    if size <= target:
        return np.arange(size, dtype=int)
    indices = np.rint(np.linspace(0, size - 1, num=target)).astype(int)
    return np.unique(indices)


def _color_for_value(
    value: float,
    value_min: float,
    value_max: float,
    palette: tuple[tuple[int, int, int], ...],
) -> str:
    if value_max <= value_min:
        return _rgb_hex(*palette[-1])
    ratio = (value - value_min) / (value_max - value_min)
    return _color_for_ratio(ratio, palette)


def _color_for_ratio(ratio: float, palette: tuple[tuple[int, int, int], ...]) -> str:
    clipped = min(1.0, max(0.0, float(ratio)))
    if len(palette) == 1:
        return _rgb_hex(*palette[0])
    scaled = clipped * float(len(palette) - 1)
    left_index = int(np.floor(scaled))
    right_index = min(left_index + 1, len(palette) - 1)
    blend = scaled - float(left_index)
    left = palette[left_index]
    right = palette[right_index]
    return _rgb_hex(
        int(round(left[0] + (right[0] - left[0]) * blend)),
        int(round(left[1] + (right[1] - left[1]) * blend)),
        int(round(left[2] + (right[2] - left[2]) * blend)),
    )


def _rgb_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def _legend_footprint_points(x: float, y: float) -> list[tuple[float, float]]:
    return [
        (x, y),
        (x + 12.0, y),
        (x + 16.0, y + 4.0),
        (x + 13.0, y + 10.0),
        (x + 2.0, y + 10.0),
    ]


def _figure_grid(items: list[tuple[str, str]]) -> str:
    return (
        "<div class='figure-grid'>"
        + "".join(
            f"<figure class='figure-card'><img src='{src}' alt='{caption}'/><figcaption>{caption}</figcaption></figure>"
            for src, caption in items
        )
        + "</div>"
    )


def _relative_href(from_dir: Path, target: Path) -> str:
    return os.path.relpath(target, start=from_dir).replace("\\", "/")


def _format_scalar(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    numeric_value = float(value)
    if abs(numeric_value) >= 100.0:
        return f"{numeric_value:.3f}"
    if abs(numeric_value) >= 10.0:
        return f"{numeric_value:.3f}"
    return f"{numeric_value:.3f}"


def _format_hotspot(hotspot: dict[str, Any]) -> str:
    if not hotspot:
        return "n/a"
    return f"({float(hotspot.get('x', 0.0)):.2f}, {float(hotspot.get('y', 0.0)):.2f})"


def _format_grid_shape(value: Any) -> str:
    if not isinstance(value, list):
        return "n/a"
    return " x ".join(str(int(item)) for item in value)


def _format_bounds(bounds: dict[str, Any]) -> str:
    if not bounds:
        return "n/a"
    return (
        f"x=[{float(bounds.get('x_min', 0.0)):.2f}, {float(bounds.get('x_max', 0.0)):.2f}], "
        f"y=[{float(bounds.get('y_min', 0.0)):.2f}, {float(bounds.get('y_max', 0.0)):.2f}]"
    )


def _compute_margin(report: dict[str, Any]) -> float:
    relation = str(report.get("relation", "<="))
    actual = float(report.get("actual", 0.0))
    limit = float(report.get("limit", 0.0))
    if relation == "<=":
        return limit - actual
    if relation == ">=":
        return actual - limit
    return 0.0


def _format_bool(value: Any) -> str:
    if value is None:
        return "n/a"
    return "yes" if bool(value) else "no"
