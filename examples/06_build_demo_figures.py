from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from orchestration.demo_figures import build_demo_figures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build aggregate demo figures from demo summary.")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "demo_runs" / "official_10_iter")
    return parser.parse_args(argv)


def run_example(*, runs_root: str | Path | None = None) -> dict[str, str]:
    if runs_root is None:
        runs_root = ROOT / "demo_runs" / "official_10_iter"
    return build_demo_figures(runs_root)


if __name__ == "__main__":
    args = parse_args()
    result = run_example(runs_root=args.runs_root)
    print("Demo figures built.")
    print(f"Chip max trend: {result['chip_max_trend']}")
    print(f"Delta trend: {result['delta_trend']}")
    print(f"Category timeline: {result['category_timeline']}")
