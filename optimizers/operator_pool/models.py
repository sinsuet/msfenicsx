"""Shared model contracts for the algorithm-agnostic operator pool."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ParentBundle:
    vectors: tuple[np.ndarray, ...]

    def __post_init__(self) -> None:
        if not self.vectors:
            raise ValueError("ParentBundle must contain at least one numeric decision vector.")
        normalized: list[np.ndarray] = []
        vector_size: int | None = None
        for vector in self.vectors:
            values = np.asarray(vector, dtype=np.float64)
            if values.ndim != 1:
                raise ValueError("ParentBundle vectors must be one-dimensional numeric arrays.")
            if vector_size is None:
                vector_size = int(values.shape[0])
            elif values.shape[0] != vector_size:
                raise ValueError("ParentBundle vectors must all share the same length.")
            frozen_values = np.array(values, dtype=np.float64, copy=True)
            frozen_values.setflags(write=False)
            normalized.append(frozen_values)
        object.__setattr__(self, "vectors", tuple(normalized))

    @classmethod
    def from_vectors(cls, *vectors: np.ndarray | list[float] | tuple[float, ...]) -> ParentBundle:
        return cls(vectors=tuple(np.asarray(vector, dtype=np.float64) for vector in vectors))

    @property
    def num_parents(self) -> int:
        return len(self.vectors)

    @property
    def vector_size(self) -> int:
        return int(self.vectors[0].shape[0])

    @property
    def primary(self) -> np.ndarray:
        return self.vectors[0]

    @property
    def secondary(self) -> np.ndarray:
        return self.vectors[1] if len(self.vectors) >= 2 else self.vectors[0]

