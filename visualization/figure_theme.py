"""Theme tokens and canvas helpers for scientific figure exports."""

from __future__ import annotations

import html

SCIENTIFIC_COLORS: dict[str, str] = {
    "background": "#FFFFFF",
    "ink": "#1A1A1A",
    "muted": "#666666",
    "panel_stroke": "#C8C8C8",
    "panel_fill": "#FFFFFF",
}

SCIENTIFIC_FONT_FAMILY = "Arial, Helvetica, 'DejaVu Sans', sans-serif"

SCIENTIFIC_EXPORT_PRESETS: dict[str, tuple[int, int]] = {
    "web": (980, 660),
    "report": (1200, 780),
    "paper": (1000, 700),
}


def build_scientific_canvas(
    *,
    title: str,
    width: int,
    height: int,
    body: str,
    description: str | None = None,
) -> str:
    escaped_title = html.escape(title)
    escaped_description = html.escape(description or f"{title} scientific figure export")
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'"
        f" role='img' aria-labelledby='title desc'>"
        f"<title>{escaped_title}</title>"
        f"<desc>{escaped_description}</desc>"
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='{SCIENTIFIC_COLORS['background']}'/>"
        f"{body}</svg>"
    )
