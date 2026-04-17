"""Regression lock for the inverted-colorbar bug at old figure_axes.py:44.

After rendering, the highest-valued input pixel must map to the top of the
rendered colorbar (not the bottom, as the legacy hand-rolled SVG did).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def test_temperature_field_colorbar_hot_at_top(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from visualization.figures.temperature_field import render_temperature_field

    # Grid with a single obvious hotspot at (row=1, col=1), cool elsewhere.
    grid = np.array(
        [
            [290.0, 290.0, 290.0],
            [290.0, 360.0, 290.0],
            [290.0, 290.0, 290.0],
        ]
    )
    xs = np.array([0.0, 0.5, 1.0])
    ys = np.array([0.0, 0.5, 1.0])

    output = tmp_path / "temperature.png"
    fig, im, cbar = render_temperature_field(
        grid=grid,
        xs=xs,
        ys=ys,
        output=output,
        return_artifacts=True,
    )

    # Colorbar ticks must be oriented low-at-bottom, high-at-top.
    ymin, ymax = cbar.ax.get_ylim()
    assert ymax > ymin, "colorbar y-axis must increase upward"

    # The max value displayed must correspond to the actual max input value.
    assert im.norm.vmax >= 360.0 - 1e-9
    assert im.norm.vmin <= 290.0 + 1e-9

    assert output.exists() and output.stat().st_size > 0
    plt.close(fig)
