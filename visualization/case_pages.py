"""Single-case page renderers for representative thermal bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from visualization.static_assets import (
    dashboard_style,
    html_metric_grid,
    html_section,
    html_table,
    load_json,
    svg_document,
    svg_line,
    svg_polygon,
    svg_rect,
    svg_text,
    write_dashboard,
    write_svg,
)


def render_case_page(representative_root: str | Path) -> Path:
    root = Path(representative_root)
    field_view = load_json(root / "summaries" / "field_view.json")
    case_payload = _load_yaml(root / "case.yaml")
    solution_payload = _load_yaml(root / "solution.yaml")
    evaluation_payload = _load_yaml(root / "evaluation.yaml") if (root / "evaluation.yaml").exists() else {}
    case_id = str(case_payload.get("case_meta", {}).get("case_id", root.name))
    figures_root = root / "figures"
    write_svg(figures_root / "layout.svg", _render_layout_svg(case_id, field_view))

    component_rows = [
        [
            str(component.get("component_id", "")),
            _format_bounds(dict(component.get("bounds", {}))),
        ]
        for component in field_view.get("layout", {}).get("components", [])
    ]
    sink_rows = [
        [
            str(line_sink.get("feature_id", "")),
            str(line_sink.get("edge", "")),
        ]
        for line_sink in field_view.get("layout", {}).get("line_sinks", [])
    ]
    constraint_rows = [
        [
            str(report.get("constraint_id", "")),
            _format_margin(report),
        ]
        for report in evaluation_payload.get("constraint_reports", [])
    ]
    body = (
        "<main>"
        f"<section class='hero'><h1>{case_id}</h1>"
        "<p>Single-case physical-field view for the representative solution bundle.</p>"
        + html_metric_grid(
            [
                ("Peak Temperature", _format_scalar(solution_payload.get("summary_metrics", {}).get("temperature_max"))),
                (
                    "Gradient RMS",
                    _format_scalar(solution_payload.get("summary_metrics", {}).get("temperature_gradient_rms")),
                ),
                ("Hotspot", _format_hotspot(field_view.get("temperature", {}).get("hotspot", {}))),
            ]
        )
        + "</section>"
        + html_section(
            "Layout Overview",
            "<figure><img src='../figures/layout.svg' alt='Layout view' style='width:100%;max-width:720px;border-radius:14px;border:1px solid #d7c8b3;'/></figure>"
            + html_table(["Component", "Bounds"], component_rows or [["No components", ""]])
            + html_table(["Sink", "Edge"], sink_rows or [["No sinks", ""]]),
        )
        + html_section(
            "Temperature Field",
            html_metric_grid(
                [
                    ("Grid Shape", _format_grid_shape(field_view.get("temperature", {}).get("grid_shape"))),
                    ("Min", _format_scalar(field_view.get("temperature", {}).get("min"))),
                    ("Max", _format_scalar(field_view.get("temperature", {}).get("max"))),
                ]
            ),
        )
        + html_section(
            "Gradient Magnitude",
            html_metric_grid(
                [
                    ("Grid Shape", _format_grid_shape(field_view.get("gradient_magnitude", {}).get("grid_shape"))),
                    ("Min", _format_scalar(field_view.get("gradient_magnitude", {}).get("min"))),
                    ("Max", _format_scalar(field_view.get("gradient_magnitude", {}).get("max"))),
                ]
            ),
        )
        + html_section(
            "Constraint Margins",
            html_table(["Constraint", "Margin"], constraint_rows or [["No constraints", ""]]),
        )
        + "</main>"
    )
    output_path = root / "pages" / "index.html"
    return write_dashboard(output_path, f"{case_id} Case Page", body, style=dashboard_style())


def _render_layout_svg(case_id: str, field_view: dict[str, Any]) -> str:
    width = 760
    height = 560
    frame_x = 48.0
    frame_y = 74.0
    frame_width = 640.0
    frame_height = 430.0
    panel_domain = dict(field_view.get("panel_domain", {}))
    panel_width = float(panel_domain.get("width", 1.0))
    panel_height = float(panel_domain.get("height", 1.0))
    components = list(field_view.get("layout", {}).get("components", []))
    line_sinks = list(field_view.get("layout", {}).get("line_sinks", []))

    parts = [
        svg_text(48.0, 42.0, f"{case_id} Layout", size=24, weight="700"),
        svg_rect(frame_x, frame_y, frame_width, frame_height, fill="#fbf3e7", stroke="#c8b49c", stroke_width=2.0, rx=24.0),
    ]
    for component in components:
        outline = list(component.get("outline", []))
        if outline:
            projected = [
                _project_point(
                    float(point[0]),
                    float(point[1]),
                    panel_width=panel_width,
                    panel_height=panel_height,
                    frame_x=frame_x,
                    frame_y=frame_y,
                    frame_width=frame_width,
                    frame_height=frame_height,
                )
                for point in outline
            ]
            parts.append(svg_polygon(projected, fill="#b5543855", stroke="#7b3b27", stroke_width=1.6))
        else:
            bounds = dict(component.get("bounds", {}))
            x0, y0, box_width, box_height = _project_bounds(
                bounds,
                panel_width=panel_width,
                panel_height=panel_height,
                frame_x=frame_x,
                frame_y=frame_y,
                frame_width=frame_width,
                frame_height=frame_height,
            )
            parts.append(
                svg_rect(
                    x0,
                    y0,
                    box_width,
                    box_height,
                    fill="#b5543855",
                    stroke="#7b3b27",
                    stroke_width=1.6,
                    rx=8.0,
                )
            )
        label_x, label_y = _project_label_point(
            dict(component.get("bounds", {})),
            panel_width=panel_width,
            panel_height=panel_height,
            frame_x=frame_x,
            frame_y=frame_y,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        parts.append(svg_text(label_x, label_y, str(component.get("component_id", "")), size=12, weight="700", fill="#2f4858"))
    for line_sink in line_sinks:
        parts.extend(
            _render_sink(
                line_sink,
                panel_width=panel_width,
                panel_height=panel_height,
                frame_x=frame_x,
                frame_y=frame_y,
                frame_width=frame_width,
                frame_height=frame_height,
            )
        )
    return svg_document(title=f"{case_id} Layout", width=width, height=height, body="".join(parts), background="#f8f1e7")


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _format_scalar(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


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


def _format_margin(report: dict[str, Any]) -> str:
    relation = str(report.get("relation", "<="))
    actual = float(report.get("actual", 0.0))
    limit = float(report.get("limit", 0.0))
    if relation == "<=":
        margin = limit - actual
    elif relation == ">=":
        margin = actual - limit
    else:
        margin = 0.0
    return f"{margin:.3f}"


def _project_point(
    x_value: float,
    y_value: float,
    *,
    panel_width: float,
    panel_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> tuple[float, float]:
    return (
        frame_x + frame_width * (x_value / max(panel_width, 1.0e-9)),
        frame_y + frame_height * (1.0 - y_value / max(panel_height, 1.0e-9)),
    )


def _project_bounds(
    bounds: dict[str, Any],
    *,
    panel_width: float,
    panel_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> tuple[float, float, float, float]:
    x_min = float(bounds.get("x_min", 0.0))
    x_max = float(bounds.get("x_max", 0.0))
    y_min = float(bounds.get("y_min", 0.0))
    y_max = float(bounds.get("y_max", 0.0))
    projected_left, projected_top = _project_point(
        x_min,
        y_max,
        panel_width=panel_width,
        panel_height=panel_height,
        frame_x=frame_x,
        frame_y=frame_y,
        frame_width=frame_width,
        frame_height=frame_height,
    )
    projected_right, projected_bottom = _project_point(
        x_max,
        y_min,
        panel_width=panel_width,
        panel_height=panel_height,
        frame_x=frame_x,
        frame_y=frame_y,
        frame_width=frame_width,
        frame_height=frame_height,
    )
    return projected_left, projected_top, projected_right - projected_left, projected_bottom - projected_top


def _project_label_point(
    bounds: dict[str, Any],
    *,
    panel_width: float,
    panel_height: float,
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
        panel_width=panel_width,
        panel_height=panel_height,
        frame_x=frame_x,
        frame_y=frame_y,
        frame_width=frame_width,
        frame_height=frame_height,
    )
    return projected_x - 28.0, projected_y + 4.0


def _render_sink(
    line_sink: dict[str, Any],
    *,
    panel_width: float,
    panel_height: float,
    frame_x: float,
    frame_y: float,
    frame_width: float,
    frame_height: float,
) -> list[str]:
    edge = str(line_sink.get("edge", "top"))
    sink_color = "#2a9d8f"
    if edge in {"top", "bottom"}:
        start_x = frame_x + frame_width * (float(line_sink.get("start_x", 0.0)) / max(panel_width, 1.0e-9))
        end_x = frame_x + frame_width * (float(line_sink.get("end_x", 0.0)) / max(panel_width, 1.0e-9))
        y_value = frame_y if edge == "top" else frame_y + frame_height
        return [svg_line(start_x, y_value, end_x, y_value, stroke=sink_color, stroke_width=6.0)]
    start_y = frame_y + frame_height * (1.0 - float(line_sink.get("start_y", 0.0)) / max(panel_height, 1.0e-9))
    end_y = frame_y + frame_height * (1.0 - float(line_sink.get("end_y", panel_height)) / max(panel_height, 1.0e-9))
    x_value = frame_x if edge == "left" else frame_x + frame_width
    return [svg_line(x_value, start_y, x_value, end_y, stroke=sink_color, stroke_width=6.0)]
