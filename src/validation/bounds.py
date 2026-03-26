from __future__ import annotations

from typing import Any


CONDUCTIVITY_MIN = 0.1
CONDUCTIVITY_MAX = 500.0
MESH_MIN = 2
MESH_MAX = 300
CONDUCTIVITY_RATIO_MIN = 0.5
CONDUCTIVITY_RATIO_MAX = 2.0
SIZE_RATIO_MIN = 0.5
SIZE_RATIO_MAX = 1.5
POSITION_FRACTION_LIMIT = 0.25


def check_conductivity_bounds(value: float) -> str | None:
    if CONDUCTIVITY_MIN <= value <= CONDUCTIVITY_MAX:
        return None
    return (
        f"conductivity must stay within [{CONDUCTIVITY_MIN}, {CONDUCTIVITY_MAX}], got {value:.6f}"
    )


def check_mesh_bounds(value: int, *, field_name: str) -> str | None:
    if MESH_MIN <= value <= MESH_MAX:
        return None
    return f"{field_name} must stay within [{MESH_MIN}, {MESH_MAX}], got {value}"


def check_positive_dimension(value: float, *, field_name: str) -> str | None:
    if value > 0.0:
        return None
    return f"{field_name} must be > 0, got {value:.6f}"


def check_step_limit(path: str, old_value: Any, new_value: Any, *, envelope_width: float, envelope_height: float) -> str | None:
    if not isinstance(old_value, (int, float)) or not isinstance(new_value, (int, float)):
        return None

    if path.endswith(".conductivity"):
        if old_value <= 0:
            return None
        ratio = float(new_value) / float(old_value)
        if CONDUCTIVITY_RATIO_MIN <= ratio <= CONDUCTIVITY_RATIO_MAX:
            return None
        return (
            f"{path} step ratio must stay within [{CONDUCTIVITY_RATIO_MIN}, {CONDUCTIVITY_RATIO_MAX}], got {ratio:.6f}"
        )

    if path.endswith(".width") or path.endswith(".height"):
        if old_value <= 0:
            return None
        ratio = float(new_value) / float(old_value)
        if SIZE_RATIO_MIN <= ratio <= SIZE_RATIO_MAX:
            return None
        return f"{path} step ratio must stay within [{SIZE_RATIO_MIN}, {SIZE_RATIO_MAX}], got {ratio:.6f}"

    if path.endswith(".x0"):
        limit = envelope_width * POSITION_FRACTION_LIMIT
        if abs(float(new_value) - float(old_value)) <= limit:
            return None
        return f"{path} step must stay within +/- {limit:.6f}, got {float(new_value) - float(old_value):.6f}"

    if path.endswith(".y0"):
        limit = envelope_height * POSITION_FRACTION_LIMIT
        if abs(float(new_value) - float(old_value)) <= limit:
            return None
        return f"{path} step must stay within +/- {limit:.6f}, got {float(new_value) - float(old_value):.6f}"

    return None
