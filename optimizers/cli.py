"""Standalone CLI for optimizer-layer workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from evaluation.io import load_multicase_spec
from evaluation.operating_cases import load_named_cases
from optimizers.artifacts import write_optimization_artifacts
from optimizers.io import load_optimization_spec, resolve_evaluation_spec_path
from optimizers.pymoo_driver import run_multicase_optimization


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx-optimize")
    subparsers = parser.add_subparsers(dest="command")

    optimize_parser = subparsers.add_parser("optimize-operating-cases")
    optimize_parser.add_argument("--case", action="append", required=True)
    optimize_parser.add_argument("--optimization-spec", required=True)
    optimize_parser.add_argument("--output-root", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "optimize-operating-cases":
        cases = load_named_cases(list(args.case))
        optimization_spec = load_optimization_spec(args.optimization_spec)
        evaluation_spec_path = resolve_evaluation_spec_path(args.optimization_spec, optimization_spec)
        evaluation_spec = load_multicase_spec(evaluation_spec_path)
        run = run_multicase_optimization(cases, optimization_spec, evaluation_spec)
        write_optimization_artifacts(args.output_root, run)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
