"""Layout snapshots and animated GIF progression."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter
from matplotlib.patches import Polygon as PolygonPatch, Rectangle

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.figures.spatial_annotations import (
    draw_component_labels,
    draw_metadata_panel,
    draw_sink_ribbons,
    hide_spatial_axes,
)
from visualization.style.baseline import (
    DPI_DEFAULT,
    DPI_HIRES,
    SPATIAL_LAYOUT_FILL,
    SPATIAL_LAYOUT_OUTLINE,
    apply_baseline,
)


def render_layout_evolution(
    *,
    frames: Sequence[dict],
    output_gif: Path,
    frames_dir: Path,
    fps: float = 2.0,
) -> None:
    """Render an animated GIF plus `frames_dir/step_<NNN>.png` for each frame.

    `frames[i]` is a paper-facing spatial milestone rather than a raw
    generation snapshot.
    """
    apply_baseline()
    output_gif = Path(output_gif)
    frames_dir = Path(frames_dir)
    output_gif.parent.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(3.5, 3.5))

    writer = PillowWriter(fps=fps)
    with writer.saving(fig, str(output_gif), dpi=DPI_DEFAULT):
        for frame_index, frame in enumerate(frames):
            draw_layout_board(ax, frame)
            writer.grab_frame()
            frame_id = int(frame.get("frame_index", frame_index))
            frame_path = frames_dir / f"step_{frame_id:03d}.png"
            fig.savefig(frame_path, dpi=DPI_DEFAULT)
    plt.close(fig)


def render_layout_snapshot(
    *,
    frame: dict,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    output = ensure_output_parent(Path(output))

    panel_meta = dict(frame.get("panel_meta", {}))
    if panel_meta:
        fig, (board_ax, info_ax) = plt.subplots(
            1,
            2,
            figsize=(4.8, 3.5),
            gridspec_kw={"width_ratios": [4.1, 1.35]},
        )
        draw_layout_board(board_ax, frame)
        draw_metadata_panel(info_ax, panel_meta)
    else:
        fig, board_ax = plt.subplots(figsize=(3.5, 3.5))
        draw_layout_board(board_ax, frame)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def draw_layout_board(ax, frame: dict) -> None:
    ax.cla()
    width = float(frame.get("panel_width", 1.0))
    height = float(frame.get("panel_height", 1.0))
    title = frame.get("title")
    if title:
        title_text = str(title)
    else:
        title_text = f"gen {int(frame['generation'])}"
    hide_spatial_axes(ax, width=width, height=height, title=title_text)
    for idx, comp in enumerate(frame.get("components", [])):
        outline = comp.get("outline")
        if outline:
            patch = PolygonPatch(
                outline,
                closed=True,
                facecolor=SPATIAL_LAYOUT_FILL,
                edgecolor=SPATIAL_LAYOUT_OUTLINE,
                linewidth=0.7,
                alpha=0.92,
            )
            ax.add_patch(patch)
            continue
        rect = Rectangle(
            (comp["x"] - comp["w"] / 2, comp["y"] - comp["h"] / 2),
            comp["w"],
            comp["h"],
            facecolor=SPATIAL_LAYOUT_FILL,
            edgecolor=SPATIAL_LAYOUT_OUTLINE,
            linewidth=0.7,
            alpha=0.92,
        )
        ax.add_patch(rect)
    draw_component_labels(ax, frame.get("components", []), mode="layout")
    draw_sink_ribbons(ax, frame.get("line_sinks", []), width=width, height=height)
