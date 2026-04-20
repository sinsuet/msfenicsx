"""Hypervolume progress curve; single-run and multi-seed IQR-band variants."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.style.baseline import (
    DPI_DEFAULT,
    DPI_HIRES,
    PALETTE_CATEGORICAL,
    apply_baseline,
)


def render_hypervolume_progress(
    *,
    series: dict[str, Sequence[tuple[int, float]]],
    output: Path,
    hires: bool = False,
) -> None:
    """Render `{mode: [(generation, hv), ...]}` as a line plot."""
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.5, 2.6))

    for idx, (mode, points) in enumerate(series.items()):
        if not points:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        ax.plot(xs, ys, color=color, linewidth=1.2, label=mode)

    ax.set_xlabel("Generation")
    ax.set_ylabel("Hypervolume")
    if len(series) > 1:
        ax.legend()

    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def render_hypervolume_iqr_band(
    *,
    generations: Sequence[int],
    median: Sequence[float],
    p25: Sequence[float],
    p75: Sequence[float],
    output: Path,
    hires: bool = False,
    color: str | None = None,
) -> None:
    """Render a single-mode median line with 25-75 percentile band."""
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    stroke = color or PALETTE_CATEGORICAL[1]
    xs = np.asarray(generations)
    ax.fill_between(xs, p25, p75, color=stroke, alpha=0.25, linewidth=0)
    ax.plot(xs, median, color=stroke, linewidth=1.4)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Hypervolume (median, 25-75 IQR)")

    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)
