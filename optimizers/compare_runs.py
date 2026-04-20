"""Strict external compare entrypoint for concrete single-mode run roots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from optimizers.comparison_artifacts import (
    build_comparison_bundle,
    resolve_single_run_root,
)


def compare_runs(*, runs: list[Path] | tuple[Path, ...], output: Path) -> dict[str, Any]:
    resolved_runs = [resolve_single_run_root(Path(run)) for run in runs]
    return build_comparison_bundle(runs=resolved_runs, output=Path(output), comparison_kind="external")
