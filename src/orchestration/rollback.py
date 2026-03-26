from __future__ import annotations

from pathlib import Path

from .run_manager import RunManager


def rollback_to(runs_root: str | Path, run_id: str) -> None:
    manager = RunManager(runs_root)
    run_dir = manager.runs_root / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")
    manager.set_current_run(run_id)
