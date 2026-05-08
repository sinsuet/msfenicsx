"""Internal subprocess entrypoint for one benchmark leaf."""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from evaluation.io import load_spec
from llm.openai_compatible.profile_loader import load_provider_profile_overlay
from optimizers.artifacts import write_optimization_artifacts
from optimizers.benchmark_runner.postprocess import build_runtime_summary, run_leaf_postprocess, write_runtime_summary
from optimizers.benchmark_runner.run_events import RunEventWriter
from optimizers.cli import _temporary_env_overlay, apply_algorithm_overrides
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.run_manifest import write_run_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="benchmark-leaf")
    parser.add_argument("--optimization-spec", required=True)
    parser.add_argument("--mode", required=True, choices=["raw", "union", "llm"])
    parser.add_argument("--benchmark-seed", type=int, required=True)
    parser.add_argument("--algorithm-seed", type=int, required=True)
    parser.add_argument("--population-size", type=int, required=True)
    parser.add_argument("--num-generations", type=int, required=True)
    parser.add_argument("--evaluation-workers", type=int, required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--method-id", required=True)
    parser.add_argument("--llm-profile", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    spec_path = Path(args.optimization_spec)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    event_path = output_root / "traces" / "run_events.jsonl"
    run_start = time.monotonic()

    with RunEventWriter(event_path) as event_writer:
        optimization_spec = load_optimization_spec(spec_path)
        _apply_leaf_overrides(
            optimization_spec,
            benchmark_seed=args.benchmark_seed,
            algorithm_seed=args.algorithm_seed,
            population_size=args.population_size,
            num_generations=args.num_generations,
            mode=args.mode,
        )
        scenario_id = _scenario_id_from_case_meta(generate_benchmark_case(spec_path, optimization_spec))
        event_writer.write(
            "leaf_started",
            scenario_id=scenario_id,
            method_id=args.method_id,
            mode=args.mode,
            llm_profile=args.llm_profile,
            seed=args.benchmark_seed,
            message="leaf started",
            metrics={
                "population_size": args.population_size,
                "num_generations": args.num_generations,
                "evaluation_workers": args.evaluation_workers,
            },
        )

        base_case = generate_benchmark_case(spec_path, optimization_spec)
        scenario_id = _scenario_id_from_case_meta(base_case)
        evaluation_spec_path = resolve_evaluation_spec_path(spec_path, optimization_spec)
        evaluation_spec = load_spec(evaluation_spec_path)
        evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
        objective_definitions = list(evaluation_payload["objectives"])
        optimizer_start = time.monotonic()
        with _temporary_env_overlay(_leaf_llm_env_overlay(args.llm_profile)):
            if args.mode == "raw":
                run = run_raw_optimization(
                    base_case,
                    optimization_spec,
                    evaluation_spec,
                    spec_path=spec_path,
                    evaluation_workers=args.evaluation_workers,
                )
            else:
                run = run_union_optimization(
                    base_case,
                    optimization_spec,
                    evaluation_spec,
                    spec_path=spec_path,
                    evaluation_workers=args.evaluation_workers,
                    trace_output_root=output_root,
                )
        optimizer_wall_seconds = time.monotonic() - optimizer_start

        write_optimization_artifacts(
            output_root,
            run,
            mode_id=args.mode,
            seed=args.benchmark_seed,
            objective_definitions=objective_definitions,
        )
        run_wall_before_postprocess = time.monotonic() - run_start
        _write_leaf_run_manifest(
            output_root,
            args=args,
            optimization_spec=optimization_spec,
            evaluation_spec_path=evaluation_spec_path,
            wall_seconds=run_wall_before_postprocess,
            status="running",
            postprocess_wall_seconds=None,
        )
        postprocess_start = time.monotonic()
        try:
            run_leaf_postprocess(
                output_root,
                mode=args.mode,
                llm_profile=args.llm_profile,
                optimization_spec_path=spec_path,
            )
        except Exception as exc:
            event_writer.write(
                "leaf_failed",
                scenario_id=scenario_id,
                method_id=args.method_id,
                mode=args.mode,
                llm_profile=args.llm_profile,
                seed=args.benchmark_seed,
                message=f"postprocess failed: {exc}",
                metrics={"postprocess_error": str(exc)},
            )
            raise
        postprocess_wall_seconds = time.monotonic() - postprocess_start
        run_wall_seconds = time.monotonic() - run_start
        _write_leaf_run_manifest(
            output_root,
            args=args,
            optimization_spec=optimization_spec,
            evaluation_spec_path=evaluation_spec_path,
            wall_seconds=run_wall_seconds,
            status="completed",
            postprocess_wall_seconds=postprocess_wall_seconds,
        )
        runtime_summary = build_runtime_summary(
            scenario_id=scenario_id,
            method_id=args.method_id,
            mode=args.mode,
            seed=args.benchmark_seed,
            population_size=args.population_size,
            num_generations=args.num_generations,
            run_wall_seconds=run_wall_seconds,
            optimizer_wall_seconds=optimizer_wall_seconds,
            baseline_wall_seconds=0.0,
            postprocess_wall_seconds=postprocess_wall_seconds,
            render_wall_seconds=0.0,
            history=_run_history(run),
        )
        if args.llm_profile is not None:
            runtime_summary["llm_profile"] = args.llm_profile
        write_runtime_summary(output_root, runtime_summary)
        event_writer.write(
            "leaf_completed",
            scenario_id=scenario_id,
            method_id=args.method_id,
            mode=args.mode,
            llm_profile=args.llm_profile,
            seed=args.benchmark_seed,
            message="leaf completed",
            metrics={"run_wall_seconds": run_wall_seconds, "optimizer_wall_seconds": optimizer_wall_seconds},
        )
    return 0


def _apply_leaf_overrides(
    optimization_spec: Any,
    *,
    benchmark_seed: int,
    algorithm_seed: int,
    population_size: int,
    num_generations: int,
    mode: str,
) -> None:
    optimization_spec.benchmark_source["seed"] = int(benchmark_seed)
    optimization_spec.algorithm["seed"] = int(algorithm_seed)
    optimization_spec.algorithm["mode"] = "union" if mode == "llm" else str(mode)
    apply_algorithm_overrides(
        optimization_spec.algorithm,
        population_size=population_size,
        num_generations=num_generations,
    )


def _leaf_llm_env_overlay(llm_profile: str | None) -> dict[str, str]:
    if not llm_profile:
        return {}
    return load_provider_profile_overlay(llm_profile)


def _write_leaf_run_manifest(
    output_root: Path,
    *,
    args: argparse.Namespace,
    optimization_spec: Any,
    evaluation_spec_path: Path,
    wall_seconds: float,
    status: str,
    postprocess_wall_seconds: float | None,
) -> None:
    write_run_manifest(
        output_root / "run.yaml",
        mode=args.mode,
        algorithm_family=str(optimization_spec.algorithm["family"]),
        algorithm_backbone=str(optimization_spec.algorithm["backbone"]),
        benchmark_seed=args.benchmark_seed,
        algorithm_seed=args.algorithm_seed,
        optimization_spec_path=str(args.optimization_spec),
        evaluation_spec_path=str(evaluation_spec_path),
        population_size=args.population_size,
        num_generations=args.num_generations,
        wall_seconds=wall_seconds,
        legality_policy_id=str(optimization_spec.evaluation_protocol["legality_policy_id"]),
        method_id=args.method_id,
        llm_profile=args.llm_profile,
        status=status,
        postprocess_wall_seconds=postprocess_wall_seconds,
    )


def _scenario_id_from_case_meta(case: Any) -> str:
    payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    return str(payload["case_meta"]["scenario_id"])


def _run_history(run: Any) -> list[dict[str, Any]]:
    result = getattr(run, "result")
    history = getattr(result, "history", [])
    return [dict(row) for row in history]


if __name__ == "__main__":
    raise SystemExit(main())
