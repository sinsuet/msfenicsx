"""Canonical schema models, I/O helpers, and validation."""

from core.schema.io import load_case, load_solution, load_template, save_case, save_solution, save_template
from core.schema.models import ScenarioTemplate, ThermalCase, ThermalSolution
from core.schema.validation import (
    SchemaValidationError,
    validate_scenario_template_payload,
    validate_thermal_case_payload,
    validate_thermal_solution_payload,
)

__all__ = [
    "ScenarioTemplate",
    "ThermalCase",
    "ThermalSolution",
    "SchemaValidationError",
    "load_case",
    "load_solution",
    "load_template",
    "save_case",
    "save_solution",
    "save_template",
    "validate_scenario_template_payload",
    "validate_thermal_case_payload",
    "validate_thermal_solution_payload",
]
