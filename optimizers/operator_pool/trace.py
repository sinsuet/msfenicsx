"""Serialization-friendly trace rows for pool-controller and operator telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _coerce_float_tuple(values: Any) -> tuple[float, ...]:
    return tuple(float(value) for value in values)


def _coerce_nested_float_tuples(values: Any) -> tuple[tuple[float, ...], ...]:
    return tuple(_coerce_float_tuple(item) for item in values)


@dataclass(frozen=True, slots=True)
class ControllerTraceRow:
    generation_index: int
    evaluation_index: int
    family: str
    backbone: str
    controller_id: str
    candidate_operator_ids: tuple[str, ...]
    selected_operator_id: str
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
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parent_vectors", _coerce_nested_float_tuples(self.parent_vectors))
        object.__setattr__(self, "proposal_vector", _coerce_float_tuple(self.proposal_vector))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_index": self.generation_index,
            "evaluation_index": self.evaluation_index,
            "operator_id": self.operator_id,
            "parent_count": self.parent_count,
            "parent_vectors": [list(vector) for vector in self.parent_vectors],
            "proposal_vector": list(self.proposal_vector),
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
            metadata=dict(payload.get("metadata", {})),
        )

