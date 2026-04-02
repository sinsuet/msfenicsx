"""Mode-level page renderers for the new s1_typical run tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from optimizers.mode_summary import build_mode_summaries
from optimizers.run_telemetry import load_jsonl_rows
from visualization.case_pages import render_case_page
from visualization.figure_axes import render_progress_panel
from visualization.figure_text import wrap_text_lines
from visualization.figure_theme import SCIENTIFIC_COLORS, SCIENTIFIC_FONT_FAMILY, build_scientific_canvas
from visualization.static_assets import (
    dashboard_style,
    html_section,
    html_table,
    load_json,
    svg_text,
    write_dashboard,
    write_svg,
)


def render_mode_pages(mode_root: str | Path) -> dict[str, Path]:
    root = Path(mode_root)
    seed_summary_path = root / "summaries" / "seed_summary.json"
    mode_summary_path = root / "summaries" / "mode_summary.json"
    if not seed_summary_path.exists() or not mode_summary_path.exists():
        build_mode_summaries(root)
    seed_summary = load_json(seed_summary_path)
    mode_summary = load_json(mode_summary_path)
    seed_progress = _load_seed_progress_payloads(root, seed_summary)

    figures_root = root / "figures"
    reports_root = root / "reports"
    figure_path = write_svg(figures_root / "mode-summary.svg", _render_mode_summary_figure(mode_summary, seed_progress))
    markdown_path = reports_root / "mode_summary.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_build_mode_markdown(mode_summary, seed_summary), encoding="utf-8")
    report_path = write_dashboard(
        reports_root / "mode_summary.html",
        f"{mode_summary.get('mode_id', root.name)} Mode Summary",
        "<main>"
        + html_section("Mode Summary Figure", _figure_card("../figures/mode-summary.svg", "Seed-aligned overview for this mode."))
        + html_section(
            "Seed Metrics",
            html_table(
                ["Seed", "First Feasible Eval", "Pareto Size", "Best Peak", "Best Gradient", "Representatives"],
                [
                    [
                        f"seed-{int(row['seed'])}",
                        str(row.get("first_feasible_eval", "n/a")),
                        str(row.get("pareto_size", "n/a")),
                        _format_final_metric(row, "best_temperature_max_so_far"),
                        _format_final_metric(row, "best_gradient_rms_so_far"),
                        ", ".join(str(item) for item in row.get("representatives", [])) or "n/a",
                    ]
                    for row in seed_summary.get("rows", [])
                ],
            ),
        )
        + "</main>",
        style=dashboard_style(),
    )

    sections: list[str] = [
        "<main>",
        (
            "<section class='hero'>"
            f"<h1>Mode: {mode_summary.get('mode_id', root.name)}</h1>"
            "<p>Seed-level progress index for representative physical-field bundles.</p>"
            "</section>"
        ),
        html_section("Overview Figure", _figure_card("../figures/mode-summary.svg", "Per-mode summary image for quick review.")),
        html_section(
            "Mode Scoreboard",
            html_table(
                ["Metric", "Value"],
                [
                    ["Seed Count", str(mode_summary.get("seed_count", 0))],
                    ["Mean First Feasible", _format_stats(mode_summary.get("first_feasible_eval_stats", {}))],
                    ["Mean Pareto Size", _format_stats(mode_summary.get("pareto_size_stats", {}))],
                    ["Best Peak", _format_stats(mode_summary.get("best_peak_stats", {}))],
                    ["Best Gradient", _format_stats(mode_summary.get("best_gradient_stats", {}))],
                ],
            ),
        ),
    ]
    for seed_row in seed_summary.get("rows", []):
        seed_root = root / "seeds" / f"seed-{int(seed_row['seed'])}"
        representative_links: list[str] = []
        for representative_id in seed_row.get("representatives", []):
            representative_root = seed_root / "representatives" / representative_id
            render_case_page(representative_root)
            representative_links.append(
                f"<li><a href='../seeds/seed-{int(seed_row['seed'])}/representatives/{representative_id}/pages/index.html'>{representative_id}</a></li>"
            )
        sections.append(
            html_section(
                f"seed-{int(seed_row['seed'])}",
                "<p>"
                f"First feasible eval: {seed_row.get('first_feasible_eval', 'n/a')} | "
                f"Pareto size: {seed_row.get('pareto_size', 'n/a')}"
                "</p>"
                + ("<ul>" + "".join(representative_links) + "</ul>" if representative_links else "<p>No representatives</p>"),
            )
        )
    sections.append("</main>")
    output_path = root / "pages" / "index.html"
    return {
        "index": write_dashboard(
            output_path,
            f"{mode_summary.get('mode_id', root.name)} Mode Page",
            "".join(sections),
            style=dashboard_style(),
        ),
        "figure": figure_path,
        "report": report_path,
    }


def _render_mode_summary_figure(mode_summary: dict[str, Any], seed_progress: list[dict[str, Any]]) -> str:
    mode_id = str(mode_summary.get("mode_id", "mode"))
    width = 980
    height = 700
    mode_color = _MODE_COLORS.get(mode_id, "#3F5C7A")
    figure_body: list[str] = [
        svg_text(
            60.0,
            40.0,
            f"{mode_id} mode progress summary",
            fill=SCIENTIFIC_COLORS["ink"],
            size=24,
            weight="600",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
        svg_text(
            60.0,
            64.0,
            (
                f"Seeds {mode_summary.get('seed_count', 0)} | "
                f"Mean first feasible { _format_stats(mode_summary.get('first_feasible_eval_stats', {})) } | "
                f"Mean pareto { _format_stats(mode_summary.get('pareto_size_stats', {})) }"
            ),
            fill=SCIENTIFIC_COLORS["muted"],
            size=12,
            weight="500",
            font_family=SCIENTIFIC_FONT_FAMILY,
        ),
    ]
    milestone_lines = wrap_text_lines(_build_mode_milestone_summary(seed_progress), max_chars=110, max_lines=2)
    for index, line in enumerate(milestone_lines):
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

    markers = _build_first_feasible_markers(seed_progress)
    panel_specs = [
        (
            "Best Peak vs Evaluation",
            "best_temperature_max_so_far",
            60.0,
            126.0,
            _format_progress_value,
        ),
        (
            "Best Gradient vs Evaluation",
            "best_gradient_rms_so_far",
            500.0,
            126.0,
            _format_progress_value,
        ),
        (
            "Feasible Rate vs Evaluation",
            "feasible_rate_so_far",
            60.0,
            392.0,
            _format_rate_value,
        ),
        (
            "Pareto Size vs Evaluation",
            "pareto_size_so_far",
            500.0,
            392.0,
            _format_count_value,
        ),
    ]
    for title, metric_key, panel_x, panel_y, formatter in panel_specs:
        figure_body.append(
            render_progress_panel(
                title=title,
                series=_build_metric_series(seed_progress, metric_key, mode_color),
                x=panel_x,
                y=panel_y,
                width=380.0,
                height=220.0,
                milestones=markers,
                value_formatter=formatter,
            )
        )
    return build_scientific_canvas(
        title=f"{mode_id} summary",
        width=width,
        height=height,
        body="".join(figure_body),
    )


def _build_mode_markdown(mode_summary: dict[str, Any], seed_summary: dict[str, Any]) -> str:
    lines = [
        f"# {mode_summary.get('mode_id', 'mode')} Mode Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Seed Count | {mode_summary.get('seed_count', 0)} |",
        f"| Mean First Feasible | {_format_stats(mode_summary.get('first_feasible_eval_stats', {}))} |",
        f"| Mean Pareto Size | {_format_stats(mode_summary.get('pareto_size_stats', {}))} |",
        f"| Best Peak | {_format_stats(mode_summary.get('best_peak_stats', {}))} |",
        f"| Best Gradient | {_format_stats(mode_summary.get('best_gradient_stats', {}))} |",
        "",
        "## Seed Rows",
        "",
    ]
    for row in seed_summary.get("rows", []):
        lines.append(
            f"- seed-{int(row['seed'])}: first feasible {row.get('first_feasible_eval', 'n/a')}, "
            f"pareto {row.get('pareto_size', 'n/a')}, representatives {', '.join(str(item) for item in row.get('representatives', [])) or 'none'}"
        )
    return "\n".join(lines) + "\n"


def _figure_card(src: str, caption: str) -> str:
    return f"<div class='figure-grid'><figure class='figure-card'><img src='{src}' alt='{caption}'/><figcaption>{caption}</figcaption></figure></div>"


def _format_final_metric(row: dict[str, Any], key: str) -> str:
    payload = dict(row.get("final_timeline", {}))
    value = payload.get(key)
    return "n/a" if value is None else f"{float(value):.3f}"


def _format_stats(payload: dict[str, Any]) -> str:
    mean_value = payload.get("mean")
    return "n/a" if mean_value is None else f"{float(mean_value):.2f}"


def _as_float(value: Any) -> float | None:
    return None if value is None else float(value)


_MODE_COLORS = {
    "raw": "#A24A2A",
    "union": "#2E6F5E",
    "llm": "#2F5B9A",
}

_SEED_TRAJECTORY_COLORS = (
    "#B8C0C8",
    "#8E99A5",
    "#667381",
)


def _load_seed_progress_payloads(mode_root: Path, seed_summary: dict[str, Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for row in seed_summary.get("rows", []):
        timeline_path = mode_root / str(row.get("progress_timeline", ""))
        milestones_path = mode_root / str(row.get("milestones", ""))
        payloads.append(
            {
                "seed": int(row["seed"]),
                "first_feasible_eval": row.get("first_feasible_eval"),
                "pareto_size": row.get("pareto_size"),
                "representatives": list(row.get("representatives", [])),
                "timeline": load_jsonl_rows(timeline_path) if timeline_path.exists() else [],
                "milestones": list(load_json(milestones_path).get("rows", [])) if milestones_path.exists() else [],
            }
        )
    return payloads


def _build_metric_series(
    seed_progress: list[dict[str, Any]],
    metric_key: str,
    mode_color: str,
) -> list[dict[str, Any]]:
    if not seed_progress:
        return [{"label": "mode mean", "stroke": mode_color, "points": []}]
    if len(seed_progress) == 1:
        payload = seed_progress[0]
        return [
            {
                "label": f"s{int(payload['seed'])}",
                "stroke": mode_color,
                "points": _extract_metric_points(list(payload.get("timeline", [])), metric_key),
            }
        ]
    series = [
        {
            "label": f"s{int(payload['seed'])}",
            "stroke": _SEED_TRAJECTORY_COLORS[index % len(_SEED_TRAJECTORY_COLORS)],
            "points": _extract_metric_points(list(payload.get("timeline", [])), metric_key),
        }
        for index, payload in enumerate(seed_progress)
    ]
    series.append(
        {
            "label": "mean",
            "stroke": mode_color,
            "points": _build_mean_metric_points(seed_progress, metric_key),
        }
    )
    return series


def _extract_metric_points(timeline: list[dict[str, Any]], metric_key: str) -> list[tuple[float, float | None]]:
    return [
        (
            float(row.get("evaluation_index", 0.0)),
            None if row.get(metric_key) is None else float(row.get(metric_key)),
        )
        for row in timeline
    ]


def _build_mean_metric_points(
    seed_progress: list[dict[str, Any]],
    metric_key: str,
) -> list[tuple[float, float | None]]:
    rows_by_eval: dict[int, list[float]] = {}
    for payload in seed_progress:
        for row in payload.get("timeline", []):
            evaluation_index = int(row.get("evaluation_index", 0))
            metric_value = row.get(metric_key)
            if metric_value is None:
                continue
            rows_by_eval.setdefault(evaluation_index, []).append(float(metric_value))
    return [
        (float(evaluation_index), sum(values) / float(len(values)))
        for evaluation_index, values in sorted(rows_by_eval.items())
    ]


def _build_first_feasible_markers(seed_progress: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    single_seed = len(seed_progress) == 1
    for payload in seed_progress:
        first_feasible_eval = payload.get("first_feasible_eval")
        if first_feasible_eval is None:
            continue
        markers.append(
            {
                "evaluation_index": float(first_feasible_eval),
                "label": "first feasible" if single_seed else f"s{int(payload['seed'])}",
            }
        )
    return markers


def _build_mode_milestone_summary(seed_progress: list[dict[str, Any]]) -> str:
    if not seed_progress:
        return "Milestones: none"
    rows: list[str] = []
    for payload in seed_progress[:3]:
        pareto_evals = [
            str(int(row.get("evaluation_index", 0)))
            for row in payload.get("milestones", [])
            if str(row.get("trigger_type", "")) == "pareto_expansion"
        ][:3]
        descriptors: list[str] = []
        if payload.get("first_feasible_eval") is not None:
            descriptors.append(f"feasible@{int(payload['first_feasible_eval'])}")
        if pareto_evals:
            descriptors.append(f"pareto@{','.join(pareto_evals)}")
        representatives = list(payload.get("representatives", []))
        if representatives:
            descriptors.append(f"reps={','.join(str(item) for item in representatives[:2])}")
        rows.append(f"s{int(payload['seed'])} " + " ".join(descriptors or ["no milestones"]))
    return "Milestones: " + "; ".join(rows)


def _format_progress_value(value: float) -> str:
    return f"{float(value):.3f}"


def _format_rate_value(value: float) -> str:
    return f"{float(value):.2f}"


def _format_count_value(value: float) -> str:
    return f"{float(value):.0f}"
