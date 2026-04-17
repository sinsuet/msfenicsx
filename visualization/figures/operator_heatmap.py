"""Operator × phase usage heatmap."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from visualization.style.baseline import DPI_DEFAULT, DPI_HIRES, apply_baseline


def render_operator_heatmap(
    *,
    grid: dict[str, dict[str, int]],
    output: Path,
    hires: bool = False,
) -> None:
    """Render `{operator: {phase: count}}` as a heatmap."""
    apply_baseline()
    operators = sorted(grid.keys())
    phases: list[str] = []
    for op in operators:
        for phase in grid[op]:
            if phase not in phases:
                phases.append(phase)
    phases.sort(key=lambda p: (p == "n/a", p))

    matrix = np.zeros((len(operators), len(phases)), dtype=float)
    for i, op in enumerate(operators):
        for j, phase in enumerate(phases):
            matrix[i, j] = grid[op].get(phase, 0)

    fig_w = max(3.5, 0.6 * len(phases) + 2.0)
    fig_h = max(2.6, 0.35 * len(operators) + 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(matrix, aspect="auto", cmap="magma")
    ax.set_xticks(range(len(phases)))
    ax.set_xticklabels(phases, rotation=30, ha="right")
    ax.set_yticks(range(len(operators)))
    ax.set_yticklabels(operators)
    for i in range(len(operators)):
        for j in range(len(phases)):
            count = int(matrix[i, j])
            if count:
                ax.text(j, i, str(count), ha="center", va="center", color="white", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)
