"""Gradient-magnitude field with viridis colormap."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from visualization.style.baseline import (
    COLORMAP_GRADIENT,
    DPI_DEFAULT,
    DPI_FIELD_HIRES,
    apply_baseline,
)


def render_gradient_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    hires: bool = False,
) -> None:
    """Render the gradient magnitude field."""
    apply_baseline()
    shading = "gouraud" if hires else "auto"

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_GRADIENT, shading=shading)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label(r"$|\nabla T|$ (K/m)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)
