"""Validation helpers for evaluation-layer payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any


SUPPORTED_OBJECTIVE_SENSES = {"minimize", "maximize"}
SUPPORTED_CONSTRAINT_RELATIONS = {"<=", ">="}


class EvaluationValidationError(ValueError):
    """Raised when an evaluation-layer payload is invalid."""


def validate_spec_payload(payload: Mapping[str, Any]) -> None:
    required_keys = ("schema_version", "spec_meta", "objectives", "constraints")
    _require_mapping(payload, "EvaluationSpec")
    _require_required_keys(payload, required_keys, "EvaluationSpec")
    spec_meta = _require_mapping(payload["spec_meta"], "spec_meta")
    _require_text(spec_meta.get("spec_id"), "spec_meta.spec_id")
    objectives = _require_sequence(payload["objectives"], "objectives")
    constraints = _require_sequence(payload["constraints"], "constraints")
    for objective in objectives:
        _validate_objective(objective)
    for constraint in constraints:
        _validate_constraint(constraint)


def validate_report_payload(payload: Mapping[str, Any]) -> None:
    required_keys = (
        "schema_version",
        "evaluation_meta",
        "feasible",
        "metric_values",
        "objective_summary",
        "constraint_reports",
        "violations",
        "derived_signals",
        "provenance",
    )
    _require_mapping(payload, "EvaluationReport")
    _require_required_keys(payload, required_keys, "EvaluationReport")
    evaluation_meta = _require_mapping(payload["evaluation_meta"], "evaluation_meta")
    for key in ("report_id", "case_id", "solution_id", "spec_id"):
        _require_text(evaluation_meta.get(key), f"evaluation_meta.{key}")
    if not isinstance(payload["feasible"], bool):
        raise EvaluationValidationError("feasible must be a boolean.")
    metric_values = _require_mapping(payload["metric_values"], "metric_values")
    for metric_key, metric_value in metric_values.items():
        _require_text(metric_key, "metric_values key")
        _require_real(metric_value, f"metric_values['{metric_key}']")
    for objective in _require_sequence(payload["objective_summary"], "objective_summary"):
        _validate_objective_summary(objective)
    for constraint in _require_sequence(payload["constraint_reports"], "constraint_reports"):
        _validate_constraint_report(constraint)
    for violation in _require_sequence(payload["violations"], "violations"):
        if not isinstance(violation, Mapping):
            raise EvaluationValidationError("violations entries must be mappings.")
    _require_mapping(payload["derived_signals"], "derived_signals")
    _require_mapping(payload["provenance"], "provenance")


def _validate_objective(objective: Any) -> None:
    required_keys = ("objective_id", "metric", "sense")
    _require_mapping(objective, "objective")
    _require_required_keys(objective, required_keys, "objective")
    _require_text(objective["objective_id"], "objective.objective_id")
    _require_text(objective["metric"], "objective.metric")
    sense = _require_text(objective["sense"], "objective.sense")
    if sense not in SUPPORTED_OBJECTIVE_SENSES:
        raise EvaluationValidationError(
            f"objective sense '{sense}' must be one of {sorted(SUPPORTED_OBJECTIVE_SENSES)}."
        )


def _validate_constraint(constraint: Any) -> None:
    required_keys = ("constraint_id", "metric", "relation", "limit")
    _require_mapping(constraint, "constraint")
    _require_required_keys(constraint, required_keys, "constraint")
    _require_text(constraint["constraint_id"], "constraint.constraint_id")
    _require_text(constraint["metric"], "constraint.metric")
    relation = _require_text(constraint["relation"], "constraint.relation")
    if relation not in SUPPORTED_CONSTRAINT_RELATIONS:
        raise EvaluationValidationError(
            f"constraint relation '{relation}' must be one of {sorted(SUPPORTED_CONSTRAINT_RELATIONS)}."
        )
    _require_real(constraint["limit"], "constraint.limit")


def _validate_objective_summary(objective: Any) -> None:
    required_keys = ("objective_id", "metric", "sense", "value")
    _require_mapping(objective, "objective_summary entry")
    _require_required_keys(objective, required_keys, "objective_summary entry")
    _require_text(objective["objective_id"], "objective_summary.objective_id")
    _require_text(objective["metric"], "objective_summary.metric")
    _require_text(objective["sense"], "objective_summary.sense")
    _require_real(objective["value"], "objective_summary.value")


def _validate_constraint_report(constraint: Any) -> None:
    required_keys = ("constraint_id", "metric", "relation", "limit", "actual", "margin", "satisfied")
    _require_mapping(constraint, "constraint_report entry")
    _require_required_keys(constraint, required_keys, "constraint_report entry")
    _require_text(constraint["constraint_id"], "constraint_report.constraint_id")
    _require_text(constraint["metric"], "constraint_report.metric")
    _require_text(constraint["relation"], "constraint_report.relation")
    _require_real(constraint["limit"], "constraint_report.limit")
    _require_real(constraint["actual"], "constraint_report.actual")
    _require_real(constraint["margin"], "constraint_report.margin")
    if not isinstance(constraint["satisfied"], bool):
        raise EvaluationValidationError("constraint_report.satisfied must be a boolean.")


def _require_required_keys(payload: Mapping[str, Any], required_keys: Sequence[str], label: str) -> None:
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise EvaluationValidationError(f"{label} is missing required keys: {', '.join(missing)}.")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvaluationValidationError(f"{label} must be a mapping.")
    return value


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise EvaluationValidationError(f"{label} must be a sequence.")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationValidationError(f"{label} must be a non-empty string.")
    return value


def _require_real(value: Any, label: str) -> float:
    if not isinstance(value, Real):
        raise EvaluationValidationError(f"{label} must be a real number.")
    return float(value)
