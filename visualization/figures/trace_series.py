"""Current-vs-best trace figures and feasible-progress comparisons."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

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


def render_metric_trace(
    *,
    series: Mapping[str, Sequence[Mapping[str, Any]]],
    current_key: str,
    best_key: str,
    ylabel: str,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.6, 2.6))

    for idx, (label, rows) in enumerate(series.items()):
        if not rows:
            continue
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        current_points = [
            (x_value, float(row[current_key]))
            for row in rows
            for x_value in [_timeline_x(row)]
            if x_value is not None and row.get(current_key) is not None
        ]
        best_points = [
            (x_value, float(row[best_key]))
            for row in rows
            for x_value in [_timeline_x(row)]
            if x_value is not None and row.get(best_key) is not None
        ]
        if current_points:
            ax.plot(
                [item[0] for item in current_points],
                [item[1] for item in current_points],
                color=color,
                alpha=0.28,
                linewidth=0.8,
            )
            ax.scatter(
                [item[0] for item in current_points],
                [item[1] for item in current_points],
                color=color,
                alpha=0.35,
                s=8.0,
            )
        if best_points:
            ax.step(
                [item[0] for item in best_points],
                [item[1] for item in best_points],
                where="post",
                color=color,
                linewidth=1.25,
                label=label,
            )

    lower_y = ax.get_ylim()[0] if ax.has_data() else 0.0
    for idx, (label, rows) in enumerate(series.items()):
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        failed_xs = [
            x_value
            for row in rows
            for x_value in [_timeline_x(row)]
            if x_value is not None and str(row.get("status", "")).strip().lower() == "failed"
        ]
        if failed_xs:
            ax.scatter(
                failed_xs,
                np.full(len(failed_xs), lower_y),
                marker="x",
                color=color,
                s=10.0,
                alpha=0.65,
            )

    ax.set_xlabel("PDE evaluations")
    ax.set_ylabel(ylabel)
    if len(series) > 1 and ax.get_legend_handles_labels()[0]:
        ax.legend()
    _save_trace_figure(fig, output, hires=hires)


def render_feasible_progress(
    *,
    series: Mapping[str, Sequence[Mapping[str, Any]]],
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6))
    count_ax, rate_ax = axes

    for idx, (label, rows) in enumerate(series.items()):
        if not rows:
            continue
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        xs = [x_value for row in rows for x_value in [_timeline_x(row)] if x_value is not None]
        count_ax.step(
            xs,
            [int(row["feasible_count_so_far"]) for row in rows for x_value in [_timeline_x(row)] if x_value is not None],
            where="post",
            color=color,
            linewidth=1.2,
            label=label,
        )
        rate_ax.step(
            xs,
            [float(row["feasible_rate_so_far"]) for row in rows for x_value in [_timeline_x(row)] if x_value is not None],
            where="post",
            color=color,
            linewidth=1.2,
            label=label,
        )

    count_ax.set_xlabel("PDE evaluations")
    count_ax.set_ylabel("Feasible count")
    rate_ax.set_xlabel("PDE evaluations")
    rate_ax.set_ylabel("Feasible rate")
    if len(series) > 1:
        if count_ax.get_legend_handles_labels()[0]:
            count_ax.legend()
        if rate_ax.get_legend_handles_labels()[0]:
            rate_ax.legend()
    _save_trace_figure(fig, output, hires=hires)


def render_metric_band_comparison(
    *,
    xs: Sequence[int],
    bands: Mapping[str, Mapping[str, Sequence[float]]],
    ylabel: str,
    output: Path,
    xlabel: str = "PDE evaluations",
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    x_values = np.asarray(xs, dtype=np.float64)

    for idx, (label, payload) in enumerate(bands.items()):
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        median = np.asarray(payload["median"], dtype=np.float64)
        p25 = np.asarray(payload["p25"], dtype=np.float64)
        p75 = np.asarray(payload["p75"], dtype=np.float64)
        ax.fill_between(x_values, p25, p75, color=color, alpha=0.18, linewidth=0)
        ax.plot(x_values, median, color=color, linewidth=1.25, label=label)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if len(bands) > 1 and ax.get_legend_handles_labels()[0]:
        ax.legend()
    _save_trace_figure(fig, output, hires=hires)


def render_metric_boxplot(
    *,
    values_by_mode: Mapping[str, Sequence[float]],
    ylabel: str,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.6, 2.8))
    labels = [label for label, values in values_by_mode.items() if values]
    datasets = [list(values_by_mode[label]) for label in labels]
    if datasets:
        boxplot = ax.boxplot(datasets, tick_labels=labels, patch_artist=True)
        for idx, patch in enumerate(boxplot["boxes"]):
            patch.set_facecolor(PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)])
            patch.set_alpha(0.45)
    ax.set_ylabel(ylabel)
    _save_trace_figure(fig, output, hires=hires)


def render_dual_metric_boxplot(
    *,
    left_values_by_mode: Mapping[str, Sequence[float]],
    right_values_by_mode: Mapping[str, Sequence[float]],
    left_ylabel: str,
    right_ylabel: str,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for axis, values_by_mode, ylabel in (
        (axes[0], left_values_by_mode, left_ylabel),
        (axes[1], right_values_by_mode, right_ylabel),
    ):
        labels = [label for label, values in values_by_mode.items() if values]
        datasets = [list(values_by_mode[label]) for label in labels]
        if datasets:
            boxplot = axis.boxplot(datasets, tick_labels=labels, patch_artist=True)
            for idx, patch in enumerate(boxplot["boxes"]):
                patch.set_facecolor(PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)])
                patch.set_alpha(0.45)
        axis.set_ylabel(ylabel)
    _save_trace_figure(fig, output, hires=hires)


def _save_trace_figure(fig: Any, output: Path, *, hires: bool) -> None:
    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)
