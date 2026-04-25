"""Explicit legality-policy application for optimizer proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from core.schema.models import ThermalCase
from optimizers.codec import extract_decision_vector
from optimizers.repair import project_case_payload_from_vector, repair_case_payload_from_vector

LegalityPolicyId = Literal["minimal_canonicalization", "projection_plus_local_restore"]


@dataclass(frozen=True, slots=True)
class LegalityEvaluation:
    proposal_vector: np.ndarray
    evaluated_vector: np.ndarray
    case_payload: dict[str, Any]
    legality_policy_id: str
    vector_transform_codes: tuple[str, ...]


def apply_legality_policy_from_vector(
    base_case: Any,
    optimization_spec: Any,
    vector: np.ndarray,
    *,
    legality_policy_id: LegalityPolicyId,
    radiator_span_max: float | None = None,
) -> LegalityEvaluation:
    proposal_vector = np.asarray(vector, dtype=np.float64)
    if legality_policy_id == "minimal_canonicalization":
        payload = project_case_payload_from_vector(
            base_case,
            optimization_spec,
            proposal_vector,
            radiator_span_max=radiator_span_max,
        )
    elif legality_policy_id == "projection_plus_local_restore":
        payload = repair_case_payload_from_vector(
            base_case,
            optimization_spec,
            proposal_vector,
            radiator_span_max=radiator_span_max,
        )
    else:  # pragma: no cover - validation guards this
        raise ValueError(f"Unsupported legality policy id: {legality_policy_id!r}")

    evaluated_case = ThermalCase.from_dict(payload)
    evaluated_vector = extract_decision_vector(evaluated_case, optimization_spec)
    return LegalityEvaluation(
        proposal_vector=np.asarray(proposal_vector, dtype=np.float64),
        evaluated_vector=np.asarray(evaluated_vector, dtype=np.float64),
        case_payload=payload,
        legality_policy_id=str(legality_policy_id),
        vector_transform_codes=_vector_transform_codes(
            proposal_vector=np.asarray(proposal_vector, dtype=np.float64),
            evaluated_vector=np.asarray(evaluated_vector, dtype=np.float64),
            optimization_spec=optimization_spec,
        ),
    )


def _vector_transform_codes(
    *,
    proposal_vector: np.ndarray,
    evaluated_vector: np.ndarray,
    optimization_spec: Any,
) -> tuple[str, ...]:
    codes: list[str] = []
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    clipped_vector = np.asarray(proposal_vector, dtype=np.float64).copy()
    component_indices: list[int] = []
    sink_indices: list[int] = []
    bound_clipped = False
    for index, variable in enumerate(spec_payload["design_variables"]):
        lower_bound = float(variable["lower_bound"])
        upper_bound = float(variable["upper_bound"])
        clipped_value = float(np.clip(proposal_vector[index], lower_bound, upper_bound))
        if not np.isclose(clipped_value, float(proposal_vector[index])):
            bound_clipped = True
        clipped_vector[index] = clipped_value
        path = str(variable["path"])
        if path.startswith("components[") and ".pose." in path:
            component_indices.append(index)
        elif path.startswith("boundary_features[") and path.rsplit(".", 1)[-1] in {"start", "end"}:
            sink_indices.append(index)
    if bound_clipped:
        codes.append("bound_clip")
    if proposal_vector[-2] > proposal_vector[-1]:
        codes.append("sink_reorder")
    if sink_indices and not np.allclose(proposal_vector[sink_indices], evaluated_vector[sink_indices]):
        codes.append("sink_project")
    if component_indices and not np.allclose(clipped_vector[component_indices], evaluated_vector[component_indices]):
        codes.append("local_restore")
    return tuple(dict.fromkeys(codes))
