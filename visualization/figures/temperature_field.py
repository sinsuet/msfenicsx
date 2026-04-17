"""Temperature field heatmap with CORRECTLY oriented colorbar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from visualization.style.baseline import (
    COLORMAP_TEMPERATURE,
    DPI_DEFAULT,
    DPI_FIELD_HIRES,
    apply_baseline,
)


def render_temperature_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    hires: bool = False,
    return_artifacts: bool = False,
) -> tuple[Any, Any, Any] | None:
    """Render a temperature field with inferno colormap and a native colorbar.

    Relies on matplotlib's `fig.colorbar(im, ax=ax)` for orientation — the
    hand-built legacy renderer inverted it.
    """
    apply_baseline()
    shading = "gouraud" if hires else "auto"

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_TEMPERATURE, shading=shading)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Temperature (K)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)

    # Also emit a PDF sibling if output is a png.
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))

    if return_artifacts:
        return fig, im, cbar
    plt.close(fig)
    return None
