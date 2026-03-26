from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from orchestration.history_dashboard import build_history_dashboard


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build history dashboards for a run root or grouped run root.")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "runs")
    return parser.parse_args(argv)


def run_example(*, runs_root: str | Path | None = None) -> dict[str, str]:
    if runs_root is None:
        runs_root = ROOT / "runs"
    return build_history_dashboard(runs_root)


if __name__ == "__main__":
    args = parse_args()
    result = run_example(runs_root=args.runs_root)
    print("History dashboard built.")
    print(f"Summary JSON: {result['history_summary']}")
    print(f"History HTML: {result['history_html']}")
