"""Validation helpers for optimizer-layer contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any


SUPPORTED_ALGORITHMS = {"pymoo_nsga2"}


class OptimizationValidationError(ValueError):
    """Raised when an optimizer-layer payload is invalid."""


def validate_optimization_spec_payload(payload: Mapping[str, Any]) -> None:
    required_keys = ("schema_version", "spec_meta", "design_variables", "algorithm", "evaluation_protocol")
    _require_mapping(payload, "OptimizationSpec")
    _require_required_keys(payload, required_keys, "OptimizationSpec")
    spec_meta = _require_mapping(payload["spec_meta"], "spec_meta")
    _require_text(spec_meta.get("spec_id"), "spec_meta.spec_id")
    design_variables = _require_sequence(payload["design_variables"], "design_variables")
    if not design_variables:
        raise OptimizationValidationError("design_variables must contain at least one variable.")
    seen_variable_ids: set[str] = set()
    seen_paths: set[str] = set()
    for variable in design_variables:
        _validate_design_variable(variable, seen_variable_ids, seen_paths)
    _validate_algorithm(payload["algorithm"])
    _validate_evaluation_protocol(payload["evaluation_protocol"])


def validate_optimization_result_payload(payload: Mapping[str, Any]) -> None:
    required_keys = (
        "schema_version",
        "run_meta",
        "baseline_candidates",
        "pareto_front",
        "representative_candidates",
        "aggregate_metrics",
        "history",
        "provenance",
    )
    _require_mapping(payload, "OptimizationResult")
    _require_required_keys(payload, required_keys, "OptimizationResult")
    _require_mapping(payload["run_meta"], "run_meta")
    for entry in _require_sequence(payload["baseline_candidates"], "baseline_candidates"):
        _validate_candidate_record(entry, "baseline_candidates entry")
    for entry in _require_sequence(payload["pareto_front"], "pareto_front"):
        _validate_candidate_record(entry, "pareto_front entry")
    representative_candidates = _require_mapping(payload["representative_candidates"], "representative_candidates")
    for name, candidate in representative_candidates.items():
        _require_text(name, "representative_candidates key")
        _validate_candidate_record(candidate, f"representative_candidates['{name}']")
    _require_mapping(payload["aggregate_metrics"], "aggregate_metrics")
    for entry in _require_sequence(payload["history"], "history"):
        _validate_candidate_record(entry, "history entry")
    _require_mapping(payload["provenance"], "provenance")


def _validate_design_variable(
    variable: Any,
    seen_variable_ids: set[str],
    seen_paths: set[str],
) -> None:
    required_keys = ("variable_id", "path", "lower_bound", "upper_bound")
    _require_mapping(variable, "design_variable")
    _require_required_keys(variable, required_keys, "design_variable")
    variable_id = _require_text(variable["variable_id"], "design_variable.variable_id")
    path = _require_text(variable["path"], "design_variable.path")
    lower_bound = _require_real(variable["lower_bound"], "design_variable.lower_bound")
    upper_bound = _require_real(variable["upper_bound"], "design_variable.upper_bound")
    if lower_bound >= upper_bound:
        raise OptimizationValidationError(
            f"design_variable '{variable_id}' must satisfy lower_bound < upper_bound."
        )
    if variable_id in seen_variable_ids:
        raise OptimizationValidationError(f"Duplicate design variable id '{variable_id}'.")
    if path in seen_paths:
        raise OptimizationValidationError(f"Duplicate design variable path '{path}'.")
    seen_variable_ids.add(variable_id)
    seen_paths.add(path)


def _validate_algorithm(algorithm: Any) -> None:
    required_keys = ("name", "population_size", "num_generations", "seed")
    _require_mapping(algorithm, "algorithm")
    _require_required_keys(algorithm, required_keys, "algorithm")
    name = _require_text(algorithm["name"], "algorithm.name")
    if name not in SUPPORTED_ALGORITHMS:
        raise OptimizationValidationError(
            f"algorithm.name '{name}' must be one of {sorted(SUPPORTED_ALGORITHMS)}."
        )
    if int(_require_real(algorithm["population_size"], "algorithm.population_size")) <= 0:
        raise OptimizationValidationError("algorithm.population_size must be positive.")
    if int(_require_real(algorithm["num_generations"], "algorithm.num_generations")) <= 0:
        raise OptimizationValidationError("algorithm.num_generations must be positive.")
    int(_require_real(algorithm["seed"], "algorithm.seed"))


def _validate_evaluation_protocol(protocol: Any) -> None:
    _require_mapping(protocol, "evaluation_protocol")
    _require_text(protocol.get("evaluation_spec_path"), "evaluation_protocol.evaluation_spec_path")


def _validate_candidate_record(record: Any, label: str) -> None:
    required_keys = (
        "evaluation_index",
        "source",
        "feasible",
        "decision_vector",
        "objective_values",
        "constraint_values",
        "case_reports",
    )
    _require_mapping(record, label)
    _require_required_keys(record, required_keys, label)
    _require_real(record["evaluation_index"], f"{label}.evaluation_index")
    _require_text(record["source"], f"{label}.source")
    if not isinstance(record["feasible"], bool):
        raise OptimizationValidationError(f"{label}.feasible must be a boolean.")
    decision_vector = _require_mapping(record["decision_vector"], f"{label}.decision_vector")
    objective_values = _require_mapping(record["objective_values"], f"{label}.objective_values")
    constraint_values = _require_mapping(record["constraint_values"], f"{label}.constraint_values")
    case_reports = _require_mapping(record["case_reports"], f"{label}.case_reports")
    for name, value in decision_vector.items():
        _require_text(name, f"{label}.decision_vector key")
        _require_real(value, f"{label}.decision_vector['{name}']")
    for name, value in objective_values.items():
        _require_text(name, f"{label}.objective_values key")
        _require_real(value, f"{label}.objective_values['{name}']")
    for name, value in constraint_values.items():
        _require_text(name, f"{label}.constraint_values key")
        _require_real(value, f"{label}.constraint_values['{name}']")
    for name, report in case_reports.items():
        _require_text(name, f"{label}.case_reports key")
        _require_mapping(report, f"{label}.case_reports['{name}']")


def _require_required_keys(payload: Mapping[str, Any], required_keys: Sequence[str], label: str) -> None:
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise OptimizationValidationError(f"{label} is missing required keys: {', '.join(missing)}.")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OptimizationValidationError(f"{label} must be a mapping.")
    return value


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise OptimizationValidationError(f"{label} must be a sequence.")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OptimizationValidationError(f"{label} must be a non-empty string.")
    return value


def _require_real(value: Any, label: str) -> float:
    if not isinstance(value, Real):
        raise OptimizationValidationError(f"{label} must be a real number.")
    return float(value)
