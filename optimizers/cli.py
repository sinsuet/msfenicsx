"""Standalone CLI for optimizer-layer workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from evaluation.io import load_multicase_spec
from llm.openai_compatible.replay import replay_request_trace_file, save_replay_summary
from optimizers.artifacts import write_optimization_artifacts
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.io import generate_benchmark_cases, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.operator_pool.diagnostics import analyze_controller_trace, save_controller_trace_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx-optimize")
    subparsers = parser.add_subparsers(dest="command")

    optimize_parser = subparsers.add_parser("optimize-benchmark")
    optimize_parser.add_argument("--optimization-spec", required=True)
    optimize_parser.add_argument("--output-root", required=True)

    replay_parser = subparsers.add_parser("replay-llm-trace")
    replay_parser.add_argument("--optimization-spec", required=True)
    replay_parser.add_argument("--request-trace", required=True)
    replay_parser.add_argument("--output", required=True)
    replay_parser.add_argument("--limit", type=int, default=None)

    diagnostics_parser = subparsers.add_parser("analyze-controller-trace")
    diagnostics_parser.add_argument("--controller-trace", required=True)
    diagnostics_parser.add_argument("--output", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "optimize-benchmark":
        optimization_spec = load_optimization_spec(args.optimization_spec)
        cases = generate_benchmark_cases(args.optimization_spec, optimization_spec)
        evaluation_spec_path = resolve_evaluation_spec_path(args.optimization_spec, optimization_spec)
        evaluation_spec = load_multicase_spec(evaluation_spec_path)
        mode = optimization_spec.algorithm["mode"]
        if mode == "raw":
            run = run_raw_optimization(cases, optimization_spec, evaluation_spec, spec_path=args.optimization_spec)
        elif mode == "union":
            run = run_union_optimization(cases, optimization_spec, evaluation_spec, spec_path=args.optimization_spec)
        else:
            raise ValueError(f"Unsupported optimizer mode {mode!r}.")
        write_optimization_artifacts(args.output_root, run)
        return 0
    if args.command == "replay-llm-trace":
        optimization_spec = load_optimization_spec(args.optimization_spec)
        operator_control = optimization_spec.operator_control
        if operator_control is None or operator_control.get("controller") != "llm":
            raise ValueError("replay-llm-trace requires an optimization spec with operator_control.controller='llm'.")
        replay_summary = replay_request_trace_file(
            Path(args.request_trace),
            dict(operator_control["controller_parameters"]),
            limit=args.limit,
        )
        save_replay_summary(args.output, replay_summary)
        return 0
    if args.command == "analyze-controller-trace":
        summary = analyze_controller_trace(Path(args.controller_trace))
        save_controller_trace_summary(args.output, summary)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
