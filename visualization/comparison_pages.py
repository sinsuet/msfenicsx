"""Mixed-mode comparison page renderers for the new s1_typical run tree."""

from __future__ import annotations

from pathlib import Path

from optimizers.comparison_summary import build_comparison_summaries
from visualization.static_assets import dashboard_style, html_section, html_table, load_json, write_dashboard


def render_comparison_pages(run_root: str | Path) -> dict[str, Path]:
    root = Path(run_root)
    comparison_root = root / "comparison"
    summaries_root = comparison_root / "summaries"
    pages_root = comparison_root / "pages"
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

    outputs = {
        "index": write_dashboard(
            pages_root / "index.html",
            "Comparison Overview",
            "<main>"
            + html_section(
                "Mode Scoreboard",
                html_table(
                    ["Mode", "Seeds", "Mean First Feasible", "Mean Pareto Size"],
                    [
                        [
                            str(row.get("mode_id", "")),
                            str(row.get("seed_count", "")),
                            _format_nested_metric(row, "first_feasible_eval_stats"),
                            _format_nested_metric(row, "pareto_size_stats"),
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
            + html_section(
                "Field Alignment",
                html_table(
                    ["Mode", "Seed", "Temperature Grid", "Gradient Grid", "Hotspot"],
                    [
                        [
                            str(row.get("mode_id", "")),
                            str(row.get("seed", "")),
                            _format_grid_shape(row.get("temperature_grid_shape")),
                            _format_grid_shape(row.get("gradient_grid_shape")),
                            _format_hotspot(row.get("hotspot")),
                        ]
                        for row in field_alignment.get("rows", [])
                    ],
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
