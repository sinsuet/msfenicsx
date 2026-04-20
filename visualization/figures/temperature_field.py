"""Temperature field heatmap with correctly oriented colorbar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import Normalize

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.figures.spatial_annotations import draw_component_labels, draw_sink_ribbons, hide_spatial_axes
from visualization.style.baseline import (
    COLORMAP_TEMPERATURE,
    DPI_DEFAULT,
    DPI_FIELD_HIRES,
    SPATIAL_FIELD_OUTLINE,
    apply_baseline,
)


def render_temperature_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    layout: dict[str, Any] | None = None,
    hotspot: dict[str, Any] | None = None,
    title: str | None = None,
    hires: bool = False,
    return_artifacts: bool = False,
) -> tuple[Any, Any, Any] | None:
    """Render a temperature field with inferno colormap and a native colorbar.

    Relies on matplotlib's `fig.colorbar(im, ax=ax)` for orientation — the
    hand-built legacy renderer inverted it.
    """
    apply_baseline()
    shading = "gouraud" if hires else "auto"

    fig = plt.figure(figsize=(4.2, 3.5))
    grid_spec = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.07], wspace=0.08)
    ax = fig.add_subplot(grid_spec[0, 0])
    cax = fig.add_subplot(grid_spec[0, 1])
    im = draw_temperature_field(
        ax,
        grid=grid,
        xs=xs,
        ys=ys,
        layout=layout,
        hotspot=hotspot,
        title=title or "Temperature Field",
        shading=shading,
    )
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("Temperature (K)")

    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)

    # Also emit a PDF sibling if output is a png.
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)

    if return_artifacts:
        return fig, im, cbar
    plt.close(fig)
    return None


def draw_temperature_field(
    ax: Axes,
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    layout: dict[str, Any] | None = None,
    hotspot: dict[str, Any] | None = None,
    title: str = "Temperature Field",
    shading: str = "auto",
    norm: Normalize | None = None,
):
    norm = norm or Normalize(vmin=float(np.nanmin(grid)), vmax=float(np.nanmax(grid)))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_TEMPERATURE, shading=shading, norm=norm)
    hide_spatial_axes(ax, width=float(xs.max()), height=float(ys.max()), title=title)
    _overlay_layout(ax, layout)
    if layout:
        def _sample_rgba(x_value: float, y_value: float):
            col_index = int(np.abs(xs - x_value).argmin())
            row_index = int(np.abs(ys - y_value).argmin())
            return im.cmap(norm(float(grid[row_index, col_index])))

        draw_component_labels(ax, layout.get("components", []), mode="field", sample_rgba=_sample_rgba)
    if hotspot:
        ax.plot(
            [float(hotspot["x"])],
            [float(hotspot["y"])],
            marker="x",
            markersize=4.0,
            markeredgewidth=0.9,
            color="white",
        )
    return im


def _overlay_layout(ax: Axes, layout: dict[str, Any] | None) -> None:
    if not layout:
        return
    for component in layout.get("components", []):
        outline = component.get("outline")
        if not outline:
            continue
        coords = np.asarray(outline, dtype=np.float64)
        if coords.ndim != 2 or coords.shape[1] != 2:
            continue
        closed = np.vstack([coords, coords[0]])
        ax.plot(closed[:, 0], closed[:, 1], color=SPATIAL_FIELD_OUTLINE, linewidth=0.7, alpha=0.95, zorder=6)
    draw_sink_ribbons(
        ax,
        layout.get("line_sinks", []),
        width=float(ax.get_xlim()[1]),
        height=float(ax.get_ylim()[1]),
    )
