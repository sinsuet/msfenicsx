from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np


OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"]


def render_distribution_figure(rows: Iterable[dict[str, str]], *, metric: str, output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["scenario_id"], row["method_id"])].append(float(row[metric]))

    _set_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    labels = [f"{scenario}\n{method}" for scenario, method in sorted(grouped)]
    values = [grouped[key] for key in sorted(grouped)]
    ax.boxplot(values, tick_labels=labels, showfliers=False)
    for index, group_values in enumerate(values, start=1):
        jitter = np.linspace(-0.05, 0.05, num=len(group_values)) if len(group_values) > 1 else [0.0]
        ax.scatter([index + offset for offset in jitter], group_values, color="black", alpha=0.55, s=12, zorder=3)
    ax.set_xlabel("Scenario / Method")
    ax.set_ylabel(metric)
    return _save(fig, output_root, f"{metric}_distribution")


def render_rank_heatmap(rows: Iterable[dict[str, str]], *, output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
    scenarios = sorted({row["scenario_id"] for row in row_list})
    methods = sorted({row["method_id"] for row in row_list})
    rank_lookup = {(row["scenario_id"], row["method_id"]): float(row["rank"]) for row in row_list}
    matrix = np.array([[rank_lookup.get((scenario, method), np.nan) for method in methods] for scenario in scenarios])

    _set_style()
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    image = ax.imshow(matrix, cmap="viridis_r")
    ax.set_xticks(range(len(methods)), methods, rotation=30, ha="right")
    ax.set_yticks(range(len(scenarios)), scenarios)
    ax.set_xlabel("Method")
    ax.set_ylabel("Scenario")
    for row_index, scenario in enumerate(scenarios):
        for column_index, method in enumerate(methods):
            value = rank_lookup.get((scenario, method))
            if value is not None:
                ax.text(column_index, row_index, f"{value:.1f}", ha="center", va="center", color="white")
    fig.colorbar(image, ax=ax, label="Rank")
    return _save(fig, output_root, "rank_heatmap")


def render_failure_stacked_bar(rows: Iterable[dict[str, str]], *, output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
    methods = sorted({row["method_id"] for row in row_list})
    statuses = sorted({row["status"] for row in row_list})
    counts = {(method, status): 0 for method in methods for status in statuses}
    for row in row_list:
        counts[(row["method_id"], row["status"])] += 1

    _set_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    bottoms = np.zeros(len(methods))
    x_positions = np.arange(len(methods))
    for status_index, status in enumerate(statuses):
        values = np.array([counts[(method, status)] for method in methods])
        ax.bar(x_positions, values, bottom=bottoms, label=status, color=OKABE_ITO[status_index % len(OKABE_ITO)])
        bottoms += values
    ax.set_xticks(x_positions, methods, rotation=30, ha="right")
    ax.set_xlabel("Method")
    ax.set_ylabel("Run count")
    ax.legend(frameon=False)
    return _save(fig, output_root, "failure_stacked_bar")


def _set_style() -> None:
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})


def _save(fig, output_root: Path, stem: str) -> list[Path]:
    fig.tight_layout()
    png_path = output_root / f"{stem}.png"
    pdf_path = output_root / f"{stem}.pdf"
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)
    return [png_path, pdf_path]
