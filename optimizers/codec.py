"""Decision-vector encoding and decoding for thermal-case variables."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from numbers import Real
from typing import Any

import numpy as np

from core.schema.models import ThermalCase


PATH_TOKEN_PATTERN = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<index>\d+)\])?$")


class DecisionVectorError(ValueError):
    """Raised when a decision vector cannot be applied to a thermal case."""


def extract_decision_vector(case: Any, optimization_spec: Any) -> np.ndarray:
    case_payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    values = []
    for variable in spec_payload["design_variables"]:
        value = _get_path_value(case_payload, variable["path"])
        if not isinstance(value, Real):
            raise DecisionVectorError(f"Path '{variable['path']}' does not resolve to a numeric value.")
        values.append(float(value))
    return np.asarray(values, dtype=np.float64)


def apply_decision_vector(case: Any, optimization_spec: Any, vector: Sequence[float]) -> ThermalCase:
    case_payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    values = np.asarray(vector, dtype=np.float64)
    design_variables = spec_payload["design_variables"]
    if values.size != len(design_variables):
        raise DecisionVectorError(
            f"Decision vector length {values.size} does not match {len(design_variables)} design variables."
        )
    mutated_payload = deepcopy(case_payload)
    for variable, value in zip(design_variables, values.tolist(), strict=True):
        lower_bound = float(variable["lower_bound"])
        upper_bound = float(variable["upper_bound"])
        if not lower_bound <= float(value) <= upper_bound:
            raise DecisionVectorError(
                f"Decision value {value} for '{variable['variable_id']}' is outside [{lower_bound}, {upper_bound}]."
            )
        _set_path_value(mutated_payload, variable["path"], float(value))
    return ThermalCase.from_dict(mutated_payload)


def _get_path_value(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        name, index = _parse_segment(segment)
        if not isinstance(current, Mapping) or name not in current:
            raise DecisionVectorError(f"Path segment '{name}' is missing in '{path}'.")
        current = current[name]
        if index is not None:
            if not isinstance(current, Sequence) or isinstance(current, (str, bytes, bytearray)):
                raise DecisionVectorError(f"Path segment '{segment}' is not indexable in '{path}'.")
            try:
                current = current[index]
            except IndexError as exc:
                raise DecisionVectorError(f"Path segment '{segment}' is out of range in '{path}'.") from exc
    return current


def _set_path_value(payload: dict[str, Any], path: str, value: float) -> None:
    current: Any = payload
    segments = path.split(".")
    for segment in segments[:-1]:
        name, index = _parse_segment(segment)
        if name not in current:
            raise DecisionVectorError(f"Path segment '{name}' is missing in '{path}'.")
        current = current[name]
        if index is not None:
            if not isinstance(current, Sequence) or isinstance(current, (str, bytes, bytearray)):
                raise DecisionVectorError(f"Path segment '{segment}' is not indexable in '{path}'.")
            current = current[index]
    leaf_name, leaf_index = _parse_segment(segments[-1])
    if leaf_name not in current:
        raise DecisionVectorError(f"Leaf path segment '{leaf_name}' is missing in '{path}'.")
    if leaf_index is None:
        original_value = current[leaf_name]
        if not isinstance(original_value, Real):
            raise DecisionVectorError(f"Leaf path '{path}' does not resolve to a numeric value.")
        current[leaf_name] = float(value)
        return
    target = current[leaf_name]
    if not isinstance(target, list):
        raise DecisionVectorError(f"Leaf path segment '{segments[-1]}' is not mutable in '{path}'.")
    original_value = target[leaf_index]
    if not isinstance(original_value, Real):
        raise DecisionVectorError(f"Leaf path '{path}' does not resolve to a numeric value.")
    target[leaf_index] = float(value)


def _parse_segment(segment: str) -> tuple[str, int | None]:
    match = PATH_TOKEN_PATTERN.fullmatch(segment)
    if match is None:
        raise DecisionVectorError(f"Unsupported path segment syntax '{segment}'.")
    index = match.group("index")
    return match.group("name"), None if index is None else int(index)
