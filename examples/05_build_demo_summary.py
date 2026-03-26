from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from orchestration.demo_summary import (
    write_demo_summary_csv,
    write_demo_summary_json,
    write_demo_summary_markdown,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build demo summary files from run directories.")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "demo_runs" / "official_10_iter")
    return parser.parse_args(argv)


def run_example(*, runs_root: str | Path | None = None) -> dict[str, str]:
    if runs_root is None:
        runs_root = ROOT / "demo_runs" / "official_10_iter"
    runs_root = Path(runs_root)
    summary_json = write_demo_summary_json(runs_root)
    summary_csv = write_demo_summary_csv(runs_root)
    summary_md = write_demo_summary_markdown(runs_root)
    return {
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "summary_md": str(summary_md),
    }


if __name__ == "__main__":
    args = parse_args()
    result = run_example(runs_root=args.runs_root)
    print("Demo summary built.")
    print(f"JSON: {result['summary_json']}")
    print(f"CSV: {result['summary_csv']}")
    print(f"Markdown: {result['summary_md']}")
