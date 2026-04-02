"""Standalone CLI for the evaluation layer."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from core.schema.io import load_case, load_solution
from evaluation.artifacts import write_evaluation_snapshot
from evaluation.engine import evaluate_case_solution
from evaluation.io import load_spec, save_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx-evaluate")
    subparsers = parser.add_subparsers(dest="command")

    evaluate_parser = subparsers.add_parser("evaluate-case")
    evaluate_parser.add_argument("--case", required=True)
    evaluate_parser.add_argument("--solution", required=True)
    evaluate_parser.add_argument("--spec", required=True)
    evaluate_parser.add_argument("--output", required=True)
    evaluate_parser.add_argument("--bundle-root")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "evaluate-case":
        case = load_case(args.case)
        solution = load_solution(args.solution)
        spec = load_spec(args.spec)
        report = evaluate_case_solution(case, solution, spec)
        save_report(report, args.output)
        if args.bundle_root:
            write_evaluation_snapshot(args.bundle_root, report)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
