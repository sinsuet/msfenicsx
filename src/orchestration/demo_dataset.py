from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any


def _has_contents(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def prepare_demo_dataset_workspace(
    workspace_root: str | Path,
    *,
    archive_label: str,
    runs_dir_name: str = "runs",
    demo_runs_relpath: str = "demo_runs/official_10_iter",
    archive_root_name: str = "runs_archive",
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    runs_root = workspace_root / runs_dir_name
    demo_runs_root = workspace_root / demo_runs_relpath
    archive_root = workspace_root / archive_root_name / archive_label

    archived_runs_root: Path | None = None
    if _has_contents(runs_root):
        archive_root.mkdir(parents=True, exist_ok=True)
        archived_runs_root = archive_root / runs_dir_name
        if archived_runs_root.exists():
            raise FileExistsError(f"Archive target already exists: {archived_runs_root}")
        shutil.move(str(runs_root), str(archived_runs_root))

    runs_root.mkdir(parents=True, exist_ok=True)

    archived_demo_runs_root: Path | None = None
    if _has_contents(demo_runs_root):
        archive_root.mkdir(parents=True, exist_ok=True)
        archived_demo_runs_root = archive_root / demo_runs_relpath
        archived_demo_runs_root.parent.mkdir(parents=True, exist_ok=True)
        if archived_demo_runs_root.exists():
            raise FileExistsError(f"Archive target already exists: {archived_demo_runs_root}")
        shutil.move(str(demo_runs_root), str(archived_demo_runs_root))
    elif demo_runs_root.exists():
        shutil.rmtree(demo_runs_root)
    demo_runs_root.mkdir(parents=True, exist_ok=True)

    return {
        "workspace_root": str(workspace_root),
        "runs_root": str(runs_root),
        "demo_runs_root": str(demo_runs_root),
        "archived_runs_root": str(archived_runs_root) if archived_runs_root is not None else None,
        "archived_demo_runs_root": (
            str(archived_demo_runs_root) if archived_demo_runs_root is not None else None
        ),
    }
