"""Evaluation layer for derived objectives and constraint reporting."""

from evaluation.engine import MetricResolutionError, evaluate_case_solution
from evaluation.models import EvaluationReport, EvaluationSpec, MultiCaseEvaluationReport, MultiCaseEvaluationSpec
from evaluation.multicase_engine import evaluate_operating_cases

__all__ = [
    "EvaluationReport",
    "EvaluationSpec",
    "MultiCaseEvaluationReport",
    "MultiCaseEvaluationSpec",
    "MetricResolutionError",
    "evaluate_case_solution",
    "evaluate_operating_cases",
]
