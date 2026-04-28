"""Raw constrained MOEA/D backbone wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.algorithms.moo.moead import MOEAD, default_decomp

from optimizers.clean_initialization import CleanBaselineSampling
from optimizers.raw_backbones.common import build_reference_directions, resolve_population_fraction_size


FAMILY = "decomposition"
BACKBONE = "moead"


class ConstrainedMOEAD(MOEAD):
    """Repository-owned constraint-aware MOEA/D variant for the benchmark."""

    def _setup(self, problem, **kwargs):
        if self.ref_dirs is None:
            self.ref_dirs = build_reference_directions(problem.n_obj, self.pop_size, self.reference_direction_parameters)
        self.pop_size = len(self.ref_dirs)
        self.neighbors = np.argsort(
            np.linalg.norm(self.ref_dirs[:, None, :] - self.ref_dirs[None, :, :], axis=2),
            axis=1,
            kind="quicksort",
        )[:, : self.n_neighbors]
        if self.decomposition is None:
            self.decomposition = default_decomp(problem)

    def _replace(self, k, off):
        pop = self.pop
        neighborhood = self.neighbors[k]
        objective_values = self.decomposition.do(
            pop[neighborhood].get("F"),
            weights=self.ref_dirs[neighborhood, :],
            ideal_point=self.ideal,
        )
        offspring_values = self.decomposition.do(
            off.F[None, :],
            weights=self.ref_dirs[neighborhood, :],
            ideal_point=self.ideal,
        )

        current_cv = np.asarray(pop[neighborhood].get("CV"), dtype=float).reshape(len(neighborhood), -1)[:, 0]
        offspring_cv = float(np.asarray(off.CV, dtype=float).reshape(-1)[0])
        replace_mask = np.asarray(
            [
                compare_moead_candidates(
                    current_candidate={
                        "label": "current",
                        "cv": current_neighbor_cv,
                        "scalar": current_neighbor_scalar,
                    },
                    offspring_candidate={
                        "label": "offspring",
                        "cv": offspring_cv,
                        "scalar": offspring_neighbor_scalar,
                    },
                )
                == "offspring"
                for current_neighbor_cv, current_neighbor_scalar, offspring_neighbor_scalar in zip(
                    current_cv,
                    objective_values,
                    offspring_values,
                    strict=True,
                )
            ],
            dtype=bool,
        )

        replace_indices = np.where(replace_mask)[0]
        pop[neighborhood[replace_indices]] = off


def compare_moead_candidates(
    *,
    current_candidate: dict[str, float | str],
    offspring_candidate: dict[str, float | str],
) -> str:
    current_label = str(current_candidate["label"])
    offspring_label = str(offspring_candidate["label"])
    current_cv = float(current_candidate["cv"])
    offspring_cv = float(offspring_candidate["cv"])
    current_scalar = float(current_candidate["scalar"])
    offspring_scalar = float(offspring_candidate["scalar"])

    current_feasible = current_cv <= 0.0
    offspring_feasible = offspring_cv <= 0.0
    if current_feasible and not offspring_feasible:
        return current_label
    if offspring_feasible and not current_feasible:
        return offspring_label
    if current_feasible and offspring_feasible:
        return offspring_label if offspring_scalar < current_scalar else current_label
    return offspring_label if offspring_cv < current_cv else current_label


def build_algorithm_kwargs(problem: Any, algorithm_config: dict[str, Any]) -> dict[str, Any]:
    pop_size = int(algorithm_config["population_size"])
    parameters = algorithm_config["parameters"]
    ref_dirs = build_reference_directions(problem.n_obj, pop_size, parameters["reference_directions"])
    n_neighbors = min(resolve_population_fraction_size(pop_size, parameters["neighbors"]), len(ref_dirs))
    return {
        "ref_dirs": ref_dirs,
        "n_neighbors": n_neighbors,
        "reference_direction_parameters": parameters["reference_directions"],
    }


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> ConstrainedMOEAD:
    kwargs = build_algorithm_kwargs(problem, algorithm_config)
    algorithm = ConstrainedMOEAD(
        ref_dirs=kwargs["ref_dirs"],
        n_neighbors=kwargs["n_neighbors"],
        sampling=CleanBaselineSampling(),
    )
    algorithm.reference_direction_parameters = kwargs["reference_direction_parameters"]
    return algorithm
