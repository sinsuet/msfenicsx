"""Objective-progress curves against PDE evaluation count."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.style.baseline import (
    DPI_DEFAULT,
    DPI_HIRES,
    PALETTE_CATEGORICAL,
    apply_baseline,
)


def _timeline_x(row: Mapping[str, Any]) -> int | None:
    value = row.get("pde_evaluation_index", row.get("evaluation_index"))
    return None if value is None else int(value)


def _first_feasible_x(row: Mapping[str, Any]) -> int | None:
    value = row.get("first_feasible_pde_eval_so_far", row.get("first_feasible_eval_so_far"))
    return None if value is None else int(value)


def render_objective_progress(
    *,
    series: Mapping[str, Sequence[Mapping[str, Any]]],
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    peak_ax, gradient_ax = axes
    has_labeled_series = False

    for idx, (label, rows) in enumerate(series.items()):
        if not rows:
            continue
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        usable_peak = [
            (x_value, float(row["best_temperature_max_so_far"]))
            for row in rows
            for x_value in [_timeline_x(row)]
            if x_value is not None and row.get("best_temperature_max_so_far") is not None
        ]
        usable_gradient = [
            (x_value, float(row["best_gradient_rms_so_far"]))
            for row in rows
            for x_value in [_timeline_x(row)]
            if x_value is not None and row.get("best_gradient_rms_so_far") is not None
        ]
        if usable_peak:
            has_labeled_series = True
            peak_ax.step(
                [item[0] for item in usable_peak],
                [item[1] for item in usable_peak],
                where="post",
                linewidth=1.2,
                color=color,
                label=label,
            )
        if usable_gradient:
            gradient_ax.step(
                [item[0] for item in usable_gradient],
                [item[1] for item in usable_gradient],
                where="post",
                linewidth=1.2,
                color=color,
                label=label,
            )
        first_feasible_eval = next(
            (
                _first_feasible_x(row)
                for row in rows
                if _first_feasible_x(row) is not None
            ),
            None,
        )
        if first_feasible_eval is not None:
            peak_ax.axvline(first_feasible_eval, color=color, linewidth=0.8, linestyle="--", alpha=0.35)
            gradient_ax.axvline(first_feasible_eval, color=color, linewidth=0.8, linestyle="--", alpha=0.35)

    peak_ax.set_xlabel("PDE evaluations")
    peak_ax.set_ylabel(r"Best $T_{\max}$ so far (K)")
    gradient_ax.set_xlabel("PDE evaluations")
    gradient_ax.set_ylabel(r"Best $\nabla T_{\mathrm{rms}}$ so far (K/m)")
    if len(series) > 1 and has_labeled_series:
        if peak_ax.get_legend_handles_labels()[0]:
            peak_ax.legend()
        if gradient_ax.get_legend_handles_labels()[0]:
            gradient_ax.legend()

    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)
