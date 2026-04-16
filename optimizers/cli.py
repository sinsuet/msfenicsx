"""Standalone CLI for optimizer-layer workflows."""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

from evaluation.io import load_spec
from llm.openai_compatible.replay import replay_request_trace_file, save_replay_summary
from optimizers.artifacts import write_optimization_artifacts
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.operator_pool.diagnostics import analyze_controller_trace, save_controller_trace_summary
from optimizers.run_manifest import write_run_manifest
from optimizers.run_suite import resolve_suite_mode_id, run_benchmark_suite


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def apply_algorithm_overrides(
    spec_dict: dict,
    *,
    population_size: int | None,
    num_generations: int | None,
) -> None:
    """Overwrite `algorithm.population_size` / `num_generations` when provided."""
    if population_size is not None:
        spec_dict.setdefault("algorithm", {})["population_size"] = int(population_size)
    if num_generations is not None:
        spec_dict.setdefault("algorithm", {})["num_generations"] = int(num_generations)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx-optimize")
    subparsers = parser.add_subparsers(dest="command")

    optimize_parser = subparsers.add_parser("optimize-benchmark")
    optimize_parser.add_argument("--optimization-spec", required=True)
    optimize_parser.add_argument("--output-root", required=True)
    optimize_parser.add_argument("--evaluation-workers", type=_positive_int, default=None)
    optimize_parser.add_argument("--population-size", type=_positive_int, default=None)
    optimize_parser.add_argument("--num-generations", type=_positive_int, default=None)
    optimize_parser.add_argument("--skip-render", action="store_true")

    suite_parser = subparsers.add_parser("run-benchmark-suite")
    suite_parser.add_argument("--optimization-spec", required=True, action="append")
    suite_parser.add_argument("--mode", action="append", default=[])
    suite_parser.add_argument("--scenario-runs-root", required=True)
    suite_parser.add_argument("--benchmark-seed", type=int, action="append", default=[])
    suite_parser.add_argument("--evaluation-workers", type=_positive_int, default=None)
    suite_parser.add_argument("--population-size", type=_positive_int, default=None)
    suite_parser.add_argument("--num-generations", type=_positive_int, default=None)
    suite_parser.add_argument("--skip-render", action="store_true")

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

    render_parser = subparsers.add_parser("render-assets")
    render_parser.add_argument("--run", required=True)
    render_parser.add_argument("--hires", action="store_true")

    compare_parser = subparsers.add_parser("compare-runs")
    compare_parser.add_argument("--run", required=True, action="append")
    compare_parser.add_argument("--output", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "optimize-benchmark":
        optimization_spec = load_optimization_spec(args.optimization_spec)
        apply_algorithm_overrides(
            optimization_spec.algorithm,
            population_size=args.population_size,
            num_generations=args.num_generations,
        )
        base_case = generate_benchmark_case(args.optimization_spec, optimization_spec)
        evaluation_spec_path = resolve_evaluation_spec_path(args.optimization_spec, optimization_spec)
        evaluation_spec = load_spec(evaluation_spec_path)
        mode = optimization_spec.algorithm["mode"]
        _wall_start = time.monotonic()
        if mode == "raw":
            run = run_raw_optimization(
                base_case,
                optimization_spec,
                evaluation_spec,
                spec_path=args.optimization_spec,
                evaluation_workers=args.evaluation_workers,
            )
        elif mode == "union":
            run = run_union_optimization(
                base_case,
                optimization_spec,
                evaluation_spec,
                spec_path=args.optimization_spec,
                evaluation_workers=args.evaluation_workers,
            )
        else:
            raise ValueError(f"Unsupported optimizer mode {mode!r}.")
        _wall_seconds = time.monotonic() - _wall_start
        evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
        write_optimization_artifacts(
            args.output_root,
            run,
            mode_id=resolve_suite_mode_id(optimization_spec),
            seed=int(optimization_spec.benchmark_source["seed"]),
            objective_definitions=list(evaluation_payload["objectives"]),
        )
        write_run_manifest(
            Path(args.output_root) / "run.yaml",
            mode=resolve_suite_mode_id(optimization_spec),
            benchmark_seed=int(optimization_spec.benchmark_source["seed"]),
            algorithm_seed=int(optimization_spec.algorithm["seed"]),
            optimization_spec_path=args.optimization_spec,
            evaluation_spec_path=str(evaluation_spec_path),
            population_size=int(optimization_spec.algorithm["population_size"]),
            num_generations=int(optimization_spec.algorithm["num_generations"]),
            wall_seconds=_wall_seconds,
        )
        if not args.skip_render:
            from optimizers.render_assets import render_run_assets
            render_run_assets(Path(args.output_root), hires=False)
        return 0
    if args.command == "run-benchmark-suite":
        run_benchmark_suite(
            optimization_spec_paths=[Path(path) for path in args.optimization_spec],
            benchmark_seeds=list(args.benchmark_seed),
            scenario_runs_root=Path(args.scenario_runs_root),
            modes=list(args.mode),
            evaluation_workers=args.evaluation_workers,
            population_size=args.population_size,
            num_generations=args.num_generations,
        )
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
        summary = analyze_controller_trace(
            Path(args.controller_trace),
            optimization_result_path=None if args.optimization_result is None else Path(args.optimization_result),
            operator_trace_path=None if args.operator_trace is None else Path(args.operator_trace),
            llm_request_trace_path=None if args.llm_request_trace is None else Path(args.llm_request_trace),
            llm_response_trace_path=None if args.llm_response_trace is None else Path(args.llm_response_trace),
        )
        save_controller_trace_summary(args.output, summary)
        return 0
    if args.command == "render-assets":
        from optimizers.render_assets import render_run_assets
        render_run_assets(Path(args.run), hires=args.hires)
        return 0
    if args.command == "compare-runs":
        from optimizers.compare_runs import compare_runs
        compare_runs(runs=[Path(r) for r in args.run], output=Path(args.output))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
