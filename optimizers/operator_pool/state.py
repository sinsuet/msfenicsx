"""Controller-facing state summaries for shared operator-pool proposals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from optimizers.operator_pool.models import ParentBundle


@dataclass(frozen=True, slots=True)
class ControllerState:
    family: str
    backbone: str
    generation_index: int
    evaluation_index: int
    parent_count: int
    vector_size: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.generation_index < 0:
            raise ValueError("ControllerState.generation_index must be non-negative.")
        if self.evaluation_index < 0:
            raise ValueError("ControllerState.evaluation_index must be non-negative.")
        if self.parent_count <= 0:
            raise ValueError("ControllerState.parent_count must be positive.")
        if self.vector_size <= 0:
            raise ValueError("ControllerState.vector_size must be positive.")
        object.__setattr__(self, "metadata", dict(self.metadata))

    @classmethod
    def from_parent_bundle(
        cls,
        parents: ParentBundle,
        *,
        family: str,
        backbone: str,
        generation_index: int,
        evaluation_index: int,
        metadata: dict[str, Any] | None = None,
    ) -> ControllerState:
        return cls(
            family=family,
            backbone=backbone,
            generation_index=generation_index,
            evaluation_index=evaluation_index,
            parent_count=parents.num_parents,
            vector_size=parents.vector_size,
            metadata={} if metadata is None else dict(metadata),
        )

