"""Helpers for the single-case-first s1_typical run layout."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Sequence


MODE_ORDER = ("raw", "union", "llm")


def build_run_id(started_at: datetime, modes: Sequence[str]) -> str:
    requested_modes = {str(mode) for mode in modes}
    ordered_modes = [mode for mode in MODE_ORDER if mode in requested_modes]
    if not ordered_modes:
        raise ValueError("build_run_id requires at least one supported mode.")
    return f"{started_at:%m%d_%H%M}__{'_'.join(ordered_modes)}"


def initialize_run_root(
    scenario_runs_root: str | Path,
    *,
    scenario_template_id: str,
    run_id: str,
    modes: Sequence[str],
) -> Path:
    root = Path(scenario_runs_root) / scenario_template_id / run_id
    (root / "shared").mkdir(parents=True, exist_ok=True)
    for mode in MODE_ORDER:
        if mode in {str(item) for item in modes}:
            (root / mode).mkdir(parents=True, exist_ok=True)
    return root


def initialize_mode_root(run_root: str | Path, *, mode: str) -> Path:
    root = Path(run_root) / mode
    for directory_name in ("logs", "summaries", "pages", "figures", "reports", "seeds"):
        (root / directory_name).mkdir(parents=True, exist_ok=True)
    return root


def initialize_comparison_root(run_root: str | Path) -> Path:
    root = Path(run_root) / "comparison"
    for directory_name in ("summaries", "pages", "figures", "reports"):
        (root / directory_name).mkdir(parents=True, exist_ok=True)
    return root


def write_manifest(path: str | Path, payload: dict[str, object]) -> Path:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path
