from __future__ import annotations

from pathlib import Path

from llm.openai_compatible.profile_loader import load_provider_profile_overlay


def execute_leaf(row: dict[str, str], *, evaluation_workers: int) -> dict[str, str]:
    from optimizers.cli import _run_optimize_benchmark, _temporary_env_overlay

    spec_path = Path(row["optimization_spec_snapshot"])
    output_root = Path(row["run_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    profile = row.get("llm_profile", "")
    if profile:
        overlay = load_provider_profile_overlay(profile)
        with _temporary_env_overlay(overlay):
            _run_optimize_benchmark(
                spec_path,
                output_root,
                evaluation_workers=evaluation_workers,
                skip_render=False,
            )
    else:
        _run_optimize_benchmark(
            spec_path,
            output_root,
            evaluation_workers=evaluation_workers,
            skip_render=False,
        )
    return {"status": "completed"}
