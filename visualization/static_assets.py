"""Shared static asset helpers for experiment dashboards and figures."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def write_dashboard(path: Path, title: str, body: str, *, style: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        "<!DOCTYPE html><html><head>"
        f"<meta charset='utf-8'><title>{html.escape(title)}</title>"
        f"<style>{style}</style>"
        "</head><body>"
        f"{body}</body></html>"
    )
    path.write_text(payload, encoding="utf-8")
    return path


def svg_document(*, title: str, width: int, height: int, body: str, background: str) -> str:
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'"
        f" role='img' aria-labelledby='title desc'>"
        f"<title>{html.escape(title)}</title>"
        f"<desc>{html.escape(title)} static figure export</desc>"
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='{background}'/>"
        f"{body}</svg>"
    )


def svg_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str,
    stroke: str = "none",
    stroke_width: float = 0.0,
    rx: float = 0.0,
) -> str:
    return (
        f"<rect x='{x:.2f}' y='{y:.2f}' width='{width:.2f}' height='{height:.2f}'"
        f" rx='{rx:.2f}' fill='{fill}' stroke='{stroke}' stroke-width='{stroke_width:.2f}'/>"
    )


def svg_line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str,
    stroke_width: float = 1.0,
    dasharray: str | None = None,
) -> str:
    dash = "" if dasharray is None else f" stroke-dasharray='{dasharray}'"
    return (
        f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}'"
        f" stroke='{stroke}' stroke-width='{stroke_width:.2f}'{dash}/>"
    )


def svg_text(
    x: float,
    y: float,
    value: str,
    *,
    fill: str = "#1f2933",
    size: int = 16,
    weight: str = "400",
    anchor: str = "start",
) -> str:
    return (
        f"<text x='{x:.2f}' y='{y:.2f}' fill='{fill}' font-size='{size}'"
        f" font-family='Georgia, serif' font-weight='{weight}' text-anchor='{anchor}'>"
        f"{html.escape(value)}</text>"
    )


def svg_polyline(points: list[tuple[float, float]], *, stroke: str, stroke_width: float = 3.0) -> str:
    if not points:
        return ""
    serialized = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (
        f"<polyline points='{serialized}' fill='none' stroke='{stroke}'"
        f" stroke-width='{stroke_width:.2f}' stroke-linejoin='round' stroke-linecap='round'/>"
    )


def render_metric_cards(
    cards: list[tuple[str, str]],
    *,
    x: float,
    y: float,
    width: float,
    card_height: float,
    fill: str,
    stroke: str,
    label_fill: str = "#556270",
    value_fill: str = "#1f2933",
) -> str:
    if not cards:
        return ""
    gap = 18.0
    card_width = (width - gap * float(len(cards) - 1)) / float(len(cards))
    parts: list[str] = []
    for index, (label, value) in enumerate(cards):
        card_x = x + float(index) * (card_width + gap)
        parts.append(svg_rect(card_x, y, card_width, card_height, fill=fill, stroke=stroke, stroke_width=1.0, rx=14.0))
        parts.append(svg_text(card_x + 18.0, y + 32.0, label, fill=label_fill, size=14, weight="600"))
        parts.append(svg_text(card_x + 18.0, y + 74.0, value, fill=value_fill, size=28, weight="700"))
    return "".join(parts)


def render_vertical_bar_panel(
    *,
    title: str,
    items: list[tuple[str, float | None]],
    x: float,
    y: float,
    width: float,
    height: float,
    panel_fill: str,
    panel_stroke: str,
    bar_fill: str,
    label_fill: str = "#1f2933",
    value_fill: str = "#556270",
    value_formatter: Any = None,
) -> str:
    parts = [svg_rect(x, y, width, height, fill=panel_fill, stroke=panel_stroke, stroke_width=1.0, rx=18.0)]
    parts.append(svg_text(x + 20.0, y + 30.0, title, fill=label_fill, size=18, weight="700"))
    numeric_items = [(label, float(value)) for label, value in items if value is not None]
    if not numeric_items:
        parts.append(svg_text(x + 20.0, y + 68.0, "No data", fill=value_fill, size=16, weight="600"))
        return "".join(parts)
    max_value = max(value for _, value in numeric_items)
    chart_x = x + 28.0
    chart_y = y + 56.0
    chart_width = width - 56.0
    chart_height = height - 96.0
    baseline_y = chart_y + chart_height
    parts.append(svg_line(chart_x, baseline_y, chart_x + chart_width, baseline_y, stroke=panel_stroke, stroke_width=1.0))
    gap = 14.0
    bar_width = max(18.0, (chart_width - gap * float(len(numeric_items) - 1)) / float(len(numeric_items)))
    for index, (label, value) in enumerate(numeric_items):
        bar_x = chart_x + float(index) * (bar_width + gap)
        bar_height = 0.0 if max_value <= 0.0 else chart_height * (value / max_value)
        bar_y = baseline_y - bar_height
        parts.append(svg_rect(bar_x, bar_y, bar_width, max(2.0, bar_height), fill=bar_fill, rx=10.0))
        parts.append(svg_text(bar_x + bar_width / 2.0, baseline_y + 22.0, label, fill=label_fill, size=13, weight="600", anchor="middle"))
        formatter = value_formatter or format_scalar
        parts.append(svg_text(bar_x + bar_width / 2.0, bar_y - 8.0, formatter(value), fill=value_fill, size=12, weight="600", anchor="middle"))
    return "".join(parts)


def render_horizontal_bar_panel(
    *,
    title: str,
    items: list[tuple[str, float | None]],
    x: float,
    y: float,
    width: float,
    height: float,
    panel_fill: str,
    panel_stroke: str,
    bar_fill: str,
    label_fill: str = "#1f2933",
    value_fill: str = "#556270",
    value_formatter: Any = None,
) -> str:
    parts = [svg_rect(x, y, width, height, fill=panel_fill, stroke=panel_stroke, stroke_width=1.0, rx=18.0)]
    parts.append(svg_text(x + 20.0, y + 30.0, title, fill=label_fill, size=18, weight="700"))
    numeric_items = [(label, float(value)) for label, value in items if value is not None][:6]
    if not numeric_items:
        parts.append(svg_text(x + 20.0, y + 68.0, "No data", fill=value_fill, size=16, weight="600"))
        return "".join(parts)
    max_value = max(value for _, value in numeric_items)
    row_height = (height - 60.0) / float(max(1, len(numeric_items)))
    formatter = value_formatter or format_scalar
    for index, (label, value) in enumerate(numeric_items):
        row_y = y + 56.0 + float(index) * row_height
        label_y = row_y + 18.0
        bar_x = x + 170.0
        bar_width = 0.0 if max_value <= 0.0 else (width - 220.0) * (value / max_value)
        parts.append(svg_text(x + 20.0, label_y, label, fill=label_fill, size=13, weight="600"))
        parts.append(svg_rect(bar_x, row_y + 4.0, width - 220.0, 14.0, fill="#e6ded0", rx=8.0))
        parts.append(svg_rect(bar_x, row_y + 4.0, max(2.0, bar_width), 14.0, fill=bar_fill, rx=8.0))
        parts.append(svg_text(x + width - 20.0, label_y, formatter(value), fill=value_fill, size=13, weight="600", anchor="end"))
    return "".join(parts)


def render_line_panel(
    *,
    title: str,
    points: list[tuple[float, float | None]],
    x: float,
    y: float,
    width: float,
    height: float,
    panel_fill: str,
    panel_stroke: str,
    line_color: str,
    label_fill: str = "#1f2933",
    empty_fill: str = "#556270",
    value_formatter: Any = None,
) -> str:
    parts = [svg_rect(x, y, width, height, fill=panel_fill, stroke=panel_stroke, stroke_width=1.0, rx=18.0)]
    parts.append(svg_text(x + 20.0, y + 30.0, title, fill=label_fill, size=18, weight="700"))
    numeric_points = [(float(px), float(py)) for px, py in points if py is not None]
    if len(numeric_points) < 2:
        parts.append(svg_text(x + 20.0, y + 68.0, "Not enough points", fill=empty_fill, size=16, weight="600"))
        return "".join(parts)
    xs = [px for px, _ in numeric_points]
    ys = [py for _, py in numeric_points]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    if max_x <= min_x:
        max_x = min_x + 1.0
    if max_y <= min_y:
        max_y = min_y + 1.0
    chart_x = x + 32.0
    chart_y = y + 52.0
    chart_width = width - 64.0
    chart_height = height - 92.0
    baseline_y = chart_y + chart_height
    parts.append(svg_line(chart_x, chart_y, chart_x, baseline_y, stroke=panel_stroke, stroke_width=1.0))
    parts.append(svg_line(chart_x, baseline_y, chart_x + chart_width, baseline_y, stroke=panel_stroke, stroke_width=1.0))
    plot_points: list[tuple[float, float]] = []
    for px, py in numeric_points:
        scaled_x = chart_x + chart_width * ((px - min_x) / (max_x - min_x))
        scaled_y = baseline_y - chart_height * ((py - min_y) / (max_y - min_y))
        plot_points.append((scaled_x, scaled_y))
    parts.append(svg_polyline(plot_points, stroke=line_color, stroke_width=3.5))
    formatter = value_formatter or format_scalar
    parts.append(svg_text(chart_x, chart_y - 8.0, formatter(max(ys)), fill=empty_fill, size=12, weight="600"))
    parts.append(svg_text(chart_x, baseline_y + 22.0, formatter(min(ys)), fill=empty_fill, size=12, weight="600"))
    parts.append(svg_text(chart_x + chart_width, baseline_y + 22.0, f"x={int(max(xs))}", fill=empty_fill, size=12, weight="600", anchor="end"))
    return "".join(parts)


def render_text_panel(
    *,
    title: str,
    rows: list[str],
    x: float,
    y: float,
    width: float,
    height: float,
    panel_fill: str,
    panel_stroke: str,
    label_fill: str = "#1f2933",
    text_fill: str = "#556270",
) -> str:
    parts = [svg_rect(x, y, width, height, fill=panel_fill, stroke=panel_stroke, stroke_width=1.0, rx=18.0)]
    parts.append(svg_text(x + 20.0, y + 30.0, title, fill=label_fill, size=18, weight="700"))
    if not rows:
        rows = ["No data"]
    for index, row in enumerate(rows[:8]):
        parts.append(svg_text(x + 20.0, y + 64.0 + float(index) * 24.0, row, fill=text_fill, size=13, weight="600"))
    return "".join(parts)


def format_scalar(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    absolute = abs(float(value))
    if absolute >= 1000.0:
        return f"{value:.1f}"
    if absolute >= 10.0:
        return f"{value:.2f}"
    return f"{value:.{digits}f}"
