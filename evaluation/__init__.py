"""Evaluation layer for derived objectives and constraint reporting."""

from evaluation.engine import MetricResolutionError, evaluate_case_solution
from evaluation.models import EvaluationReport, EvaluationSpec

__all__ = [
    "EvaluationReport",
    "EvaluationSpec",
    "MetricResolutionError",
    "evaluate_case_solution",
]
