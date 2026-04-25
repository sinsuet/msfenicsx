"""Serialization-friendly trace rows for pool-controller and operator telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _coerce_float_tuple(values: Any) -> tuple[float, ...]:
    return tuple(float(value) for value in values)


def _coerce_nested_float_tuples(values: Any) -> tuple[tuple[float, ...], ...]:
    return tuple(_coerce_float_tuple(item) for item in values)


@dataclass(slots=True)
class ControllerAttemptTraceRow:
    generation_index: int
    provisional_evaluation_index: int
    decision_index: int
    attempt_index: int
    family: str
    backbone: str
    controller_id: str
    candidate_operator_ids: tuple[str, ...]
    selected_operator_id: str
    phase: str = ""
    rationale: str = ""
    accepted_for_evaluation: bool = False
    accepted_evaluation_indices: list[int] = field(default_factory=list)
    rejection_reason: str = ""
    duplicate_with_population: bool = False
    duplicate_within_batch: bool = False
    repair_collapsed_duplicate: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.candidate_operator_ids = tuple(str(value) for value in self.candidate_operator_ids)
        self.accepted_evaluation_indices = [int(value) for value in self.accepted_evaluation_indices]
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_index": self.generation_index,
            "provisional_evaluation_index": self.provisional_evaluation_index,
            "decision_index": self.decision_index,
            "attempt_index": self.attempt_index,
            "family": self.family,
            "backbone": self.backbone,
            "controller_id": self.controller_id,
            "candidate_operator_ids": list(self.candidate_operator_ids),
            "selected_operator_id": self.selected_operator_id,
            "phase": self.phase,
            "rationale": self.rationale,
            "accepted_for_evaluation": self.accepted_for_evaluation,
            "accepted_evaluation_indices": list(self.accepted_evaluation_indices),
            "accepted_evaluation_index": (
                None if not self.accepted_evaluation_indices else int(self.accepted_evaluation_indices[0])
            ),
            "rejection_reason": self.rejection_reason,
            "duplicate_with_population": self.duplicate_with_population,
            "duplicate_within_batch": self.duplicate_within_batch,
            "repair_collapsed_duplicate": self.repair_collapsed_duplicate,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ControllerAttemptTraceRow:
        accepted_indices = payload.get("accepted_evaluation_indices")
        if not isinstance(accepted_indices, list):
            accepted_index = payload.get("accepted_evaluation_index")
            accepted_indices = [] if accepted_index is None else [int(accepted_index)]
        return cls(
            generation_index=int(payload["generation_index"]),
            provisional_evaluation_index=int(payload["provisional_evaluation_index"]),
            decision_index=int(payload["decision_index"]),
            attempt_index=int(payload["attempt_index"]),
            family=str(payload["family"]),
            backbone=str(payload["backbone"]),
            controller_id=str(payload["controller_id"]),
            candidate_operator_ids=tuple(str(value) for value in payload["candidate_operator_ids"]),
            selected_operator_id=str(payload["selected_operator_id"]),
            phase=str(payload.get("phase", "")),
            rationale=str(payload.get("rationale", "")),
            accepted_for_evaluation=bool(payload.get("accepted_for_evaluation", False)),
            accepted_evaluation_indices=[int(value) for value in accepted_indices],
            rejection_reason=str(payload.get("rejection_reason", "")),
            duplicate_with_population=bool(payload.get("duplicate_with_population", False)),
            duplicate_within_batch=bool(payload.get("duplicate_within_batch", False)),
            repair_collapsed_duplicate=bool(payload.get("repair_collapsed_duplicate", False)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class OperatorAttemptTraceRow:
    generation_index: int
    provisional_evaluation_index: int
    decision_index: int
    attempt_index: int
    operator_id: str
    parent_count: int
    parent_vectors: tuple[tuple[float, ...], ...]
    proposal_vector: tuple[float, ...]
    repaired_vector: tuple[float, ...]
    accepted_for_evaluation: bool = False
    accepted_evaluation_indices: list[int] = field(default_factory=list)
    rejection_reason: str = ""
    duplicate_with_population: bool = False
    duplicate_within_batch: bool = False
    repair_collapsed_duplicate: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.parent_vectors = _coerce_nested_float_tuples(self.parent_vectors)
        self.proposal_vector = _coerce_float_tuple(self.proposal_vector)
        self.repaired_vector = _coerce_float_tuple(self.repaired_vector)
        self.accepted_evaluation_indices = [int(value) for value in self.accepted_evaluation_indices]
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_index": self.generation_index,
            "provisional_evaluation_index": self.provisional_evaluation_index,
            "decision_index": self.decision_index,
            "attempt_index": self.attempt_index,
            "operator_id": self.operator_id,
            "parent_count": self.parent_count,
            "parent_vectors": [list(vector) for vector in self.parent_vectors],
            "proposal_vector": list(self.proposal_vector),
            "repaired_vector": list(self.repaired_vector),
            "accepted_for_evaluation": self.accepted_for_evaluation,
            "accepted_evaluation_indices": list(self.accepted_evaluation_indices),
            "accepted_evaluation_index": (
                None if not self.accepted_evaluation_indices else int(self.accepted_evaluation_indices[0])
            ),
            "rejection_reason": self.rejection_reason,
            "duplicate_with_population": self.duplicate_with_population,
            "duplicate_within_batch": self.duplicate_within_batch,
            "repair_collapsed_duplicate": self.repair_collapsed_duplicate,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> OperatorAttemptTraceRow:
        accepted_indices = payload.get("accepted_evaluation_indices")
        if not isinstance(accepted_indices, list):
            accepted_index = payload.get("accepted_evaluation_index")
            accepted_indices = [] if accepted_index is None else [int(accepted_index)]
        return cls(
            generation_index=int(payload["generation_index"]),
            provisional_evaluation_index=int(payload["provisional_evaluation_index"]),
            decision_index=int(payload["decision_index"]),
            attempt_index=int(payload["attempt_index"]),
            operator_id=str(payload["operator_id"]),
            parent_count=int(payload["parent_count"]),
            parent_vectors=_coerce_nested_float_tuples(payload["parent_vectors"]),
            proposal_vector=_coerce_float_tuple(payload["proposal_vector"]),
            repaired_vector=_coerce_float_tuple(payload.get("repaired_vector", payload["proposal_vector"])),
            accepted_for_evaluation=bool(payload.get("accepted_for_evaluation", False)),
            accepted_evaluation_indices=[int(value) for value in accepted_indices],
            rejection_reason=str(payload.get("rejection_reason", "")),
            duplicate_with_population=bool(payload.get("duplicate_with_population", False)),
            duplicate_within_batch=bool(payload.get("duplicate_within_batch", False)),
            repair_collapsed_duplicate=bool(payload.get("repair_collapsed_duplicate", False)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ControllerTraceRow:
    generation_index: int
    evaluation_index: int
    family: str
    backbone: str
    controller_id: str
    candidate_operator_ids: tuple[str, ...]
    selected_operator_id: str
    phase: str = ""
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_operator_ids", tuple(str(value) for value in self.candidate_operator_ids))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_index": self.generation_index,
            "evaluation_index": self.evaluation_index,
            "family": self.family,
            "backbone": self.backbone,
            "controller_id": self.controller_id,
            "candidate_operator_ids": list(self.candidate_operator_ids),
            "selected_operator_id": self.selected_operator_id,
            "phase": self.phase,
            "rationale": self.rationale,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ControllerTraceRow:
        return cls(
            generation_index=int(payload["generation_index"]),
            evaluation_index=int(payload["evaluation_index"]),
            family=str(payload["family"]),
            backbone=str(payload["backbone"]),
            controller_id=str(payload["controller_id"]),
            candidate_operator_ids=tuple(str(value) for value in payload["candidate_operator_ids"]),
            selected_operator_id=str(payload["selected_operator_id"]),
            phase=str(payload.get("phase", "")),
            rationale=str(payload.get("rationale", "")),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class OperatorTraceRow:
    generation_index: int
    evaluation_index: int
    operator_id: str
    parent_count: int
    parent_vectors: tuple[tuple[float, ...], ...]
    proposal_vector: tuple[float, ...]
    evaluated_vector: tuple[float, ...] = ()
    legality_policy_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parent_vectors", _coerce_nested_float_tuples(self.parent_vectors))
        object.__setattr__(self, "proposal_vector", _coerce_float_tuple(self.proposal_vector))
        object.__setattr__(self, "evaluated_vector", _coerce_float_tuple(self.evaluated_vector))
        object.__setattr__(self, "legality_policy_id", str(self.legality_policy_id))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_index": self.generation_index,
            "evaluation_index": self.evaluation_index,
            "operator_id": self.operator_id,
            "parent_count": self.parent_count,
            "parent_vectors": [list(vector) for vector in self.parent_vectors],
            "proposal_vector": list(self.proposal_vector),
            "evaluated_vector": list(self.evaluated_vector),
            "legality_policy_id": self.legality_policy_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> OperatorTraceRow:
        return cls(
            generation_index=int(payload["generation_index"]),
            evaluation_index=int(payload["evaluation_index"]),
            operator_id=str(payload["operator_id"]),
            parent_count=int(payload["parent_count"]),
            parent_vectors=_coerce_nested_float_tuples(payload["parent_vectors"]),
            proposal_vector=_coerce_float_tuple(payload["proposal_vector"]),
            evaluated_vector=_coerce_float_tuple(payload.get("evaluated_vector", ())),
            legality_policy_id=str(payload.get("legality_policy_id", "")),
            metadata=dict(payload.get("metadata", {})),
        )
