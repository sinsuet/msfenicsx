from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .demo_summary import collect_demo_summary


def _load_or_build_summary(runs_root: Path) -> dict:
    summary_path = runs_root / "demo_summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    return collect_demo_summary(runs_root)


def _save_chip_max_trend(figures_dir: Path, runs: list[dict]) -> Path:
    path = figures_dir / "chip_max_trend.png"
    labels = [item["run_id"] for item in runs]
    values = [item.get("chip_max_before") for item in runs]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(labels, values, marker="o", color="#a44a3f", linewidth=2)
    ax.set_title("Chip Max Temperature By Run")
    ax.set_xlabel("Run")
    ax.set_ylabel("Chip Max Before (degC)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _save_delta_trend(figures_dir: Path, runs: list[dict]) -> Path:
    path = figures_dir / "delta_trend.png"
    labels = [item["run_id"] for item in runs]
    values = [item.get("delta_chip_max") or 0.0 for item in runs]
    colors = ["#2a9d8f" if value <= 0 else "#e76f51" for value in values]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(labels, values, color=colors)
    ax.axhline(0.0, color="#444", linewidth=1)
    ax.set_title("Delta Chip Max Temperature (Next Run - Current Run)")
    ax.set_xlabel("Run")
    ax.set_ylabel("Delta (degC)")
    ax.grid(alpha=0.2, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _save_category_timeline(figures_dir: Path, runs: list[dict]) -> Path:
    path = figures_dir / "category_timeline.png"
    fig, ax = plt.subplots(figsize=(10, 3.8))
    palette = {
        "material": "#457b9d",
        "geometry": "#f4a261",
        "load": "#8d99ae",
        "mixed": "#6a4c93",
        "none": "#adb5bd",
    }
    for idx, item in enumerate(runs, start=1):
        categories = item.get("change_categories", [])
        if not categories:
            category = "none"
        elif len(categories) == 1:
            category = categories[0]
        else:
            category = "mixed"
        ax.scatter(
            [idx],
            [1],
            s=320,
            color=palette.get(category, "#6a4c93"),
            edgecolors="black",
            linewidths=0.8,
        )
        ax.text(idx, 1, category, ha="center", va="center", fontsize=8, color="white")
    ax.set_title("Change Category Timeline")
    ax.set_xlim(0.5, len(runs) + 0.5)
    ax.set_ylim(0.7, 1.3)
    ax.set_xticks(range(1, len(runs) + 1), [item["run_id"] for item in runs], rotation=30, ha="right")
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def build_demo_figures(runs_root: str | Path) -> dict[str, str]:
    runs_root = Path(runs_root)
    figures_dir = runs_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    summary = _load_or_build_summary(runs_root)
    runs = summary.get("runs", [])
    return {
        "chip_max_trend": str(_save_chip_max_trend(figures_dir, runs)),
        "delta_trend": str(_save_delta_trend(figures_dir, runs)),
        "category_timeline": str(_save_category_timeline(figures_dir, runs)),
    }
