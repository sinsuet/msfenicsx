"""Clean, legality-aware initialization for tight layout search spaces."""

from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.core.sampling import Sampling

from optimizers.cheap_constraints import evaluate_cheap_constraints, resolve_radiator_span_max
from optimizers.codec import extract_decision_vector
from optimizers.repair import project_case_payload_from_vector


class CleanBaselineSampling(Sampling):
    """Seed raw baselines from the generated legal layout and cheap-legal variants."""

    def _do(self, problem: Any, n_samples: int, *args: Any, random_state=None, **kwargs: Any) -> np.ndarray:
        del args, kwargs
        rng = random_state if random_state is not None else np.random.default_rng()
        n_samples = int(n_samples)
        if n_samples <= 0:
            return np.empty((0, int(problem.n_var)), dtype=np.float64)
        xl = np.asarray(problem.xl, dtype=np.float64)
        xu = np.asarray(problem.xu, dtype=np.float64)
        if not all(hasattr(problem, name) for name in ("base_case", "optimization_spec", "evaluation_spec")):
            return rng.uniform(xl, xu, size=(n_samples, int(problem.n_var)))

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
        for vector in _sink_sweep_vectors(problem, base_vector, n_samples=_sink_sweep_sample_count(n_samples)):
            add_candidate(vector)

        _add_component_jitter_candidates(problem, base_vector, candidates, seen, n_samples, rng)
        _add_component_block_shift_candidates(problem, base_vector, candidates, seen, n_samples, rng)

        attempts = 0
        max_attempts = max(100, n_samples * 200)
        jitter_scales = (0.01, 0.02, 0.03, 0.045)
        anchor_vectors = _sink_anchor_vectors(problem, base_vector)
        while len(candidates) < n_samples and attempts < max_attempts:
            scale = jitter_scales[min(attempts // max(1, n_samples * 20), len(jitter_scales) - 1)]
            anchor = anchor_vectors[attempts % len(anchor_vectors)] if anchor_vectors else base_vector
            proposal = np.asarray(anchor, dtype=np.float64).copy()
            proposal += rng.normal(0.0, scale, size=base_vector.shape)
            proposal = _restore_sink_from_anchor(problem, proposal, anchor)
            add_candidate(proposal)
            attempts += 1

        _add_limited_anchor_fallback(problem, base_vector, candidates, seen, n_samples, rng)
        _add_low_risk_component_refill(problem, base_vector, candidates, seen, n_samples)
        _add_shape_preserving_anchor_refill(problem, base_vector, candidates, seen, n_samples)
        return np.asarray(candidates[:n_samples], dtype=np.float64)


def _sink_sweep_sample_count(n_samples: int) -> int:
    if n_samples <= 4:
        return max(2, n_samples - 1)
    return max(2, min(6, int(round(float(n_samples) * 0.30))))


def _add_component_jitter_candidates(
    problem: Any,
    base_vector: np.ndarray,
    candidates: list[np.ndarray],
    seen: set[tuple[float, ...]],
    n_samples: int,
    rng: np.random.Generator,
) -> None:
    target_count = max(1, int(round(float(n_samples) * 0.35)))
    _add_component_perturbations(
        problem,
        base_vector,
        candidates,
        seen,
        n_samples,
        rng,
        target_new_candidates=target_count,
        component_count_range=(2, 5),
        shift_scale_range=(0.025, 0.07),
        coherent_shift=False,
        anchor_vectors=_sink_anchor_vectors(problem, base_vector),
    )


def _add_component_block_shift_candidates(
    problem: Any,
    base_vector: np.ndarray,
    candidates: list[np.ndarray],
    seen: set[tuple[float, ...]],
    n_samples: int,
    rng: np.random.Generator,
) -> None:
    target_count = max(1, int(round(float(n_samples) * 0.20)))
    _add_component_perturbations(
        problem,
        base_vector,
        candidates,
        seen,
        n_samples,
        rng,
        target_new_candidates=target_count,
        component_count_range=(3, 7),
        shift_scale_range=(0.02, 0.055),
        coherent_shift=True,
        anchor_vectors=_sink_anchor_vectors(problem, base_vector),
    )


def _add_component_perturbations(
    problem: Any,
    base_vector: np.ndarray,
    candidates: list[np.ndarray],
    seen: set[tuple[float, ...]],
    n_samples: int,
    rng: np.random.Generator,
    *,
    target_new_candidates: int,
    component_count_range: tuple[int, int],
    shift_scale_range: tuple[float, float],
    coherent_shift: bool,
    anchor_vectors: list[np.ndarray] | None = None,
) -> None:
    component_pairs = _component_xy_indices(problem.optimization_spec)
    if not component_pairs:
        return
    xl = np.asarray(problem.xl, dtype=np.float64)
    xu = np.asarray(problem.xu, dtype=np.float64)
    anchors = anchor_vectors or [base_vector]
    added = 0
    attempts = 0
    max_attempts = max(80, target_new_candidates * 80)
    while len(candidates) < n_samples and added < target_new_candidates and attempts < max_attempts:
        anchor = anchors[attempts % len(anchors)]
        proposal = np.asarray(anchor, dtype=np.float64).copy()
        component_count = int(rng.integers(component_count_range[0], component_count_range[1] + 1))
        component_count = min(component_count, len(component_pairs))
        selected_indices = rng.choice(len(component_pairs), size=component_count, replace=False)
        if coherent_shift:
            angle = float(rng.uniform(0.0, 2.0 * np.pi))
            magnitude = float(rng.uniform(*shift_scale_range))
            shared_shift = np.asarray([np.cos(angle), np.sin(angle)], dtype=np.float64) * magnitude
        else:
            shared_shift = None
        for selected_index in np.atleast_1d(selected_indices):
            x_index, y_index = component_pairs[int(selected_index)]
            if shared_shift is None:
                angle = float(rng.uniform(0.0, 2.0 * np.pi))
                magnitude = float(rng.uniform(*shift_scale_range))
                shift = np.asarray([np.cos(angle), np.sin(angle)], dtype=np.float64) * magnitude
            else:
                shift = shared_shift
            proposal[x_index] += float(shift[0])
            proposal[y_index] += float(shift[1])
        proposal = np.clip(proposal, xl, xu)
        proposal = _restore_sink_from_anchor(problem, proposal, anchor)
        key = tuple(round(float(value), 12) for value in proposal.tolist())
        if key not in seen and _is_cheap_feasible(problem, proposal):
            seen.add(key)
            candidates.append(proposal)
            added += 1
        attempts += 1

def _add_limited_anchor_fallback(
    problem: Any,
    base_vector: np.ndarray,
    candidates: list[np.ndarray],
    seen: set[tuple[float, ...]],
    n_samples: int,
    rng: np.random.Generator,
) -> None:
    component_pairs = _component_xy_indices(problem.optimization_spec)
    if not component_pairs:
        return
    xl = np.asarray(problem.xl, dtype=np.float64)
    xu = np.asarray(problem.xu, dtype=np.float64)
    anchors = _sink_anchor_vectors(problem, base_vector)
    target_count = min(2, max(0, n_samples - len(candidates)))
    added = 0
    attempts = 0
    max_attempts = max(80, target_count * 80)
    while len(candidates) < n_samples and added < target_count and attempts < max_attempts:
        anchor = anchors[attempts % len(anchors)] if anchors else base_vector
        proposal = np.asarray(anchor, dtype=np.float64).copy()
        component_count = min(int(rng.integers(4, 9)), len(component_pairs))
        selected_indices = rng.choice(len(component_pairs), size=component_count, replace=False)
        for selected_index in np.atleast_1d(selected_indices):
            x_index, y_index = component_pairs[int(selected_index)]
            proposal[x_index] += float(rng.uniform(-0.08, 0.08))
            proposal[y_index] += float(rng.uniform(-0.08, 0.08))
        proposal = np.clip(proposal, xl, xu)
        proposal = _restore_sink_from_anchor(problem, proposal, anchor)
        key = tuple(round(float(value), 12) for value in proposal.tolist())
        if key not in seen and _is_cheap_feasible(problem, proposal):
            seen.add(key)
            candidates.append(proposal)
            added += 1
        attempts += 1


def _add_low_risk_component_refill(
    problem: Any,
    base_vector: np.ndarray,
    candidates: list[np.ndarray],
    seen: set[tuple[float, ...]],
    n_samples: int,
) -> None:
    component_pairs = _component_xy_indices(problem.optimization_spec)
    if not component_pairs:
        return
    xl = np.asarray(problem.xl, dtype=np.float64)
    xu = np.asarray(problem.xu, dtype=np.float64)
    anchors = _sink_anchor_vectors(problem, base_vector)
    directions = (
        np.asarray([1.0, 0.0], dtype=np.float64),
        np.asarray([-1.0, 0.0], dtype=np.float64),
        np.asarray([0.0, 1.0], dtype=np.float64),
        np.asarray([0.0, -1.0], dtype=np.float64),
    )
    magnitudes = (0.012, 0.018, 0.024, 0.03)
    attempt = 0
    max_attempts = max(120, n_samples * len(component_pairs) * len(directions))
    while len(candidates) < n_samples and attempt < max_attempts:
        anchor = anchors[attempt % len(anchors)] if anchors else base_vector
        component_index = (attempt // max(1, len(anchors))) % len(component_pairs)
        direction = directions[(attempt // max(1, len(anchors) * len(component_pairs))) % len(directions)]
        magnitude = magnitudes[(attempt // max(1, len(anchors) * len(component_pairs) * len(directions))) % len(magnitudes)]
        proposal = np.asarray(anchor, dtype=np.float64).copy()
        x_index, y_index = component_pairs[component_index]
        proposal[x_index] += float(direction[0] * magnitude)
        proposal[y_index] += float(direction[1] * magnitude)
        proposal = np.clip(proposal, xl, xu)
        proposal = _restore_sink_from_anchor(problem, proposal, anchor)
        key = tuple(round(float(value), 12) for value in proposal.tolist())
        if key not in seen and _is_cheap_feasible(problem, proposal):
            seen.add(key)
            candidates.append(proposal)
        attempt += 1


def _add_shape_preserving_anchor_refill(
    problem: Any,
    base_vector: np.ndarray,
    candidates: list[np.ndarray],
    seen: set[tuple[float, ...]],
    n_samples: int,
) -> None:
    xl = np.asarray(problem.xl, dtype=np.float64)
    xu = np.asarray(problem.xu, dtype=np.float64)
    anchors = _sink_anchor_vectors(problem, base_vector)
    anchor_index = 0
    while len(candidates) < n_samples:
        anchor = anchors[anchor_index % len(anchors)] if anchors else base_vector
        proposal = np.clip(np.asarray(anchor, dtype=np.float64), xl, xu)
        key = tuple(round(float(value), 12) for value in proposal.tolist())
        if key in seen:
            offset = np.zeros_like(proposal)
            adjustable = [index for index in range(proposal.size) if float(xu[index] - xl[index]) > 0.0]
            if adjustable:
                variable_index = adjustable[(anchor_index // max(1, len(anchors))) % len(adjustable)]
                direction = 1.0 if (anchor_index // max(1, len(anchors) * len(adjustable))) % 2 == 0 else -1.0
                offset[variable_index] = direction * min(1.0e-9, 0.5 * float(xu[variable_index] - xl[variable_index]))
                proposal = np.clip(proposal + offset, xl, xu)
                proposal = _restore_sink_from_anchor(problem, proposal, anchor)
                key = tuple(round(float(value), 12) for value in proposal.tolist())
        if key not in seen:
            seen.add(key)
            candidates.append(proposal)
        else:
            candidates.append(proposal.copy())
        anchor_index += 1


def _restore_sink_from_anchor(problem: Any, vector: np.ndarray, anchor_vector: np.ndarray) -> np.ndarray:
    sink_indices = _sink_indices(problem.optimization_spec)
    if sink_indices is None:
        return vector
    restored = np.asarray(vector, dtype=np.float64).copy()
    start_index, end_index = sink_indices
    restored[start_index] = float(anchor_vector[start_index])
    restored[end_index] = float(anchor_vector[end_index])
    return restored


def _sink_anchor_vectors(problem: Any, base_vector: np.ndarray) -> list[np.ndarray]:
    sink_indices = _sink_indices(problem.optimization_spec)
    if sink_indices is None:
        return [np.asarray(base_vector, dtype=np.float64).copy()]
    start_index, end_index = sink_indices
    xl = np.asarray(problem.xl, dtype=np.float64)
    xu = np.asarray(problem.xu, dtype=np.float64)
    span_limit = resolve_radiator_span_max(problem.evaluation_spec)
    current_span = max(0.0, float(base_vector[end_index] - base_vector[start_index]))
    span = current_span if span_limit is None else min(current_span, float(span_limit))
    span = max(0.0, min(span, float(xu[end_index] - xl[start_index])))
    if span <= 0.0:
        return [np.asarray(base_vector, dtype=np.float64).copy()]
    center_min = max(float(xl[start_index] + 0.5 * span), float(xl[end_index] - 0.5 * span))
    center_max = min(float(xu[start_index] + 0.5 * span), float(xu[end_index] - 0.5 * span))
    centers = [0.50, 0.645, 0.737]
    anchors: list[np.ndarray] = []
    for center in centers:
        clipped_center = min(max(float(center), center_min), center_max)
        vector = np.asarray(base_vector, dtype=np.float64).copy()
        vector[start_index] = float(clipped_center - 0.5 * span)
        vector[end_index] = float(clipped_center + 0.5 * span)
        anchors.append(vector)
    return anchors


def _component_xy_indices(optimization_spec: Any) -> list[tuple[int, int]]:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    by_component: dict[int, dict[str, int]] = {}
    for index, variable in enumerate(spec_payload.get("design_variables", [])):
        path = str(variable.get("path", ""))
        if not path.startswith("components[") or ".pose." not in path:
            continue
        component_index = int(path.split("[", 1)[1].split("]", 1)[0])
        axis = path.rsplit(".", 1)[1]
        if axis in {"x", "y"}:
            by_component.setdefault(component_index, {})[axis] = index
    return [
        (axes["x"], axes["y"])
        for _, axes in sorted(by_component.items())
        if "x" in axes and "y" in axes
    ]

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
