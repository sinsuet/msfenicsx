from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from orchestration.demo_beamer import build_demo_beamer


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Chinese Beamer draft for the demo workflow.")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=ROOT / "demo_runs" / "consistency_10x15_fullwindow_20260326",
    )
    parser.add_argument("--output-path", type=Path, default=ROOT / "slides" / "demo_workflow_beamer.tex")
    return parser.parse_args(argv)


def run_example(
    *,
    runs_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, str]:
    if runs_root is None:
        runs_root = ROOT / "demo_runs" / "consistency_10x15_fullwindow_20260326"
    if output_path is None:
        output_path = ROOT / "slides" / "demo_workflow_beamer.tex"
    return build_demo_beamer(runs_root=runs_root, output_path=output_path)


if __name__ == "__main__":
    args = parse_args()
    result = run_example(runs_root=args.runs_root, output_path=args.output_path)
    print("Demo beamer draft built.")
    print(f"TeX: {result['tex_path']}")
