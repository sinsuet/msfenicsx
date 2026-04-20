"""Gradient-magnitude field with viridis colormap."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.figures.spatial_annotations import draw_component_labels, hide_spatial_axes
from visualization.style.baseline import (
    COLORMAP_GRADIENT,
    DPI_DEFAULT,
    DPI_FIELD_HIRES,
    apply_baseline,
)
from visualization.figures.temperature_field import _overlay_layout


def render_gradient_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    layout: dict[str, Any] | None = None,
    title: str | None = None,
    hires: bool = False,
) -> None:
    """Render the gradient magnitude field."""
    apply_baseline()
    shading = "gouraud" if hires else "auto"

    fig = plt.figure(figsize=(4.2, 3.5))
    grid_spec = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.07], wspace=0.08)
    ax = fig.add_subplot(grid_spec[0, 0])
    cax = fig.add_subplot(grid_spec[0, 1])
    im = draw_gradient_field(
        ax,
        grid=grid,
        xs=xs,
        ys=ys,
        layout=layout,
        title=title or "Gradient Field",
        shading=shading,
    )
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label(r"$|\nabla T|$ (K/m)")

    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def draw_gradient_field(
    ax,
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    layout: dict[str, Any] | None = None,
    title: str = "Gradient Field",
    shading: str = "auto",
    norm: Normalize | None = None,
    hotspot: dict[str, Any] | None = None,
):
    norm = norm or Normalize(vmin=float(np.nanmin(grid)), vmax=float(np.nanmax(grid)))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_GRADIENT, shading=shading, norm=norm)
    hide_spatial_axes(ax, width=float(xs.max()), height=float(ys.max()), title=title)
    _overlay_layout(ax, layout)
    if layout:
        def _sample_rgba(x_value: float, y_value: float):
            col_index = int(np.abs(xs - x_value).argmin())
            row_index = int(np.abs(ys - y_value).argmin())
            return im.cmap(norm(float(grid[row_index, col_index])))

        draw_component_labels(ax, layout.get("components", []), mode="field", sample_rgba=_sample_rgba)
    return im
