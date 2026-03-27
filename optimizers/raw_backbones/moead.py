"""Raw constrained MOEA/D backbone wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.algorithms.moo.moead import MOEAD, default_decomp
from pymoo.util.ref_dirs import get_reference_directions


FAMILY = "decomposition"
BACKBONE = "moead"


class ConstrainedMOEAD(MOEAD):
    """Repository-owned constraint-aware MOEA/D variant for the benchmark."""

    def _setup(self, problem, **kwargs):
        if self.ref_dirs is None:
            self.ref_dirs = get_reference_directions("energy", problem.n_obj, n_points=self.pop_size)
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
        current_feasible = current_cv <= 0.0
        offspring_feasible = offspring_cv <= 0.0

        replace_mask = np.zeros(len(neighborhood), dtype=bool)
        if offspring_feasible:
            replace_mask = np.logical_not(current_feasible)
            replace_mask |= np.logical_and(current_feasible, offspring_values < objective_values)
        else:
            replace_mask = np.logical_and(np.logical_not(current_feasible), offspring_cv < current_cv)

        replace_indices = np.where(replace_mask)[0]
        pop[neighborhood[replace_indices]] = off


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> ConstrainedMOEAD:
    pop_size = int(algorithm_config["population_size"])
    ref_dirs = get_reference_directions("energy", problem.n_obj, n_points=pop_size)
    n_neighbors = min(max(2, pop_size // 2), len(ref_dirs))
    return ConstrainedMOEAD(ref_dirs=ref_dirs, n_neighbors=n_neighbors)
