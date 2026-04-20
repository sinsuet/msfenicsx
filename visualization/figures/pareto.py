"""Pareto-front plot for single-mode and overlay variants."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.style.baseline import (
    DPI_DEFAULT,
    DPI_HIRES,
    PALETTE_CATEGORICAL,
    apply_baseline,
)


def render_pareto_front(
    *,
    fronts: Mapping[str, Sequence[tuple[float, float]]],
    output: Path,
    hires: bool = False,
) -> None:
    """Render one Pareto curve per mode overlaid on a single axis."""
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.5, 2.6))

    for idx, (mode, points) in enumerate(fronts.items()):
        if not points:
            continue
        ordered = sorted(points, key=lambda p: p[0])
        xs = [p[0] for p in ordered]
        ys = [p[1] for p in ordered]
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        ax.plot(xs, ys, color=color, marker="o", markersize=3, linewidth=1.0, label=mode)

    ax.set_xlabel(r"$T_{\max}$ (K)")
    ax.set_ylabel(r"$\nabla T_{\mathrm{rms}}$ (K/m)")
    if len(fronts) > 1:
        ax.legend()

    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)
