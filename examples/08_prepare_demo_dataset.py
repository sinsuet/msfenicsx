from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from orchestration.demo_dataset import prepare_demo_dataset_workspace


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive current runs and prepare a clean demo dataset workspace.")
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--archive-label", default=f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    return parser.parse_args(argv)


def run_example(
    *,
    workspace_root: str | Path | None = None,
    archive_label: str | None = None,
) -> dict[str, str | None]:
    if workspace_root is None:
        workspace_root = ROOT
    if archive_label is None:
        archive_label = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return prepare_demo_dataset_workspace(workspace_root, archive_label=archive_label)


if __name__ == "__main__":
    args = parse_args()
    result = run_example(workspace_root=args.workspace_root, archive_label=args.archive_label)
    print("Demo dataset workspace prepared.")
    print(f"Archived runs: {result['archived_runs_root']}")
    print(f"Fresh runs root: {result['runs_root']}")
    print(f"Official demo runs root: {result['demo_runs_root']}")
