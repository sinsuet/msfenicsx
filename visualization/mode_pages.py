"""Mode-level page renderers for the new s1_typical run tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from optimizers.mode_summary import build_mode_summaries
from visualization.case_pages import render_case_page
from visualization.static_assets import dashboard_style, html_list, html_section, load_json, write_dashboard


def render_mode_pages(mode_root: str | Path) -> dict[str, Path]:
    root = Path(mode_root)
    seed_summary_path = root / "summaries" / "seed_summary.json"
    mode_summary_path = root / "summaries" / "mode_summary.json"
    if not seed_summary_path.exists() or not mode_summary_path.exists():
        build_mode_summaries(root)
    seed_summary = load_json(seed_summary_path)
    mode_summary = load_json(mode_summary_path)

    sections: list[str] = [
        "<main>",
        (
            "<section class='hero'>"
            f"<h1>Mode: {mode_summary.get('mode_id', root.name)}</h1>"
            "<p>Seed-level progress index for representative physical-field bundles.</p>"
            "</section>"
        ),
    ]
    for seed_row in seed_summary.get("rows", []):
        seed_root = root / "seeds" / f"seed-{int(seed_row['seed'])}"
        representative_links: list[str] = []
        for representative_id in seed_row.get("representatives", []):
            representative_root = seed_root / "representatives" / representative_id
            render_case_page(representative_root)
            representative_links.append(
                f"{representative_id} -> representatives/{representative_id}/pages/index.html"
            )
        sections.append(
            html_section(
                f"seed-{int(seed_row['seed'])}",
                "<p>"
                f"First feasible eval: {seed_row.get('first_feasible_eval', 'n/a')} | "
                f"Pareto size: {seed_row.get('pareto_size', 'n/a')}"
                "</p>"
                + html_list(representative_links or ["No representatives"]),
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
        )
    }
