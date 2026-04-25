"""Write the canonical run.yaml manifest at the top of each run."""

from __future__ import annotations

from pathlib import Path

import yaml


def write_run_manifest(
    path: Path,
    *,
    mode: str,
    benchmark_seed: int,
    algorithm_seed: int,
    optimization_spec_path: str,
    evaluation_spec_path: str,
    population_size: int,
    num_generations: int,
    wall_seconds: float,
    legality_policy_id: str,
) -> None:
    """Write run.yaml with the top-level schema agreed in § 3.1."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": mode,
        "seeds": {"benchmark": int(benchmark_seed), "algorithm": int(algorithm_seed)},
        "specs": {
            "optimization": optimization_spec_path,
            "evaluation": evaluation_spec_path,
        },
        "algorithm": {
            "population_size": int(population_size),
            "num_generations": int(num_generations),
        },
        "policies": {
            "legality": str(legality_policy_id),
            "replay_geometry_source": "evaluated_decision_vector",
        },
        "timing": {"wall_seconds": float(wall_seconds)},
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
