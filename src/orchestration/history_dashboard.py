from __future__ import annotations

from pathlib import Path

from history_dashboard_viz import save_history_collection_html, save_history_dashboard_html

from .history_report import (
    collect_history_collection_summary,
    collect_history_summary,
    write_history_collection_summary,
    write_history_summary,
)


def _run_dirs(root: Path) -> list[Path]:
    return sorted([path for path in root.glob("run_*") if path.is_dir()])


def _group_dirs(root: Path) -> list[Path]:
    return sorted([path for path in root.glob("group_*") if path.is_dir()])


def build_history_dashboard(runs_root: str | Path) -> dict[str, str]:
    runs_root = Path(runs_root)

    if _run_dirs(runs_root):
        history_summary_path = write_history_summary(runs_root)
        history_summary = collect_history_summary(runs_root)
        history_html_path = runs_root / "history.html"
        save_history_dashboard_html(history_html_path, history_summary=history_summary)
        return {
            "history_summary": str(history_summary_path),
            "history_html": str(history_html_path),
        }

    group_dirs = _group_dirs(runs_root)
    if group_dirs:
        for group_dir in group_dirs:
            build_history_dashboard(group_dir)
        history_summary_path = write_history_collection_summary(runs_root)
        history_summary = collect_history_collection_summary(runs_root)
        history_html_path = runs_root / "history.html"
        save_history_collection_html(history_html_path, collection_summary=history_summary)
        return {
            "history_summary": str(history_summary_path),
            "history_html": str(history_html_path),
        }

    raise ValueError(f"No run_* or group_* directories found under {runs_root}")
