"""Axis, legend, and color-bar helpers for scientific figures."""

from __future__ import annotations

from typing import Any, Callable

from visualization.figure_theme import SCIENTIFIC_COLORS, SCIENTIFIC_FONT_FAMILY
from visualization.static_assets import svg_line, svg_polyline, svg_rect, svg_text


def render_colorbar_panel(
    *,
    title: str,
    value_min: float,
    value_max: float,
    x: float,
    y: float,
    width: float,
    height: float,
) -> str:
    steps = 20
    bar_width = max(12.0, width * 0.38)
    bar_x = x + width * 0.5
    bar_y = y + 26.0
    bar_height = max(24.0, height - 58.0)
    step_height = bar_height / float(steps)
    parts = [
        f"<g data-figure-role='colorbar'>",
        svg_text(
            x,
            y + 14.0,
            title,
            fill=SCIENTIFIC_COLORS["ink"],
            size=12,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
    ]
    for index in range(steps):
        ratio = float(index) / float(max(1, steps - 1))
        parts.append(
            svg_rect(
                bar_x,
                bar_y + float(steps - 1 - index) * step_height,
                bar_width,
                step_height + 0.2,
                fill=_interpolate_blue_red(ratio),
            )
        )
    parts.extend(
        [
            svg_rect(
                bar_x,
                bar_y,
                bar_width,
                bar_height,
                fill="none",
                stroke=SCIENTIFIC_COLORS["panel_stroke"],
                stroke_width=1.0,
            ),
            svg_line(
                bar_x + bar_width,
                bar_y,
                bar_x + bar_width + 6.0,
                bar_y,
                stroke=SCIENTIFIC_COLORS["panel_stroke"],
                stroke_width=1.0,
            ),
            svg_line(
                bar_x + bar_width,
                bar_y + bar_height,
                bar_x + bar_width + 6.0,
                bar_y + bar_height,
                stroke=SCIENTIFIC_COLORS["panel_stroke"],
                stroke_width=1.0,
            ),
            svg_text(
                bar_x + bar_width + 10.0,
                bar_y + 4.0,
                f"{value_max:.3f}",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            svg_text(
                bar_x + bar_width + 10.0,
                bar_y + bar_height + 4.0,
                f"{value_min:.3f}",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            "</g>",
        ]
    )
    return "".join(parts)


def render_progress_panel(
    *,
    title: str,
    series: list[dict[str, Any]],
    x: float,
    y: float,
    width: float,
    height: float,
    milestones: list[dict[str, Any]] | None = None,
    value_formatter: Callable[[float], str] | None = None,
) -> str:
    parts = [
        svg_rect(
            x,
            y,
            width,
            height,
            fill=SCIENTIFIC_COLORS["panel_fill"],
            stroke=SCIENTIFIC_COLORS["panel_stroke"],
            stroke_width=1.0,
            rx=8.0,
        ),
        svg_text(
            x + 18.0,
            y + 26.0,
            title,
            fill=SCIENTIFIC_COLORS["ink"],
            size=15,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
    ]
    numeric_series: list[tuple[str, str, list[tuple[float, float]]]] = []
    for row in series:
        label = str(row.get("label", "series"))
        stroke = str(row.get("stroke", SCIENTIFIC_COLORS["ink"]))
        numeric_points = [(float(px), float(py)) for px, py in row.get("points", []) if py is not None]
        if numeric_points:
            numeric_series.append((label, stroke, numeric_points))
    if not numeric_series:
        parts.append(
            svg_text(
                x + 18.0,
                y + 54.0,
                "No data",
                fill=SCIENTIFIC_COLORS["muted"],
                size=12,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            )
        )
        return "".join(parts)

    xs = [point_x for _, _, points in numeric_series for point_x, _ in points]
    ys = [point_y for _, _, points in numeric_series for _, point_y in points]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    if max_x <= min_x:
        max_x = min_x + 1.0
    if max_y <= min_y:
        max_y = min_y + 1.0
    y_padding = (max_y - min_y) * 0.06
    min_y -= y_padding
    max_y += y_padding

    chart_x = x + 42.0
    chart_y = y + 50.0
    chart_width = width - 64.0
    chart_height = height - 86.0
    baseline_y = chart_y + chart_height
    formatter = value_formatter or _default_axis_formatter

    parts.extend(
        [
            svg_line(chart_x, chart_y, chart_x, baseline_y, stroke=SCIENTIFIC_COLORS["panel_stroke"], stroke_width=1.0),
            svg_line(
                chart_x,
                baseline_y,
                chart_x + chart_width,
                baseline_y,
                stroke=SCIENTIFIC_COLORS["panel_stroke"],
                stroke_width=1.0,
            ),
        ]
    )

    milestone_rows = milestones or []
    for index, milestone in enumerate(milestone_rows[:3]):
        milestone_x = float(milestone.get("evaluation_index", milestone.get("x", min_x)))
        scaled_x = chart_x + chart_width * ((milestone_x - min_x) / (max_x - min_x))
        parts.append(
            svg_line(
                scaled_x,
                chart_y,
                scaled_x,
                baseline_y,
                stroke=SCIENTIFIC_COLORS["panel_stroke"],
                stroke_width=1.0,
                dasharray="4 4",
            )
        )
        label = str(milestone.get("label", "")).strip()
        if label:
            parts.append(
                svg_text(
                    scaled_x + 4.0,
                    chart_y + 12.0 + float(index) * 12.0,
                    label,
                    fill=SCIENTIFIC_COLORS["muted"],
                    size=10,
                    weight="500",
                    font_family=SCIENTIFIC_FONT_FAMILY,
                )
            )

    for label, stroke, points in numeric_series:
        plot_points: list[tuple[float, float]] = []
        for point_x, point_y in points:
            scaled_x = chart_x + chart_width * ((point_x - min_x) / (max_x - min_x))
            scaled_y = baseline_y - chart_height * ((point_y - min_y) / (max_y - min_y))
            plot_points.append((scaled_x, scaled_y))
        parts.append(svg_polyline(plot_points, stroke=stroke, stroke_width=3.0))

    parts.extend(
        [
            svg_text(
                chart_x,
                chart_y - 8.0,
                formatter(max_y - y_padding),
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            svg_text(
                chart_x,
                baseline_y + 22.0,
                formatter(min_y + y_padding),
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            svg_text(
                chart_x,
                baseline_y + 40.0,
                f"eval {int(round(min_x))}",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
            svg_text(
                chart_x + chart_width,
                baseline_y + 40.0,
                f"eval {int(round(max_x))}",
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                anchor="end",
                font_family=SCIENTIFIC_FONT_FAMILY,
            ),
        ]
    )

    if len(numeric_series) > 1:
        legend_x = x + width - 132.0
        legend_y = y + 24.0
        for index, (label, stroke, _) in enumerate(numeric_series[:4]):
            row_y = legend_y + float(index) * 16.0
            parts.append(svg_line(legend_x, row_y - 4.0, legend_x + 16.0, row_y - 4.0, stroke=stroke, stroke_width=2.6))
            parts.append(
                svg_text(
                    legend_x + 22.0,
                    row_y,
                    label,
                    fill=SCIENTIFIC_COLORS["muted"],
                    size=10,
                    weight="500",
                    font_family=SCIENTIFIC_FONT_FAMILY,
                )
            )
    return "".join(parts)


def _interpolate_blue_red(ratio: float) -> str:
    clipped = min(1.0, max(0.0, ratio))
    red = int(round(43 + (188 - 43) * clipped))
    green = int(round(98 + (76 - 98) * clipped))
    blue = int(round(163 + (60 - 163) * clipped))
    return f"#{red:02x}{green:02x}{blue:02x}"


def _default_axis_formatter(value: float) -> str:
    magnitude = abs(float(value))
    if magnitude >= 100.0:
        return f"{value:.1f}"
    if magnitude >= 10.0:
        return f"{value:.2f}"
    return f"{value:.3f}"
