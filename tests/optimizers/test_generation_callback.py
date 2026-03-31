from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from optimizers.generation_callback import GenerationSummaryCallback


class _FakePopulation:
    def __init__(self, *, F: np.ndarray, G: np.ndarray) -> None:
        self._payload = {
            "F": np.asarray(F, dtype=np.float64),
            "G": np.asarray(G, dtype=np.float64),
        }

    def get(self, *keys):
        if len(keys) == 1:
            return self._payload[keys[0]]
        return tuple(self._payload[key] for key in keys)

    def __len__(self) -> int:
        return int(len(self._payload["F"]))


def test_generation_callback_records_generation_boundaries() -> None:
    callback = GenerationSummaryCallback(
        objective_ids=(
            "minimize_hot_pa_peak",
            "maximize_cold_battery_min",
            "minimize_radiator_resource",
        )
    )
    algorithm = SimpleNamespace(
        n_iter=3,
        pop=_FakePopulation(
            F=np.asarray(
                [
                    [301.0, -258.0, 0.48],
                    [299.0, -257.5, 0.45],
                ],
                dtype=np.float64,
            ),
            G=np.asarray(
                [
                    [0.0, 0.0, 0.0],
                    [0.0, 0.1, 0.0],
                ],
                dtype=np.float64,
            ),
        ),
        problem=SimpleNamespace(
            history=[
                {"evaluation_index": 1, "feasible": False},
                {"evaluation_index": 2, "feasible": False},
                {"evaluation_index": 3, "feasible": True},
            ]
        ),
    )

    callback.notify(algorithm)

    assert callback.rows[-1]["generation_index"] == 3
    assert callback.rows[-1]["num_evaluations_so_far"] == 3
    assert callback.rows[-1]["feasible_fraction"] == pytest.approx(0.5)
    assert callback.rows[-1]["best_total_constraint_violation"] == pytest.approx(0.0)
    assert callback.rows[-1]["best_hot_pa_peak"] == pytest.approx(299.0)
    assert callback.rows[-1]["best_cold_battery_min"] == pytest.approx(258.0)
    assert callback.rows[-1]["pareto_size"] >= 1
