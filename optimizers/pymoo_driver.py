"""Compatibility wrapper for the active raw NSGA-II optimizer path."""

from __future__ import annotations

from typing import Any

from optimizers.drivers.raw_driver import OptimizationRun, run_raw_optimization


def run_multicase_optimization(base_cases: dict[str, Any], optimization_spec: Any, evaluation_spec: Any) -> OptimizationRun:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    algorithm_config = spec_payload["algorithm"]
    if algorithm_config["family"] != "genetic" or algorithm_config["backbone"] != "nsga2":
        raise ValueError(
            "The active pymoo driver currently supports only the raw NSGA-II backbone. "
            f"Received family={algorithm_config['family']!r}, backbone={algorithm_config['backbone']!r}."
        )
    if algorithm_config["mode"] != "raw":
        raise ValueError(
            "The active pymoo driver currently supports only algorithm.mode='raw'. "
            f"Received mode={algorithm_config['mode']!r}."
        )
    return run_raw_optimization(base_cases, optimization_spec, evaluation_spec)
