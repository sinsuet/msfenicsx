"""Standalone CLI for optimizer-layer workflows."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path

from evaluation.io import load_spec
from llm.openai_compatible.profile_loader import load_provider_profile_overlay
from llm.openai_compatible.replay import replay_request_trace_file, save_replay_summary
from optimizers.artifacts import write_optimization_artifacts
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.operator_pool.diagnostics import analyze_controller_trace, save_controller_trace_summary
from optimizers.run_suite import resolve_suite_mode_id, run_benchmark_suite


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx-optimize")
    subparsers = parser.add_subparsers(dest="command")

    optimize_parser = subparsers.add_parser("optimize-benchmark")
    optimize_parser.add_argument("--optimization-spec", required=True)
    optimize_parser.add_argument("--output-root", required=True)
    optimize_parser.add_argument("--evaluation-workers", type=_positive_int, default=None)

    run_llm_parser = subparsers.add_parser("run-llm")
    run_llm_parser.add_argument("profile")
    run_llm_parser.add_argument("--optimization-spec", required=True)
    run_llm_parser.add_argument("--output-root", required=True)
    run_llm_parser.add_argument("--evaluation-workers", type=_positive_int, default=None)

    suite_parser = subparsers.add_parser("run-benchmark-suite")
    suite_parser.add_argument("--optimization-spec", required=True, action="append")
    suite_parser.add_argument("--mode", action="append", default=[])
    suite_parser.add_argument("--scenario-runs-root", required=True)
    suite_parser.add_argument("--benchmark-seed", type=int, action="append", default=[])
    suite_parser.add_argument("--evaluation-workers", type=_positive_int, default=None)

    replay_parser = subparsers.add_parser("replay-llm-trace")
    replay_parser.add_argument("--optimization-spec", required=True)
    replay_parser.add_argument("--request-trace", required=True)
    replay_parser.add_argument("--output", required=True)
    replay_parser.add_argument("--limit", type=int, default=None)

    diagnostics_parser = subparsers.add_parser("analyze-controller-trace")
    diagnostics_parser.add_argument("--controller-trace", required=True)
    diagnostics_parser.add_argument("--optimization-result", required=False)
    diagnostics_parser.add_argument("--operator-trace", required=False)
    diagnostics_parser.add_argument("--llm-request-trace", required=False)
    diagnostics_parser.add_argument("--llm-response-trace", required=False)
    diagnostics_parser.add_argument("--output", required=True)

    return parser


def _run_optimize_benchmark(
    optimization_spec_path: str | Path,
    output_root: str | Path,
    *,
    evaluation_workers: int | None,
    optimization_spec=None,
) -> int:
    optimization_spec = (
        load_optimization_spec(optimization_spec_path) if optimization_spec is None else optimization_spec
    )
    base_case = generate_benchmark_case(optimization_spec_path, optimization_spec)
    evaluation_spec_path = resolve_evaluation_spec_path(optimization_spec_path, optimization_spec)
    evaluation_spec = load_spec(evaluation_spec_path)
    mode = optimization_spec.algorithm["mode"]
    if mode == "raw":
        run = run_raw_optimization(
            base_case,
            optimization_spec,
            evaluation_spec,
            spec_path=optimization_spec_path,
            evaluation_workers=evaluation_workers,
        )
    elif mode == "union":
        run = run_union_optimization(
            base_case,
            optimization_spec,
            evaluation_spec,
            spec_path=optimization_spec_path,
            evaluation_workers=evaluation_workers,
        )
    else:
        raise ValueError(f"Unsupported optimizer mode {mode!r}.")
    evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
    write_optimization_artifacts(
        output_root,
        run,
        mode_id=resolve_suite_mode_id(optimization_spec),
        seed=int(optimization_spec.benchmark_source["seed"]),
        objective_definitions=list(evaluation_payload["objectives"]),
    )
    return 0


def _require_llm_optimization_spec(optimization_spec, *, command_name: str) -> None:
    operator_control = optimization_spec.operator_control
    if operator_control is None or operator_control.get("controller") != "llm":
        raise ValueError(f"{command_name} requires an optimization spec with operator_control.controller='llm'.")


@contextmanager
def _temporary_env_overlay(values: dict[str, str]):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "optimize-benchmark":
        return _run_optimize_benchmark(
            args.optimization_spec,
            args.output_root,
            evaluation_workers=args.evaluation_workers,
        )
    if args.command == "run-llm":
        optimization_spec = load_optimization_spec(args.optimization_spec)
        _require_llm_optimization_spec(optimization_spec, command_name="run-llm")
        overlay = load_provider_profile_overlay(args.profile)
        with _temporary_env_overlay(overlay):
            return _run_optimize_benchmark(
                args.optimization_spec,
                args.output_root,
                evaluation_workers=args.evaluation_workers,
                optimization_spec=optimization_spec,
            )
    if args.command == "run-benchmark-suite":
        run_benchmark_suite(
            optimization_spec_paths=[Path(path) for path in args.optimization_spec],
            benchmark_seeds=list(args.benchmark_seed),
            scenario_runs_root=Path(args.scenario_runs_root),
            modes=list(args.mode),
            evaluation_workers=args.evaluation_workers,
        )
        return 0
    if args.command == "replay-llm-trace":
        optimization_spec = load_optimization_spec(args.optimization_spec)
        _require_llm_optimization_spec(optimization_spec, command_name="replay-llm-trace")
        operator_control = optimization_spec.operator_control
        assert operator_control is not None
        replay_summary = replay_request_trace_file(
            Path(args.request_trace),
            dict(operator_control["controller_parameters"]),
            limit=args.limit,
        )
        save_replay_summary(args.output, replay_summary)
        return 0
    if args.command == "analyze-controller-trace":
        summary = analyze_controller_trace(
            Path(args.controller_trace),
            optimization_result_path=None if args.optimization_result is None else Path(args.optimization_result),
            operator_trace_path=None if args.operator_trace is None else Path(args.operator_trace),
            llm_request_trace_path=None if args.llm_request_trace is None else Path(args.llm_request_trace),
            llm_response_trace_path=None if args.llm_response_trace is None else Path(args.llm_response_trace),
        )
        save_controller_trace_summary(args.output, summary)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
