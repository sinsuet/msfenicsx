"""Standalone CLI for optimizer-layer workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from evaluation.io import load_multicase_spec
from optimizers.artifacts import write_optimization_artifacts
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.io import generate_benchmark_cases, load_optimization_spec, resolve_evaluation_spec_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx-optimize")
    subparsers = parser.add_subparsers(dest="command")

    optimize_parser = subparsers.add_parser("optimize-benchmark")
    optimize_parser.add_argument("--optimization-spec", required=True)
    optimize_parser.add_argument("--output-root", required=True)

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
    parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
