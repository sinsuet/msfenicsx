"""High-information comparison figures for optimizer runs."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.figures.gradient_field import draw_gradient_field
from visualization.figures.layout_evolution import draw_layout_board
from visualization.figures.temperature_field import draw_temperature_field
from visualization.style.baseline import DPI_DEFAULT, DPI_HIRES, PALETTE_CATEGORICAL, apply_baseline


def _timeline_x(row: Mapping[str, Any]) -> int | None:
    value = row.get("pde_evaluation_index", row.get("evaluation_index"))
    return None if value is None else int(value)


def render_summary_overview(
    *,
    rows: Sequence[Mapping[str, Any]],
    output: Path,
    title: str,
    hires: bool = False,
) -> None:
    apply_baseline()
    output = ensure_output_parent(Path(output))
    table_rows = [_summary_table_row(row) for row in rows]
    headers = list(table_rows[0].keys()) if table_rows else ["summary"]
    cell_text = [[_display_value(row.get(header)) for header in headers] for row in table_rows] or [["No data"]]
    fig, ax = plt.subplots(figsize=(max(4.8, 1.2 * len(headers)), 1.6 + 0.5 * max(1, len(cell_text))))
    ax.set_axis_off()
    ax.set_title(title, loc="left")
    table = ax.table(cellText=cell_text, colLabels=headers, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1.0, 1.35)
    for (row_index, _col_index), cell in table.get_celld().items():
        if row_index == 0:
            cell.set_text_props(weight="semibold")
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def render_progress_dashboard(
    *,
    progress_series: Mapping[str, Sequence[Mapping[str, Any]]],
    hypervolume_series: Mapping[str, Sequence[tuple[int, float]]],
    output: Path,
    title: str,
    hires: bool = False,
) -> None:
    apply_baseline()
    output = ensure_output_parent(Path(output))
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 4.8))
    fig.suptitle(title, x=0.08, ha="left")
    violation_axis = axes[1, 1].twinx()

    for idx, (mode, rows) in enumerate(progress_series.items()):
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        _plot_trace_pair(
            axes[0, 0],
            rows,
            current_key="current_temperature_max",
            best_key="best_temperature_max_so_far",
            color=color,
            label=mode,
        )
        _plot_trace_pair(
            axes[0, 1],
            rows,
            current_key="current_gradient_rms",
            best_key="best_gradient_rms_so_far",
            color=color,
            label=mode,
        )
        if mode in hypervolume_series:
            xs = [int(item[0]) for item in hypervolume_series[mode]]
            ys = [float(item[1]) for item in hypervolume_series[mode]]
            axes[1, 0].plot(xs, ys, color=color, linewidth=1.2, label=mode)
        eval_xs = [x_value for row in rows for x_value in [_timeline_x(row)] if x_value is not None]
        feasible_rate = [float(row.get("feasible_rate_so_far", 0.0)) for row in rows for x_value in [_timeline_x(row)] if x_value is not None]
        violation_points = [
            (_timeline_x(row), float(row["best_total_constraint_violation_so_far"]))
            for row in rows
            if _timeline_x(row) is not None and row.get("best_total_constraint_violation_so_far") is not None
        ]
        axes[1, 1].plot(eval_xs[: len(feasible_rate)], feasible_rate, color=color, linewidth=1.2, label=mode)
        if violation_points:
            violation_axis.step(
                [item[0] for item in violation_points],
                [item[1] for item in violation_points],
                where="post",
                color=color,
                linewidth=0.9,
                alpha=0.35,
                linestyle="--",
            )

    axes[0, 0].set_title("Temperature Trace")
    axes[0, 0].set_xlabel("PDE evaluations")
    axes[0, 0].set_ylabel("Temperature (K)")
    axes[0, 1].set_title("Gradient Trace")
    axes[0, 1].set_xlabel("PDE evaluations")
    axes[0, 1].set_ylabel("Gradient RMS (K/m)")
    axes[1, 0].set_title("Hypervolume")
    axes[1, 0].set_xlabel("Generation")
    axes[1, 0].set_ylabel("Hypervolume")
    axes[1, 1].set_title("Feasible Rate / Best Violation")
    axes[1, 1].set_xlabel("PDE evaluations")
    axes[1, 1].set_ylabel("Feasible rate")
    violation_axis.set_ylabel("Best violation")
    violation_axis.grid(False)
    for axis in axes.flat:
        axis.legend(loc="best", fontsize=6)
        axis.grid(alpha=0.18, linewidth=0.4)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def render_pde_budget_accounting(
    *,
    progress_series: Mapping[str, Sequence[Mapping[str, Any]]],
    output: Path,
    title: str,
    common_pde_cutoff: int | None = None,
    hires: bool = False,
) -> None:
    apply_baseline()
    output = ensure_output_parent(Path(output))
    series = [(str(mode), list(rows)) for mode, rows in progress_series.items() if rows]
    if not series:
        return

    fig, axes = plt.subplots(
        len(series),
        1,
        figsize=(6.4, 1.45 * len(series) + 0.65),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    fig.suptitle(title, x=0.08, y=0.995, ha="left", fontsize=10)
    pde_color = PALETTE_CATEGORICAL[1 % len(PALETTE_CATEGORICAL)]
    skipped_color = PALETTE_CATEGORICAL[3 % len(PALETTE_CATEGORICAL)]
    proposal_color = "#2f2f2f"

    for row_index, (mode, rows) in enumerate(series):
        axis = axes[row_index, 0]
        xs = [0]
        pde_counts = [0]
        skipped_counts = [0]
        for row in rows:
            proposals = row.get("optimizer_evaluations_so_far")
            pde_count = row.get("pde_evaluations_so_far")
            skipped_count = row.get("solver_skipped_evaluations_so_far")
            if proposals is None or pde_count is None or skipped_count is None:
                continue
            xs.append(int(proposals))
            pde_counts.append(int(pde_count))
            skipped_counts.append(int(skipped_count))
        if len(xs) <= 1:
            continue
        totals = [pde + skipped for pde, skipped in zip(pde_counts, skipped_counts, strict=True)]
        axis.fill_between(
            xs,
            [0] * len(xs),
            pde_counts,
            step="post",
            color=pde_color,
            alpha=0.36,
            label="PDE solves",
        )
        axis.fill_between(
            xs,
            pde_counts,
            totals,
            step="post",
            color=skipped_color,
            alpha=0.30,
            label="Cheap-screen skipped",
        )
        axis.step(xs, totals, where="post", color=proposal_color, linewidth=0.9, label="Proposal budget")
        if common_pde_cutoff is not None and common_pde_cutoff > 0:
            axis.axhline(
                common_pde_cutoff,
                color=proposal_color,
                linewidth=0.7,
                linestyle=":",
                alpha=0.55,
                label="Common PDE cutoff" if row_index == 0 else "_nolegend_",
            )
        axis.set_title(mode.upper(), loc="left", fontsize=8)
        axis.grid(alpha=0.18, linewidth=0.4)

    axes[-1, 0].set_xlabel("Optimizer proposals")
    fig.supylabel("Cumulative evaluations", fontsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.98, 0.995), ncol=4, fontsize=6)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def render_layout_comparison(
    *,
    frames: Sequence[Mapping[str, Any]],
    output: Path,
    title: str,
    hires: bool = False,
) -> None:
    apply_baseline()
    output = ensure_output_parent(Path(output))
    column_count = max(1, len(frames))
    fig, axes = plt.subplots(1, column_count, figsize=(3.0 * column_count, 3.25), squeeze=False)
    fig.suptitle(title, x=0.06, ha="left")
    for axis, frame in zip(axes[0], frames):
        draw_layout_board(axis, dict(frame))
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def render_temperature_field_comparison(
    *,
    panels: Sequence[Mapping[str, Any]],
    output: Path,
    title: str,
    hires: bool = False,
) -> None:
    _render_field_comparison(
        panels=panels,
        output=output,
        title=title,
        hires=hires,
        draw_fn=draw_temperature_field,
        colorbar_label="Temperature (K)",
    )


def render_gradient_field_comparison(
    *,
    panels: Sequence[Mapping[str, Any]],
    output: Path,
    title: str,
    hires: bool = False,
) -> None:
    _render_field_comparison(
        panels=panels,
        output=output,
        title=title,
        hires=hires,
        draw_fn=draw_gradient_field,
        colorbar_label=r"$|\nabla T|$ (K/m)",
    )


def render_seed_outcome_dashboard(
    *,
    rows: Sequence[Mapping[str, Any]],
    output: Path,
    title: str,
    hires: bool = False,
) -> None:
    apply_baseline()
    output = ensure_output_parent(Path(output))
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 4.8))
    fig.suptitle(title, x=0.08, ha="left")
    metric_defs = [
        ("best_temperature_max", "Best Tmax"),
        ("best_gradient_rms", "Best Grad RMS"),
        ("first_feasible_eval", "First Feasible Eval"),
        ("final_hypervolume", "Final Hypervolume"),
    ]
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seed = row.get("benchmark_seed")
        if seed is None:
            continue
        grouped[int(seed)].append(dict(row))
    modes = sorted({str(row.get("mode")) for row in rows if row.get("mode") is not None})
    x_positions = {mode: idx for idx, mode in enumerate(modes)}

    for axis, (metric_key, metric_label) in zip(axes.flat, metric_defs):
        for seed_index, seed in enumerate(sorted(grouped)):
            seed_rows = sorted(grouped[seed], key=lambda row: x_positions.get(str(row.get("mode")), 0))
            xs = [x_positions[str(row.get("mode"))] for row in seed_rows if row.get(metric_key) is not None]
            ys = [float(row[metric_key]) for row in seed_rows if row.get(metric_key) is not None]
            if not xs:
                continue
            color = PALETTE_CATEGORICAL[(seed_index + 1) % len(PALETTE_CATEGORICAL)]
            axis.plot(xs, ys, color=color, linewidth=0.9, alpha=0.45)
            axis.scatter(xs, ys, color=color, s=16.0, alpha=0.8)
        axis.set_title(metric_label)
        axis.set_xticks(list(x_positions.values()), list(x_positions.keys()))
        axis.grid(alpha=0.18, linewidth=0.4)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def _render_field_comparison(
    *,
    panels: Sequence[Mapping[str, Any]],
    output: Path,
    title: str,
    hires: bool,
    draw_fn,
    colorbar_label: str,
) -> None:
    apply_baseline()
    output = ensure_output_parent(Path(output))
    if not panels:
        return
    all_values = np.concatenate([np.asarray(panel["grid"], dtype=np.float64).ravel() for panel in panels])
    norm = Normalize(vmin=float(np.nanmin(all_values)), vmax=float(np.nanmax(all_values)))
    column_count = len(panels)
    fig = plt.figure(figsize=(3.0 * column_count + 0.45, 3.35))
    grid_spec = fig.add_gridspec(1, column_count + 1, width_ratios=[*[1.0] * column_count, 0.07], wspace=0.08)
    fig.suptitle(title, x=0.06, ha="left")
    last_im = None
    for idx, panel in enumerate(panels):
        axis = fig.add_subplot(grid_spec[0, idx])
        last_im = draw_fn(
            axis,
            grid=np.asarray(panel["grid"], dtype=np.float64),
            xs=np.asarray(panel["xs"], dtype=np.float64),
            ys=np.asarray(panel["ys"], dtype=np.float64),
            layout=dict(panel.get("layout") or {}),
            title=str(panel.get("title") or ""),
            norm=norm,
            hotspot=panel.get("hotspot"),
        )
    cax = fig.add_subplot(grid_spec[0, -1])
    cbar = fig.colorbar(last_im, cax=cax)
    cbar.set_label(colorbar_label)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)


def _plot_trace_pair(
    axis,
    rows: Sequence[Mapping[str, Any]],
    *,
    current_key: str,
    best_key: str,
    color: str,
    label: str,
) -> None:
    current_points = [
        (x_value, float(row[current_key]))
        for row in rows
        for x_value in [_timeline_x(row)]
        if row.get(current_key) is not None and x_value is not None
    ]
    best_points = [
        (x_value, float(row[best_key]))
        for row in rows
        for x_value in [_timeline_x(row)]
        if row.get(best_key) is not None and x_value is not None
    ]
    if current_points:
        axis.plot(
            [item[0] for item in current_points],
            [item[1] for item in current_points],
            color=color,
            linewidth=0.8,
            alpha=0.28,
        )
    if best_points:
        axis.step(
            [item[0] for item in best_points],
            [item[1] for item in best_points],
            where="post",
            color=color,
            linewidth=1.15,
            label=label,
        )


def _summary_table_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "mode": row.get("mode"),
        "algorithm": row.get("algorithm"),
        "model": row.get("model"),
        "repr": row.get("representative_id"),
        "front": row.get("front_size", row.get("seed_count")),
        "pde_evals": row.get("pde_evaluations", row.get("pde_evaluations_mean")),
        "cheap_skip": row.get("solver_skipped_evaluations", row.get("solver_skipped_evaluations_mean")),
        "first_feasible": row.get("first_feasible_pde_eval", row.get("first_feasible_pde_eval_mean")),
        "best_tmax": row.get("best_temperature_max", row.get("best_temperature_max_mean")),
        "best_grad": row.get("best_gradient_rms", row.get("best_gradient_rms_mean")),
        "feasible_rate": row.get("feasible_rate", row.get("feasible_rate_mean")),
        "hypervolume": row.get("final_hypervolume", row.get("final_hypervolume_mean")),
    }


def _display_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}" if abs(value) < 100 else f"{value:.2f}"
    return str(value)
