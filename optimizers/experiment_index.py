"""Experiment-level artifact indexing helpers for single-mode containers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def refresh_experiment_index(experiment_root: str | Path) -> dict[str, Any]:
    root = Path(experiment_root)
    manifest = _load_optional_json(root / "manifest.json")
    payload = {
        "scenario_template_id": manifest.get("scenario_template_id"),
        "mode_id": manifest.get("mode_id"),
        "benchmark_seeds": list(manifest.get("benchmark_seeds", [])),
        "manifest": "manifest.json" if (root / "manifest.json").exists() else None,
        "run_roots": _discover_run_roots(root),
        "summaries": _discover_directory_files(root, "summaries"),
        "dashboards": _discover_directory_files(root, "dashboards"),
        "figures": _discover_directory_files(root, "figures"),
        "representatives": _discover_directory_files(root, "representatives"),
    }
    output_path = root / "logs" / "experiment_index.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _discover_run_roots(root: Path) -> list[dict[str, Any]]:
    runs_root = root / "runs"
    if not runs_root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for run_root in sorted(
        [path for path in runs_root.iterdir() if path.is_dir() and path.name.startswith("seed-")],
        key=lambda path: int(path.name.removeprefix("seed-")),
    ):
        rows.append(
            {
                "seed": int(run_root.name.removeprefix("seed-")),
                "path": str(run_root.relative_to(root).as_posix()),
                "manifest": (
                    str((run_root / "manifest.json").relative_to(root).as_posix())
                    if (run_root / "manifest.json").exists()
                    else None
                ),
            }
        )
    return rows


def _discover_directory_files(root: Path, directory_name: str) -> dict[str, str]:
    directory = root / directory_name
    if not directory.exists():
        return {}
    return {
        str(path.relative_to(directory).as_posix()): str(path.relative_to(root).as_posix())
        for path in sorted([item for item in directory.rglob("*") if item.is_file()])
    }


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
