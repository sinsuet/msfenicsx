"""Per-generation rollups over evaluation events."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from optimizers.analytics.pareto import hypervolume_2d


def rollup_per_generation(
    events: Iterable[dict[str, Any]],
    *,
    reference_point: tuple[float, float],
) -> list[dict[str, Any]]:
    """Return one summary dict per generation, sorted by generation index."""
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        buckets[int(event["generation"])].append(event)

    seen_points: list[tuple[float, float]] = []
    summaries: list[dict[str, Any]] = []
    for generation in sorted(buckets):
        rows = buckets[generation]
        feasible = [r for r in rows if r.get("status") == "ok" and r.get("objectives")]
        for row in feasible:
            obj = row["objectives"]
            seen_points.append(
                (float(obj["temperature_max"]), float(obj["temperature_gradient_rms"]))
            )
        hv = hypervolume_2d(seen_points, reference_point=reference_point) if seen_points else 0.0
        front_points = [
            (float(r["objectives"]["temperature_max"]), float(r["objectives"]["temperature_gradient_rms"]))
            for r in feasible
        ]
        summaries.append(
            {
                "generation": generation,
                "population_size": len(rows),
                "num_feasible": len(feasible),
                "num_infeasible": len(rows) - len(feasible),
                "front_objectives": front_points,
                "hypervolume": hv,
            }
        )
    return summaries
