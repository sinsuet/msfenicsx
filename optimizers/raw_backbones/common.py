"""Shared builders for raw backbone operators and reference-direction helpers."""

from __future__ import annotations

from typing import Any

from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.util.reference_direction import get_number_of_uniform_points, get_partition_closest_to_points


def build_reference_directions(n_obj: int, pop_size: int, parameters: dict[str, Any]) -> Any:
    scheme = str(parameters.get("scheme", "energy"))
    if scheme == "energy":
        return get_reference_directions("energy", n_obj, n_points=pop_size)
    if scheme == "uniform":
        n_partitions = get_partition_closest_to_points(pop_size, n_obj)
        n_ref_dirs = get_number_of_uniform_points(n_partitions, n_obj)
        return get_reference_directions("uniform", n_obj, n_points=n_ref_dirs)
    raise ValueError(f"Unsupported reference_directions.scheme '{scheme}'.")


def build_sbx(parameters: dict[str, Any]) -> SBX:
    kwargs: dict[str, Any] = {
        "eta": float(parameters["eta"]),
        "prob": float(parameters["prob"]),
    }
    if "n_offsprings" in parameters:
        kwargs["n_offsprings"] = int(parameters["n_offsprings"])
    return SBX(**kwargs)


def build_pm(parameters: dict[str, Any]) -> PM:
    kwargs: dict[str, Any] = {
        "eta": float(parameters["eta"]),
    }
    if "prob_var" in parameters:
        kwargs["prob_var"] = parameters["prob_var"]
    return PM(**kwargs)


def resolve_population_fraction_size(pop_size: int, parameters: dict[str, Any]) -> int:
    strategy = str(parameters.get("strategy", "half_population"))
    minimum = int(parameters.get("min_size", 1))
    if strategy != "half_population":
        raise ValueError(f"Unsupported population sizing strategy '{strategy}'.")
    return min(max(minimum, pop_size // 2), pop_size)
