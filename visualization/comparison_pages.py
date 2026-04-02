"""Mixed-mode comparison page renderers for the new s1_typical run tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from optimizers.comparison_summary import build_comparison_summaries
from visualization.case_pages import (
    _GRADIENT_PALETTE,
    _THERMAL_PALETTE,
    _downsample_grid,
    _load_grid,
    _render_heatmap_cells,
    _render_layout_overlay,
)
from visualization.figure_axes import render_colorbar_panel, render_progress_panel
from visualization.figure_text import wrap_text_lines
from visualization.figure_theme import SCIENTIFIC_COLORS, SCIENTIFIC_FONT_FAMILY, build_scientific_canvas
from visualization.static_assets import (
    dashboard_style,
    html_section,
    html_table,
    load_json,
    svg_rect,
    svg_text,
    write_dashboard,
    write_svg,
)


def render_comparison_pages(run_root: str | Path) -> dict[str, Path]:
    root = Path(run_root)
    comparison_root = root / "comparison"
    summaries_root = comparison_root / "summaries"
    pages_root = comparison_root / "pages"
    figures_root = comparison_root / "figures"
    reports_root = comparison_root / "reports"
    pages_root.mkdir(parents=True, exist_ok=True)
    if not (summaries_root / "progress_matrix.json").exists():
        build_comparison_summaries(root)

    mode_scoreboard = load_json(summaries_root / "mode_scoreboard.json")
    seed_delta_table = load_json(summaries_root / "seed_delta_table.json")
    progress_matrix = load_json(summaries_root / "progress_matrix.json")
    field_alignment = load_json(summaries_root / "field_alignment.json")
    pareto_comparison = load_json(summaries_root / "pareto_comparison.json")
    controller_path = summaries_root / "controller_comparison.json"
    controller_comparison = load_json(controller_path) if controller_path.exists() else {"rows": []}

    progress_figure = write_svg(figures_root / "progress.svg", _render_progress_figure(mode_scoreboard, progress_matrix))
    fields_figure = write_svg(figures_root / "fields.svg", _render_fields_figure(root, field_alignment))
    reports_root.mkdir(parents=True, exist_ok=True)
    comparison_markdown = reports_root / "comparison_summary.md"
    comparison_markdown.write_text(
        _build_comparison_markdown(mode_scoreboard, seed_delta_table, field_alignment),
        encoding="utf-8",
    )
    comparison_report = write_dashboard(
        reports_root / "comparison_summary.html",
        "Comparison Summary",
        "<main>"
        + html_section("Progress Figure", _figure_card("../figures/progress.svg", "Evaluation-budget progress across modes."))
        + html_section("Field Figure", _figure_card("../figures/fields.svg", "Representative field alignment across modes."))
        + "</main>",
        style=dashboard_style(),
    )

    outputs = {
        "index": write_dashboard(
            pages_root / "index.html",
            "Comparison Overview",
            "<main>"
            + html_section("Overview Figure", _figure_card("../figures/progress.svg", "Cross-mode progress figure."))
            + html_section(
                "Mode Scoreboard",
                html_table(
                    ["Mode", "Seeds", "Mean First Feasible", "Mean Pareto Size", "Best Peak", "Best Gradient"],
                    [
                        [
                            str(row.get("mode_id", "")),
                            str(row.get("seed_count", "")),
                            _format_nested_metric(row, "first_feasible_eval_stats"),
                            _format_nested_metric(row, "pareto_size_stats"),
                            _format_nested_metric(row, "best_peak_stats"),
                            _format_nested_metric(row, "best_gradient_stats"),
                        ]
                        for row in mode_scoreboard.get("rows", [])
                    ],
                ),
            )
            + "</main>",
            style=dashboard_style(),
        ),
        "progress": write_dashboard(
            pages_root / "progress.html",
            "Comparison Progress",
            "<main>"
            + html_section("Progress Figure", _figure_card("../figures/progress.svg", "Best-so-far and feasibility progress by evaluation index."))
            + html_section(
                "First Feasible And Progress",
                html_table(
                    ["Mode", "Seed", "First Feasible", "Pareto Size", "Final Budget Fraction"],
                    [
                        [
                            str(row.get("mode_id", "")),
                            str(row.get("seed", "")),
                            str(row.get("first_feasible_eval", "")),
                            str(row.get("pareto_size", "")),
                            _format_budget_fraction(progress_matrix, str(row.get("mode_id", "")), int(row.get("seed", 0))),
                        ]
                        for row in seed_delta_table.get("rows", [])
                    ],
                ),
            )
            + "</main>",
            style=dashboard_style(),
        ),
        "fields": write_dashboard(
            pages_root / "fields.html",
            "Comparison Fields",
            "<main>"
            + html_section("Field Figure", _figure_card("../figures/fields.svg", "Representative field alignment and hotspot comparison."))
            + html_section(
                "Field Alignment",
                html_table(
                    ["Mode", "Seed", "Representative", "Temperature Grid", "Gradient Grid", "Hotspot"],
                    [
                        [
                            str(row.get("mode_id", "")),
                            str(row.get("seed", "")),
                            str(row.get("representative_id", "")),
                            _format_grid_shape(row.get("temperature_grid_shape")),
                            _format_grid_shape(row.get("gradient_grid_shape")),
                            _format_hotspot(row.get("hotspot")),
                        ]
                        for row in field_alignment.get("rows", [])
                    ]
                    or [["No aligned representatives", "", "", "", "", ""]],
                ),
            )
            + "</main>",
            style=dashboard_style(),
        ),
        "pareto": write_dashboard(
            pages_root / "pareto.html",
            "Comparison Pareto",
            "<main>"
            + html_section(
                "Pareto Comparison",
                html_table(
                    ["Mode", "Seed", "Pareto Size"],
                    [
                        [str(row.get("mode_id", "")), str(row.get("seed", "")), str(row.get("pareto_size", ""))]
                        for row in pareto_comparison.get("rows", [])
                    ],
                ),
            )
            + "</main>",
            style=dashboard_style(),
        ),
        "seeds": write_dashboard(
            pages_root / "seeds.html",
            "Comparison Seeds",
            "<main>"
            + html_section(
                "Seed Delta Table",
                html_table(
                    ["Mode", "Seed", "Best Peak", "Best Gradient"],
                    [
                        [
                            str(row.get("mode_id", "")),
                            str(row.get("seed", "")),
                            str(row.get("best_temperature_max", "")),
                            str(row.get("best_gradient_rms", "")),
                        ]
                        for row in seed_delta_table.get("rows", [])
                    ],
                ),
            )
            + "</main>",
            style=dashboard_style(),
        ),
        "progress_figure": progress_figure,
        "fields_figure": fields_figure,
        "report": comparison_report,
    }
    if controller_comparison.get("rows"):
        outputs["controller"] = write_dashboard(
            pages_root / "controller.html",
            "Comparison Controller",
            "<main>"
            + html_section(
                "Controller Comparison",
                html_table(
                    ["Mode", "Seed", "Selected Operators"],
                    [
                        [
                            str(row.get("mode_id", "")),
                            str(row.get("seed", "")),
                            ", ".join(sorted(dict(row.get("selected_operator_counts", {})).keys())),
                        ]
                        for row in controller_comparison.get("rows", [])
                    ],
                ),
            )
            + "</main>",
            style=dashboard_style(),
        )
    return outputs


def _render_progress_figure(mode_scoreboard: dict[str, Any], progress_matrix: dict[str, Any]) -> str:
    rows = list(mode_scoreboard.get("rows", []))
    summary_line = "; ".join(
        f"{str(row.get('mode_id', 'mode'))}: feasible {_format_nested_metric(row, 'first_feasible_eval_stats')}, pareto {_format_nested_metric(row, 'pareto_size_stats')}"
        for row in rows
    ) or "No progress rows"
    figure_body = [
        svg_text(
            60.0,
            40.0,
            "Cross-mode progress comparison",
            fill=SCIENTIFIC_COLORS["ink"],
            size=24,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            60.0,
            64.0,
            "Mode means are compared on the same evaluation axis and the same progress metrics.",
            fill=SCIENTIFIC_COLORS["muted"],
            size=12,
            weight="500",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
    ]
    for index, line in enumerate(wrap_text_lines(summary_line, max_chars=110, max_lines=2)):
        figure_body.append(
            svg_text(
                60.0,
                86.0 + float(index) * 16.0,
                line,
                fill=SCIENTIFIC_COLORS["muted"],
                size=11,
                weight="500",
                font_family=SCIENTIFIC_FONT_FAMILY,
            )
        )
    markers = _build_comparison_markers(rows)
    panel_specs = [
        ("Best Peak vs Evaluation", "best_temperature_max_so_far", 60.0, 126.0, _format_progress_value),
        ("Best Gradient vs Evaluation", "best_gradient_rms_so_far", 500.0, 126.0, _format_progress_value),
        ("Feasible Rate vs Evaluation", "feasible_rate_so_far", 60.0, 392.0, _format_rate_value),
        ("Pareto Size vs Evaluation", "pareto_size_so_far", 500.0, 392.0, _format_count_value),
    ]
    for title, metric_key, panel_x, panel_y, formatter in panel_specs:
        figure_body.append(
            render_progress_panel(
                title=title,
                series=_build_comparison_series(progress_matrix, metric_key),
                x=panel_x,
                y=panel_y,
                width=380.0,
                height=220.0,
                milestones=markers,
                value_formatter=formatter,
            )
        )
    return build_scientific_canvas(
        title="Comparison progress",
        width=980,
        height=700,
        body="".join(figure_body),
    )


def _render_fields_figure(run_root: Path, field_alignment: dict[str, Any]) -> str:
    selected_rows = _select_aligned_field_rows(field_alignment)
    temperature_min = min((float(row.get("temperature_min")) for row in selected_rows if row.get("temperature_min") is not None), default=0.0)
    temperature_max = max((float(row.get("temperature_max")) for row in selected_rows if row.get("temperature_max") is not None), default=1.0)
    gradient_min = min((float(row.get("gradient_min")) for row in selected_rows if row.get("gradient_min") is not None), default=0.0)
    gradient_max = max((float(row.get("gradient_max")) for row in selected_rows if row.get("gradient_max") is not None), default=1.0)
    shared_seed = {int(row.get("seed", 0)) for row in selected_rows}
    seed_text = f"seed-{next(iter(shared_seed))}" if len(shared_seed) == 1 and shared_seed else "aligned representatives"
    figure_body = [
        svg_text(
            60.0,
            40.0,
            "Representative field comparison",
            fill=SCIENTIFIC_COLORS["ink"],
            size=24,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            60.0,
            64.0,
            f"Temperature and gradient panels use the same scale across modes for {seed_text}.",
            fill=SCIENTIFIC_COLORS["muted"],
            size=12,
            weight="500",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            60.0,
            106.0,
            "Temperature",
            fill=SCIENTIFIC_COLORS["ink"],
            size=14,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            60.0,
            392.0,
            "Gradient",
            fill=SCIENTIFIC_COLORS["ink"],
            size=14,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            810.0,
            106.0,
            "Shared Color Scale",
            fill=SCIENTIFIC_COLORS["ink"],
            size=14,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
    ]
    for index, row in enumerate(selected_rows):
        panel_x = 60.0 + float(index) * 228.0
        figure_body.append(
            _render_field_comparison_panel(
                run_root=run_root,
                row=row,
                grid_key="temperature_grid_path",
                title=str(row.get("mode_id", "mode")),
                subtitle=f"seed-{int(row.get('seed', 0))} / {str(row.get('representative_id', 'rep'))}",
                x=panel_x,
                y=126.0,
                width=210.0,
                height=220.0,
                palette=_THERMAL_PALETTE,
                value_min=temperature_min,
                value_max=temperature_max,
                show_hotspot=True,
            )
        )
        figure_body.append(
            _render_field_comparison_panel(
                run_root=run_root,
                row=row,
                grid_key="gradient_grid_path",
                title=str(row.get("mode_id", "mode")),
                subtitle=f"seed-{int(row.get('seed', 0))} / {str(row.get('representative_id', 'rep'))}",
                x=panel_x,
                y=412.0,
                width=210.0,
                height=220.0,
                palette=_GRADIENT_PALETTE,
                value_min=gradient_min,
                value_max=gradient_max,
                show_hotspot=False,
            )
        )
    figure_body.append(
        render_colorbar_panel(
            title="Temperature",
            value_min=temperature_min,
            value_max=temperature_max,
            x=810.0,
            y=128.0,
            width=120.0,
            height=220.0,
        )
    )
    figure_body.append(
        render_colorbar_panel(
            title="Gradient",
            value_min=gradient_min,
            value_max=gradient_max,
            x=810.0,
            y=414.0,
            width=120.0,
            height=220.0,
        )
    )
    return build_scientific_canvas(
        title="Comparison fields",
        width=980,
        height=700,
        body="".join(figure_body),
    )


def _build_comparison_markdown(
    mode_scoreboard: dict[str, Any],
    seed_delta_table: dict[str, Any],
    field_alignment: dict[str, Any],
) -> str:
    lines = [
        "# Comparison Summary",
        "",
        "| Mode | Mean First Feasible | Mean Pareto Size | Best Peak | Best Gradient |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in mode_scoreboard.get("rows", []):
        lines.append(
            f"| {row.get('mode_id', '')} | {_format_nested_metric(row, 'first_feasible_eval_stats')} | {_format_nested_metric(row, 'pareto_size_stats')} | {_format_nested_metric(row, 'best_peak_stats')} | {_format_nested_metric(row, 'best_gradient_stats')} |"
        )
    lines.extend(["", "## Seed Delta Rows", ""])
    for row in seed_delta_table.get("rows", []):
        lines.append(
            f"- {row.get('mode_id', '')} seed-{row.get('seed', '')}: first feasible {row.get('first_feasible_eval', 'n/a')}, pareto {row.get('pareto_size', 'n/a')}, best peak {row.get('best_temperature_max', 'n/a')}, best gradient {row.get('best_gradient_rms', 'n/a')}"
        )
    lines.extend(["", "## Field Alignment", ""])
    for row in field_alignment.get("rows", []):
        lines.append(
            f"- {row.get('mode_id', '')} seed-{row.get('seed', '')}: rep {row.get('representative_id', 'n/a')}, hotspot {_format_hotspot(row.get('hotspot'))}"
        )
    return "\n".join(lines) + "\n"


def _figure_card(src: str, caption: str) -> str:
    return f"<div class='figure-grid'><figure class='figure-card'><img src='{src}' alt='{caption}'/><figcaption>{caption}</figcaption></figure></div>"


_MODE_COLORS = {
    "raw": "#A24A2A",
    "union": "#2E6F5E",
    "llm": "#2F5B9A",
}


def _build_comparison_series(progress_matrix: dict[str, Any], metric_key: str) -> list[dict[str, Any]]:
    rows_by_mode: dict[str, list[list[dict[str, Any]]]] = {}
    for row in progress_matrix.get("rows", []):
        mode_id = str(row.get("mode_id", "mode"))
        rows_by_mode.setdefault(mode_id, []).append(list(row.get("timeline", [])))
    ordered_modes = [mode for mode in ("raw", "union", "llm") if mode in rows_by_mode]
    return [
        {
            "label": mode_id,
            "stroke": _MODE_COLORS.get(mode_id, "#3F5C7A"),
            "points": _build_mode_mean_points(rows_by_mode.get(mode_id, []), metric_key),
        }
        for mode_id in ordered_modes
    ]


def _build_mode_mean_points(timelines: list[list[dict[str, Any]]], metric_key: str) -> list[tuple[float, float | None]]:
    rows_by_eval: dict[int, list[float]] = {}
    for timeline in timelines:
        for row in timeline:
            evaluation_index = int(row.get("evaluation_index", 0))
            metric_value = row.get(metric_key)
            if metric_value is None:
                continue
            rows_by_eval.setdefault(evaluation_index, []).append(float(metric_value))
    return [
        (float(evaluation_index), sum(values) / float(len(values)))
        for evaluation_index, values in sorted(rows_by_eval.items())
    ]


def _build_comparison_markers(mode_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for row in mode_rows:
        stats = dict(row.get("first_feasible_eval_stats", {}))
        if stats.get("mean") is None:
            continue
        markers.append(
            {
                "evaluation_index": float(stats["mean"]),
                "label": str(row.get("mode_id", "mode")),
            }
        )
    return markers


def _select_aligned_field_rows(field_alignment: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in field_alignment.get("rows", [])]
    if not rows:
        return []
    available_modes = {str(row.get("mode_id", "")) for row in rows}
    rows_by_seed: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_seed.setdefault(int(row.get("seed", 0)), []).append(row)
    for seed in sorted(rows_by_seed):
        seed_rows = rows_by_seed[seed]
        seed_modes = {str(row.get("mode_id", "")) for row in seed_rows}
        if seed_modes >= available_modes:
            return _order_mode_rows(seed_rows)
    first_rows_by_mode: dict[str, dict[str, Any]] = {}
    for row in _order_mode_rows(rows):
        first_rows_by_mode.setdefault(str(row.get("mode_id", "")), row)
    return _order_mode_rows(list(first_rows_by_mode.values()))


def _order_mode_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            ("raw", "union", "llm").index(str(row.get("mode_id", "")))
            if str(row.get("mode_id", "")) in ("raw", "union", "llm")
            else 99
        ),
    )


def _render_field_comparison_panel(
    *,
    run_root: Path,
    row: dict[str, Any],
    grid_key: str,
    title: str,
    subtitle: str,
    x: float,
    y: float,
    width: float,
    height: float,
    palette: tuple[tuple[int, int, int], ...],
    value_min: float,
    value_max: float,
    show_hotspot: bool,
) -> str:
    parts = [
        svg_text(
            x,
            y - 22.0,
            title,
            fill=SCIENTIFIC_COLORS["ink"],
            size=13,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            x,
            y - 6.0,
            subtitle,
            fill=SCIENTIFIC_COLORS["muted"],
            size=10,
            weight="500",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_rect(
            x,
            y,
            width,
            height,
            fill="#ffffff",
            stroke=SCIENTIFIC_COLORS["panel_stroke"],
            stroke_width=1.0,
            rx=6.0,
        ),
    ]
    grid_path = run_root / str(row.get(grid_key, ""))
    values = _load_grid(grid_path)
    if values is None:
        parts.append(
            svg_text(
                x + width / 2.0,
                y + height / 2.0,
                "No field data",
                fill=SCIENTIFIC_COLORS["muted"],
                size=12,
                weight="500",
                anchor="middle",
                font_family=SCIENTIFIC_FONT_FAMILY,
            )
        )
        return "".join(parts)
    inset = 8.0
    sampled = _downsample_grid(values, max_rows=36, max_cols=36)
    parts.append(
        _render_heatmap_cells(
            sampled,
            x=x + inset,
            y=y + inset,
            width=width - 2.0 * inset,
            height=height - 2.0 * inset,
            palette=palette,
            value_min=value_min,
            value_max=value_max,
        )
    )
    panel_domain = dict(row.get("panel_domain", {}))
    layout = dict(row.get("layout", {}))
    hotspot = dict(row.get("hotspot", {})) if show_hotspot else {}
    domain_width = float(panel_domain.get("width", 1.0))
    domain_height = float(panel_domain.get("height", 1.0))
    parts.extend(
        _render_layout_overlay(
            list(layout.get("components", [])),
            list(layout.get("line_sinks", [])),
            hotspot,
            domain_width,
            domain_height,
            x + inset,
            y + inset,
            width - 2.0 * inset,
            height - 2.0 * inset,
            stroke_only=True,
        )
    )
    return "".join(parts)


def _format_progress_value(value: float) -> str:
    return f"{float(value):.3f}"


def _format_rate_value(value: float) -> str:
    return f"{float(value):.2f}"


def _format_count_value(value: float) -> str:
    return f"{float(value):.0f}"


def _nested_mean(row: dict[str, Any], key: str) -> float | None:
    payload = dict(row.get(key, {}))
    mean_value = payload.get("mean")
    return None if mean_value is None else float(mean_value)


def _format_budget_fraction(progress_matrix: dict, mode_id: str, seed: int) -> str:
    for row in progress_matrix.get("rows", []):
        if str(row.get("mode_id")) == mode_id and int(row.get("seed", 0)) == seed:
            timeline = list(row.get("timeline", []))
            if timeline:
                return f"{float(timeline[-1].get('budget_fraction', 0.0)):.2f}"
    return "n/a"


def _format_grid_shape(value: object) -> str:
    if not isinstance(value, list):
        return "n/a"
    return " x ".join(str(int(item)) for item in value)


def _format_hotspot(value: object) -> str:
    if not isinstance(value, dict):
        return "n/a"
    return f"({float(value.get('x', 0.0)):.2f}, {float(value.get('y', 0.0)):.2f})"


def _format_nested_metric(row: dict, key: str) -> str:
    payload = dict(row.get(key, {}))
    mean_value = payload.get("mean")
    if mean_value is None:
        return "n/a"
    return f"{float(mean_value):.2f}"


def _hotspot_axis(row: dict[str, Any], axis: str) -> float | None:
    hotspot = row.get("hotspot")
    if not isinstance(hotspot, dict):
        return None
    value = hotspot.get(axis)
    return None if value is None else float(value)


def _as_float(value: Any) -> float | None:
    return None if value is None else float(value)
