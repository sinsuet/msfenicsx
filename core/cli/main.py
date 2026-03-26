"""Minimal command-line entrypoint for the clean rebuild."""

from __future__ import annotations

import argparse
from pathlib import Path
from collections.abc import Sequence

from core.generator.pipeline import generate_case
from core.io.scenario_runs import write_case_solution_bundle
from core.schema.io import load_case, load_template, save_case
from core.solver.nonlinear_solver import solve_case


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate-scenario-template")
    validate_parser.add_argument("--template", required=True)

    generate_parser = subparsers.add_parser("generate-case")
    generate_parser.add_argument("--template", required=True)
    generate_parser.add_argument("--seed", type=int, required=True)
    generate_parser.add_argument("--output-root", required=True)

    solve_parser = subparsers.add_parser("solve-case")
    solve_parser.add_argument("--case", required=True)
    solve_parser.add_argument("--output-root", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "validate-scenario-template":
        load_template(args.template)
        return 0
    if args.command == "generate-case":
        case = generate_case(args.template, seed=args.seed)
        output_root = Path(args.output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        save_case(case, output_root / f"{case.case_meta['case_id']}.yaml")
        return 0
    if args.command == "solve-case":
        case = load_case(args.case)
        solution = solve_case(case)
        write_case_solution_bundle(args.output_root, case, solution)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 0
