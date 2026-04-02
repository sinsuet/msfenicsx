"""Single-case page renderers for representative thermal bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from visualization.static_assets import dashboard_style, html_metric_grid, html_section, html_table, load_json, write_dashboard


def render_case_page(representative_root: str | Path) -> Path:
    root = Path(representative_root)
    field_view = load_json(root / "summaries" / "field_view.json")
    case_payload = _load_yaml(root / "case.yaml")
    solution_payload = _load_yaml(root / "solution.yaml")
    evaluation_payload = _load_yaml(root / "evaluation.yaml") if (root / "evaluation.yaml").exists() else {}
    case_id = str(case_payload.get("case_meta", {}).get("case_id", root.name))

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
            html_table(["Component", "Bounds"], component_rows or [["No components", ""]])
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
