from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from orchestration.optimize_loop import run_optimization_loop
from runtime_config import load_dotenv_file


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the multicomponent thermal optimization loop.")
    parser.add_argument("--state-path", type=Path, default=ROOT / "states" / "baseline_multicomponent.yaml")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "runs")
    parser.add_argument("--max-iters", type=int, default=1)
    parser.add_argument(
        "--max-invalid-proposals",
        type=int,
        default=2,
        help="Stop only after this many consecutive invalid LLM proposals.",
    )
    parser.add_argument("--real-llm", action="store_true", help="Use the real DashScope model instead of dry-run stub.")
    parser.add_argument("--enable-thinking", action="store_true", help="Enable thinking mode if the model supports it.")
    parser.add_argument(
        "--continue-when-feasible",
        action="store_true",
        help="Continue optimizing objective values after constraints are satisfied, until max-iters is reached.",
    )
    parser.add_argument("--model", default="qwen3.5-plus")
    return parser.parse_args(argv)


def run_example(
    *,
    state_path: str | Path | None = None,
    runs_root: str | Path | None = None,
    max_iters: int = 1,
    max_invalid_proposals: int = 2,
    dry_run_llm: bool = True,
    enable_thinking: bool = False,
    continue_when_feasible: bool = False,
    model: str = "qwen3.5-plus",
) -> dict[str, str | int]:
    load_dotenv_file(ROOT / ".env")
    if state_path is None:
        state_path = ROOT / "states" / "baseline_multicomponent.yaml"
    if runs_root is None:
        runs_root = ROOT / "runs"
    return run_optimization_loop(
        state_path=state_path,
        runs_root=runs_root,
        max_iters=max_iters,
        max_invalid_proposals=max_invalid_proposals,
        dry_run_llm=dry_run_llm,
        enable_thinking=enable_thinking,
        continue_when_feasible=continue_when_feasible,
        model=model,
    )


if __name__ == "__main__":
    args = parse_args()
    result = run_example(
        state_path=args.state_path,
        runs_root=args.runs_root,
        max_iters=args.max_iters,
        max_invalid_proposals=args.max_invalid_proposals,
        dry_run_llm=not args.real_llm,
        enable_thinking=args.enable_thinking,
        continue_when_feasible=args.continue_when_feasible,
        model=args.model,
    )
    print("Optimization loop finished.")
    print(f"Iterations: {result['iterations']}")
    print(f"Status: {result['status']}")
    print(f"Last run: {result['last_run_id']}")
