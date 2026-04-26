"""Clean, legality-aware initialization for tight layout search spaces."""

from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.core.sampling import Sampling

from optimizers.cheap_constraints import evaluate_cheap_constraints, resolve_radiator_span_max
from optimizers.codec import extract_decision_vector
from optimizers.repair import project_case_payload_from_vector


class CleanBaselineSampling(Sampling):
    """Seed genetic baselines from the generated legal layout and cheap-legal variants."""

    def _do(self, problem: Any, n_samples: int, *args: Any, random_state=None, **kwargs: Any) -> np.ndarray:
        del args, kwargs
        rng = random_state if random_state is not None else np.random.default_rng()
        n_samples = int(n_samples)
        if n_samples <= 0:
            return np.empty((0, int(problem.n_var)), dtype=np.float64)
        xl = np.asarray(problem.xl, dtype=np.float64)
        xu = np.asarray(problem.xu, dtype=np.float64)
        fallback = rng.uniform(xl, xu, size=(n_samples, int(problem.n_var)))
        if not all(hasattr(problem, name) for name in ("base_case", "optimization_spec", "evaluation_spec")):
            return fallback

        base_vector = np.asarray(extract_decision_vector(problem.base_case, problem.optimization_spec), dtype=np.float64)
        candidates: list[np.ndarray] = []
        seen: set[tuple[float, ...]] = set()

        def add_candidate(vector: np.ndarray, *, require_cheap_feasible: bool = True) -> None:
            if len(candidates) >= n_samples:
                return
            clipped = np.clip(np.asarray(vector, dtype=np.float64), xl, xu)
            if require_cheap_feasible and not _is_cheap_feasible(problem, clipped):
                return
            key = tuple(round(float(value), 12) for value in clipped.tolist())
            if key in seen:
                return
            seen.add(key)
            candidates.append(clipped)

        add_candidate(base_vector)
        for vector in _sink_sweep_vectors(problem, base_vector, n_samples=n_samples):
            add_candidate(vector)

        attempts = 0
        max_attempts = max(100, n_samples * 200)
        jitter_scales = (0.0025, 0.005, 0.0075, 0.01, 0.015)
        while len(candidates) < n_samples and attempts < max_attempts:
            scale = jitter_scales[min(attempts // max(1, n_samples * 20), len(jitter_scales) - 1)]
            proposal = base_vector + rng.normal(0.0, scale, size=base_vector.shape)
            add_candidate(proposal)
            attempts += 1

        for row in fallback:
            add_candidate(row, require_cheap_feasible=False)
        return np.asarray(candidates[:n_samples], dtype=np.float64)


def _is_cheap_feasible(problem: Any, vector: np.ndarray) -> bool:
    try:
        payload = project_case_payload_from_vector(
            problem.base_case,
            problem.optimization_spec,
            vector,
            radiator_span_max=resolve_radiator_span_max(problem.evaluation_spec),
        )
        return bool(evaluate_cheap_constraints(payload, problem.evaluation_spec).feasible)
    except Exception:
        return False


def _sink_sweep_vectors(problem: Any, base_vector: np.ndarray, *, n_samples: int) -> list[np.ndarray]:
    sink_indices = _sink_indices(problem.optimization_spec)
    if sink_indices is None:
        return []
    start_index, end_index = sink_indices
    xl = np.asarray(problem.xl, dtype=np.float64)
    xu = np.asarray(problem.xu, dtype=np.float64)
    span_limit = resolve_radiator_span_max(problem.evaluation_spec)
    current_span = max(0.0, float(base_vector[end_index] - base_vector[start_index]))
    span = current_span if span_limit is None else min(current_span, float(span_limit))
    span = max(0.0, min(span, float(xu[end_index] - xl[start_index])))
    if span <= 0.0:
        return []
    center_min = max(float(xl[start_index] + 0.5 * span), float(xl[end_index] - 0.5 * span))
    center_max = min(float(xu[start_index] + 0.5 * span), float(xu[end_index] - 0.5 * span))
    if center_max < center_min:
        return []
    center_count = max(2, min(max(2, n_samples - 1), 12))
    vectors: list[np.ndarray] = []
    for center in np.linspace(center_min, center_max, center_count):
        vector = np.asarray(base_vector, dtype=np.float64).copy()
        vector[start_index] = float(center - 0.5 * span)
        vector[end_index] = float(center + 0.5 * span)
        vectors.append(vector)
    return vectors


def _sink_indices(optimization_spec: Any) -> tuple[int, int] | None:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    start_index = None
    end_index = None
    for index, variable in enumerate(spec_payload.get("design_variables", [])):
        variable_id = str(variable.get("variable_id", ""))
        path = str(variable.get("path", ""))
        if variable_id == "sink_start" or path.endswith(".start"):
            start_index = index
        if variable_id == "sink_end" or path.endswith(".end"):
            end_index = index
    if start_index is None or end_index is None:
        return None
    return int(start_index), int(end_index)
