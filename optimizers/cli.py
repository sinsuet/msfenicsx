"""Standalone CLI for optimizer-layer workflows."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path

from llm.openai_compatible.profile_loader import load_provider_profile_overlay
from optimizers.benchmark_runner.comparisons import plan_campaign_comparisons
from optimizers.benchmark_runner.specs import build_single_leaf_campaign, load_campaigns_from_batch_spec
from optimizers.benchmark_runner.supervisor import run_campaign_supervisor


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def apply_algorithm_overrides(
    algorithm_dict: dict,
    *,
    population_size: int | None,
    num_generations: int | None,
) -> None:
    """Overwrite ``population_size`` / ``num_generations`` on an algorithm dict when provided."""
    if population_size is not None:
        algorithm_dict["population_size"] = int(population_size)
    if num_generations is not None:
        algorithm_dict["num_generations"] = int(num_generations)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx-optimize")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run-benchmark")
    run_parser.add_argument("--batch-spec")
    run_parser.add_argument("--optimization-spec")
    run_parser.add_argument("--mode", choices=["raw", "union", "llm"])
    run_parser.add_argument("--llm-profile")
    run_parser.add_argument("--benchmark-seed", type=int)
    run_parser.add_argument("--algorithm-seed", type=int)
    run_parser.add_argument("--population-size", type=_positive_int)
    run_parser.add_argument("--num-generations", type=_positive_int)
    run_parser.add_argument("--evaluation-workers", type=_positive_int, default=32)
    run_parser.add_argument("--scenario-runs-root", default="./scenario_runs")
    run_parser.add_argument("--campaign-id")
    run_parser.add_argument("--compare-with", action="append", default=[])

    return parser


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


def _llm_env_overlay_for_spec(
    optimization_spec,
    *,
    profile_id: str = "default",
    prefer_spec_profile: bool = True,
) -> dict[str, str]:
    operator_control = getattr(optimization_spec, "operator_control", None)
    if operator_control is None or operator_control.get("controller") != "llm":
        return {}
    if prefer_spec_profile:
        profile_id = _resolve_llm_provider_profile(optimization_spec, fallback_profile_id=profile_id)
    core_keys = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")
    missing_keys = [
        key
        for key in core_keys
        if not str(os.environ.get(key, "")).strip()
    ]
    if not missing_keys:
        return {}
    try:
        overlay = load_provider_profile_overlay(profile_id)
    except Exception:
        return {}
    return {
        key: str(value)
        for key, value in overlay.items()
        if (key in missing_keys or key not in core_keys and not str(os.environ.get(key, "")).strip())
        and str(value).strip()
    }


def _resolve_llm_provider_profile(optimization_spec, *, fallback_profile_id: str = "default") -> str:
    operator_control = getattr(optimization_spec, "operator_control", None)
    if not isinstance(operator_control, dict):
        return str(fallback_profile_id)
    controller_parameters = operator_control.get("controller_parameters")
    if not isinstance(controller_parameters, dict):
        return str(fallback_profile_id)
    provider_profile = str(controller_parameters.get("provider_profile", "")).strip()
    return provider_profile or str(fallback_profile_id)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "run-benchmark":
        if args.batch_spec:
            campaigns = load_campaigns_from_batch_spec(args.batch_spec)
        else:
            required = {
                "--optimization-spec": args.optimization_spec,
                "--mode": args.mode,
                "--benchmark-seed": args.benchmark_seed,
                "--algorithm-seed": args.algorithm_seed,
                "--population-size": args.population_size,
                "--num-generations": args.num_generations,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                parser.error("run-benchmark single leaf missing: " + ", ".join(missing))
            campaigns = [
                build_single_leaf_campaign(
                    optimization_spec=Path(args.optimization_spec),
                    mode=args.mode,
                    llm_profile=args.llm_profile,
                    benchmark_seed=args.benchmark_seed,
                    algorithm_seed=args.algorithm_seed,
                    population_size=args.population_size,
                    num_generations=args.num_generations,
                    evaluation_workers=args.evaluation_workers,
                    scenario_runs_root=Path(args.scenario_runs_root),
                    campaign_id=args.campaign_id,
                    compare_with=[Path(path) for path in args.compare_with],
                )
            ]
        for campaign in campaigns:
            run_root = run_campaign_supervisor(campaign)
            plan_campaign_comparisons(run_root, compare_with=list(getattr(campaign, "compare_with", ())))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
