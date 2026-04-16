"""Animated GIF of component layouts across generations, with frame pngs preserved."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter
from matplotlib.patches import Rectangle

from visualization.style.baseline import DPI_DEFAULT, PALETTE_CATEGORICAL, apply_baseline


def render_layout_evolution(
    *,
    frames: Sequence[dict],
    output_gif: Path,
    frames_dir: Path,
    fps: float = 2.0,
) -> None:
    """Render an animated GIF plus `frames_dir/gen_<NNN>.png` for each frame.

    `frames[i]` is `{"generation": int, "components": [{"x": float, "y": float,
    "w": float, "h": float}, ...]}`.
    """
    apply_baseline()
    output_gif = Path(output_gif)
    frames_dir = Path(frames_dir)
    output_gif.parent.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    writer = PillowWriter(fps=fps)
    with writer.saving(fig, str(output_gif), dpi=DPI_DEFAULT):
        for frame in frames:
            ax.cla()
            ax.set_xlim(0.0, 1.0)
            ax.set_ylim(0.0, 1.0)
            ax.set_aspect("equal")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_title(f"gen {int(frame['generation'])}")
            for idx, comp in enumerate(frame["components"]):
                rect = Rectangle(
                    (comp["x"] - comp["w"] / 2, comp["y"] - comp["h"] / 2),
                    comp["w"],
                    comp["h"],
                    facecolor=PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)],
                    edgecolor="black",
                    linewidth=0.4,
                    alpha=0.8,
                )
                ax.add_patch(rect)
            writer.grab_frame()
            frame_path = frames_dir / f"gen_{int(frame['generation']):03d}.png"
            fig.savefig(frame_path, dpi=DPI_DEFAULT)
    plt.close(fig)
