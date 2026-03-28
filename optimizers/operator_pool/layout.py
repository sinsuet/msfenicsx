"""Variable-layout contracts for the shared operator-pool proposal layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class VariableSlot:
    index: int
    variable_id: str
    path: str
    lower_bound: float
    upper_bound: float


@dataclass(frozen=True, slots=True)
class VariableLayout:
    slots: tuple[VariableSlot, ...]

    def __post_init__(self) -> None:
        if not self.slots:
            raise ValueError("VariableLayout must contain at least one slot.")
        seen_variable_ids: set[str] = set()
        seen_indices: set[int] = set()
        for expected_index, slot in enumerate(self.slots):
            if slot.index != expected_index:
                raise ValueError("VariableLayout slot indices must be contiguous and zero-based.")
            if slot.variable_id in seen_variable_ids:
                raise ValueError(f"Duplicate VariableLayout variable_id '{slot.variable_id}'.")
            if slot.index in seen_indices:
                raise ValueError(f"Duplicate VariableLayout index '{slot.index}'.")
            seen_variable_ids.add(slot.variable_id)
            seen_indices.add(slot.index)

    @classmethod
    def from_optimization_spec(cls, optimization_spec: Any) -> VariableLayout:
        spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
        return cls(
            slots=tuple(
                VariableSlot(
                    index=index,
                    variable_id=str(variable["variable_id"]),
                    path=str(variable["path"]),
                    lower_bound=float(variable["lower_bound"]),
                    upper_bound=float(variable["upper_bound"]),
                )
                for index, variable in enumerate(spec_payload["design_variables"])
            )
        )

    @property
    def variable_ids(self) -> list[str]:
        return [slot.variable_id for slot in self.slots]

    @property
    def vector_size(self) -> int:
        return len(self.slots)

    @property
    def lower_bounds(self) -> np.ndarray:
        return np.asarray([slot.lower_bound for slot in self.slots], dtype=np.float64)

    @property
    def upper_bounds(self) -> np.ndarray:
        return np.asarray([slot.upper_bound for slot in self.slots], dtype=np.float64)

    def index_of(self, variable_id: str) -> int:
        for slot in self.slots:
            if slot.variable_id == variable_id:
                return slot.index
        raise KeyError(f"Unknown VariableLayout variable_id '{variable_id}'.")

    def slot_for(self, variable_id: str) -> VariableSlot:
        for slot in self.slots:
            if slot.variable_id == variable_id:
                return slot
        raise KeyError(f"Unknown VariableLayout variable_id '{variable_id}'.")

    def clip(self, vector: np.ndarray | list[float] | tuple[float, ...]) -> np.ndarray:
        values = np.asarray(vector, dtype=np.float64)
        if values.ndim != 1:
            raise ValueError("VariableLayout.clip expects a one-dimensional decision vector.")
        if values.shape[0] != self.vector_size:
            raise ValueError(
                f"VariableLayout.clip expected vector of length {self.vector_size}, got {values.shape[0]}."
            )
        return np.clip(values, self.lower_bounds, self.upper_bounds).astype(np.float64, copy=False)

