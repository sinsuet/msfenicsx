"""Validation helpers for optimizer-layer contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any

from optimizers.operator_pool.operators import approved_operator_pool


SUPPORTED_BACKBONES_BY_FAMILY = {
    "genetic": ("nsga2", "nsga3", "ctaea", "rvea"),
    "decomposition": ("moead",),
    "swarm": ("cmopso",),
}
SUPPORTED_MODES = {"raw", "union"}
SUPPORTED_CONTROLLERS = {"random_uniform", "llm"}
SUPPORTED_REGISTRY_PROFILES = {"primitive_clean", "primitive_plus_assisted"}
SUPPORTED_LLM_CAPABILITY_PROFILES = {"responses_native", "chat_compatible_json"}
SUPPORTED_LLM_PERFORMANCE_PROFILES = {"economy", "balanced", "high_reasoning"}
SUPPORTED_LLM_FALLBACK_CONTROLLERS = {"random_uniform"}
SUPPORTED_LEGALITY_POLICIES = {
    "minimal_canonicalization",
    "projection_plus_local_restore",
}


class OptimizationValidationError(ValueError):
    """Raised when an optimizer-layer payload is invalid."""


def list_supported_backbones() -> list[str]:
    return sorted(backbone for backbones in SUPPORTED_BACKBONES_BY_FAMILY.values() for backbone in backbones)


def validate_optimization_spec_payload(payload: Mapping[str, Any]) -> None:
    required_keys = ("schema_version", "spec_meta", "benchmark_source", "design_variables", "algorithm", "evaluation_protocol")
    _require_mapping(payload, "OptimizationSpec")
    _require_required_keys(payload, required_keys, "OptimizationSpec")
    spec_meta = _require_mapping(payload["spec_meta"], "spec_meta")
    _require_text(spec_meta.get("spec_id"), "spec_meta.spec_id")
    _validate_benchmark_source(payload["benchmark_source"])
    design_variables = _require_sequence(payload["design_variables"], "design_variables")
    if not design_variables:
        raise OptimizationValidationError("design_variables must contain at least one variable.")
    seen_variable_ids: set[str] = set()
    seen_paths: set[str] = set()
    for variable in design_variables:
        _validate_design_variable(variable, seen_variable_ids, seen_paths)
    algorithm = _validate_algorithm(payload["algorithm"])
    _validate_operator_control(
        payload.get("operator_control"),
        family=algorithm["family"],
        backbone=algorithm["backbone"],
        mode=algorithm["mode"],
    )
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


def validate_algorithm_profile_payload(payload: Mapping[str, Any]) -> None:
    required_keys = ("schema_version", "profile_meta", "family", "backbone", "mode", "parameters")
    _require_mapping(payload, "AlgorithmProfile")
    _require_required_keys(payload, required_keys, "AlgorithmProfile")
    profile_meta = _require_mapping(payload["profile_meta"], "profile_meta")
    _require_text(profile_meta.get("profile_id"), "profile_meta.profile_id")
    family = _require_text(payload["family"], "AlgorithmProfile.family")
    if family not in SUPPORTED_BACKBONES_BY_FAMILY:
        raise OptimizationValidationError(
            f"AlgorithmProfile.family '{family}' must be one of {sorted(SUPPORTED_BACKBONES_BY_FAMILY)}."
        )
    backbone = _require_text(payload["backbone"], "AlgorithmProfile.backbone")
    if backbone not in SUPPORTED_BACKBONES_BY_FAMILY[family]:
        raise OptimizationValidationError(
            f"AlgorithmProfile.backbone '{backbone}' is not approved for AlgorithmProfile.family '{family}'."
        )
    mode = _require_text(payload["mode"], "AlgorithmProfile.mode")
    if mode not in SUPPORTED_MODES:
        raise OptimizationValidationError(f"AlgorithmProfile.mode '{mode}' must be one of {sorted(SUPPORTED_MODES)}.")
    _require_mapping(payload["parameters"], "AlgorithmProfile.parameters")


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


def _validate_algorithm(algorithm: Any) -> dict[str, Any]:
    required_keys = ("family", "backbone", "mode", "population_size", "num_generations", "seed")
    _require_mapping(algorithm, "algorithm")
    _require_required_keys(algorithm, required_keys, "algorithm")
    if "name" in algorithm:
        raise OptimizationValidationError(
            "algorithm.name has been replaced by algorithm.family / algorithm.backbone / algorithm.mode."
        )
    family = _require_text(algorithm["family"], "algorithm.family")
    if family not in SUPPORTED_BACKBONES_BY_FAMILY:
        raise OptimizationValidationError(
            f"algorithm.family '{family}' must be one of {sorted(SUPPORTED_BACKBONES_BY_FAMILY)}."
        )
    backbone = _require_text(algorithm["backbone"], "algorithm.backbone")
    if backbone not in SUPPORTED_BACKBONES_BY_FAMILY[family]:
        raise OptimizationValidationError(
            f"algorithm.backbone '{backbone}' is not approved for algorithm.family '{family}'."
        )
    mode = _require_text(algorithm["mode"], "algorithm.mode")
    if mode not in SUPPORTED_MODES:
        raise OptimizationValidationError(f"algorithm.mode '{mode}' must be one of {sorted(SUPPORTED_MODES)}.")
    if _require_integer(algorithm["population_size"], "algorithm.population_size") <= 0:
        raise OptimizationValidationError("algorithm.population_size must be positive.")
    if _require_integer(algorithm["num_generations"], "algorithm.num_generations") <= 0:
        raise OptimizationValidationError("algorithm.num_generations must be positive.")
    _require_integer(algorithm["seed"], "algorithm.seed")
    if "profile_path" in algorithm:
        _require_text(algorithm["profile_path"], "algorithm.profile_path")
    if "parameters" in algorithm:
        _require_mapping(algorithm["parameters"], "algorithm.parameters")
    if "operator_mode" in algorithm:
        raise OptimizationValidationError("algorithm.operator_mode has been replaced by algorithm.mode.")
    if "operator_pool" in algorithm:
        raise OptimizationValidationError("algorithm.operator_pool has moved to the top-level operator_control block.")
    return {"family": family, "backbone": backbone, "mode": mode}


def _validate_operator_control(operator_control: Any, *, family: str, backbone: str, mode: str) -> None:
    if mode == "raw":
        if operator_control is not None:
            raise OptimizationValidationError("operator_control is allowed only when algorithm.mode is 'union'.")
        return

    if mode != "union":
        raise OptimizationValidationError(f"Unsupported operator-control mode '{mode}'.")
    if operator_control is None:
        raise OptimizationValidationError("operator_control is required when algorithm.mode is 'union'.")

    required_keys = ("controller", "registry_profile", "operator_pool")
    _require_mapping(operator_control, "operator_control")
    _require_required_keys(operator_control, required_keys, "operator_control")
    controller = _require_text(operator_control["controller"], "operator_control.controller")
    if controller not in SUPPORTED_CONTROLLERS:
        raise OptimizationValidationError(
            f"operator_control.controller '{controller}' must be one of {sorted(SUPPORTED_CONTROLLERS)}."
        )

    registry_profile = _require_text(operator_control["registry_profile"], "operator_control.registry_profile")
    if registry_profile not in SUPPORTED_REGISTRY_PROFILES:
        raise OptimizationValidationError(
            f"operator_control.registry_profile must be one of {sorted(SUPPORTED_REGISTRY_PROFILES)}."
        )

    operator_pool = tuple(
        _require_text(operator_id, f"operator_control.operator_pool[{index}]")
        for index, operator_id in enumerate(_require_sequence(operator_control["operator_pool"], "operator_control.operator_pool"))
    )
    try:
        expected_pool = approved_operator_pool(registry_profile)
    except KeyError as exc:
        raise OptimizationValidationError(
            f"operator_control.registry_profile {registry_profile!r} is not approved for family={family!r}, backbone={backbone!r}."
        ) from exc
    if operator_pool != expected_pool:
        raise OptimizationValidationError(
            "operator_control.operator_pool must exactly match the approved pool for "
            f"registry_profile={registry_profile!r}: {list(expected_pool)}."
        )
    if controller == "llm" and operator_control.get("controller_parameters") is not None:
        _validate_llm_controller_parameters(operator_control.get("controller_parameters"))


def _validate_llm_controller_parameters(controller_parameters: Any) -> None:
    required_keys = (
        "provider",
        "capability_profile",
        "performance_profile",
        "api_key_env_var",
        "max_output_tokens",
    )
    _require_mapping(controller_parameters, "operator_control.controller_parameters")
    _require_required_keys(controller_parameters, required_keys, "operator_control.controller_parameters")

    provider = _require_text(controller_parameters["provider"], "operator_control.controller_parameters.provider")
    capability_profile = _require_text(
        controller_parameters["capability_profile"],
        "operator_control.controller_parameters.capability_profile",
    )
    if capability_profile not in SUPPORTED_LLM_CAPABILITY_PROFILES:
        raise OptimizationValidationError(
            "operator_control.controller_parameters.capability_profile must be one of "
            f"{sorted(SUPPORTED_LLM_CAPABILITY_PROFILES)}."
        )

    performance_profile = _require_text(
        controller_parameters["performance_profile"],
        "operator_control.controller_parameters.performance_profile",
    )
    if performance_profile not in SUPPORTED_LLM_PERFORMANCE_PROFILES:
        raise OptimizationValidationError(
            "operator_control.controller_parameters.performance_profile must be one of "
            f"{sorted(SUPPORTED_LLM_PERFORMANCE_PROFILES)}."
        )

    if not any(key in controller_parameters for key in ("model", "model_env_var")):
        raise OptimizationValidationError(
            "operator_control.controller_parameters must include 'model' or 'model_env_var'."
        )
    if "model" in controller_parameters:
        _require_text(controller_parameters["model"], "operator_control.controller_parameters.model")
    if "model_env_var" in controller_parameters:
        _require_text(
            controller_parameters["model_env_var"],
            "operator_control.controller_parameters.model_env_var",
        )
    _require_text(controller_parameters["api_key_env_var"], "operator_control.controller_parameters.api_key_env_var")
    if _require_integer(
        controller_parameters["max_output_tokens"],
        "operator_control.controller_parameters.max_output_tokens",
    ) <= 0:
        raise OptimizationValidationError("operator_control.controller_parameters.max_output_tokens must be positive.")

    if provider != "openai" and not any(
        key in controller_parameters for key in ("base_url", "base_url_env_var")
    ):
        raise OptimizationValidationError(
            "operator_control.controller_parameters for non-openai providers must include "
            "base_url or base_url_env_var."
        )
    if "base_url" in controller_parameters:
        _require_text(controller_parameters["base_url"], "operator_control.controller_parameters.base_url")
    if "base_url_env_var" in controller_parameters:
        _require_text(
            controller_parameters["base_url_env_var"],
            "operator_control.controller_parameters.base_url_env_var",
        )
    if "temperature" in controller_parameters:
        _require_real(controller_parameters["temperature"], "operator_control.controller_parameters.temperature")
    if "reasoning" in controller_parameters:
        reasoning = _require_mapping(controller_parameters["reasoning"], "operator_control.controller_parameters.reasoning")
        if "effort" in reasoning:
            _require_text(reasoning["effort"], "operator_control.controller_parameters.reasoning.effort")
    if "retry" in controller_parameters:
        retry = _require_mapping(controller_parameters["retry"], "operator_control.controller_parameters.retry")
        if "max_attempts" in retry and _require_integer(
            retry["max_attempts"],
            "operator_control.controller_parameters.retry.max_attempts",
        ) <= 0:
            raise OptimizationValidationError(
                "operator_control.controller_parameters.retry.max_attempts must be positive."
            )
        if "timeout_seconds" in retry:
            _require_real(
                retry["timeout_seconds"],
                "operator_control.controller_parameters.retry.timeout_seconds",
            )
    if "memory" in controller_parameters:
        memory = _require_mapping(controller_parameters["memory"], "operator_control.controller_parameters.memory")
        if "recent_window" in memory and _require_integer(
            memory["recent_window"],
            "operator_control.controller_parameters.memory.recent_window",
        ) <= 0:
            raise OptimizationValidationError(
                "operator_control.controller_parameters.memory.recent_window must be positive."
            )
        if "reflection_interval" in memory and _require_integer(
            memory["reflection_interval"],
            "operator_control.controller_parameters.memory.reflection_interval",
        ) <= 0:
            raise OptimizationValidationError(
                "operator_control.controller_parameters.memory.reflection_interval must be positive."
            )
    if "fallback_controller" in controller_parameters:
        fallback_controller = _require_text(
            controller_parameters["fallback_controller"],
            "operator_control.controller_parameters.fallback_controller",
        )
        if fallback_controller not in SUPPORTED_LLM_FALLBACK_CONTROLLERS:
            raise OptimizationValidationError(
                "operator_control.controller_parameters.fallback_controller must be one of "
                f"{sorted(SUPPORTED_LLM_FALLBACK_CONTROLLERS)}."
            )


def _validate_evaluation_protocol(protocol: Any) -> None:
    _require_mapping(protocol, "evaluation_protocol")
    _require_text(protocol.get("evaluation_spec_path"), "evaluation_protocol.evaluation_spec_path")
    legality_policy_id = _require_text(
        protocol.get("legality_policy_id"),
        "evaluation_protocol.legality_policy_id",
    )
    if legality_policy_id not in SUPPORTED_LEGALITY_POLICIES:
        raise OptimizationValidationError(
            "evaluation_protocol.legality_policy_id must be one of "
            f"{sorted(SUPPORTED_LEGALITY_POLICIES)}."
        )


def _validate_benchmark_source(source: Any) -> None:
    required_keys = ("template_path", "seed")
    _require_mapping(source, "benchmark_source")
    _require_required_keys(source, required_keys, "benchmark_source")
    _require_text(source["template_path"], "benchmark_source.template_path")
    _require_integer(source["seed"], "benchmark_source.seed")


def _validate_candidate_record(record: Any, label: str) -> None:
    required_keys = (
        "evaluation_index",
        "source",
        "feasible",
        "proposal_decision_vector",
        "evaluated_decision_vector",
        "legality_policy_id",
        "vector_transform_codes",
        "solver_skipped",
        "cheap_constraint_issues",
        "objective_values",
        "constraint_values",
    )
    _require_mapping(record, label)
    _require_required_keys(record, required_keys, label)
    _require_real(record["evaluation_index"], f"{label}.evaluation_index")
    _require_text(record["source"], f"{label}.source")
    if not isinstance(record["feasible"], bool):
        raise OptimizationValidationError(f"{label}.feasible must be a boolean.")
    proposal_vector = _require_mapping(record["proposal_decision_vector"], f"{label}.proposal_decision_vector")
    evaluated_vector = _require_mapping(record["evaluated_decision_vector"], f"{label}.evaluated_decision_vector")
    _require_text(record["legality_policy_id"], f"{label}.legality_policy_id")
    transform_codes = _require_sequence(record["vector_transform_codes"], f"{label}.vector_transform_codes")
    for value in transform_codes:
        _require_text(value, f"{label}.vector_transform_codes[]")
    if not isinstance(record["solver_skipped"], bool):
        raise OptimizationValidationError(f"{label}.solver_skipped must be a boolean.")
    cheap_constraint_issues = _require_sequence(
        record["cheap_constraint_issues"],
        f"{label}.cheap_constraint_issues",
    )
    for value in cheap_constraint_issues:
        _require_text(value, f"{label}.cheap_constraint_issues[]")
    if "decision_vector" in record:
        decision_vector = _require_mapping(record["decision_vector"], f"{label}.decision_vector")
        if dict(decision_vector) != dict(evaluated_vector):
            raise OptimizationValidationError(
                f"{label}.decision_vector must match {label}.evaluated_decision_vector when present."
            )
    else:
        decision_vector = None
    objective_values = _require_mapping(record["objective_values"], f"{label}.objective_values")
    constraint_values = _require_mapping(record["constraint_values"], f"{label}.constraint_values")
    if "evaluation_report" in record:
        _require_mapping(record["evaluation_report"], f"{label}.evaluation_report")
    elif "case_reports" in record:
        case_reports = _require_mapping(record["case_reports"], f"{label}.case_reports")
        for name, report in case_reports.items():
            _require_text(name, f"{label}.case_reports key")
            _require_mapping(report, f"{label}.case_reports['{name}']")
    else:
        raise OptimizationValidationError(f"{label} must include evaluation_report or case_reports.")
    for name, value in proposal_vector.items():
        _require_text(name, f"{label}.proposal_decision_vector key")
        _require_real(value, f"{label}.proposal_decision_vector['{name}']")
    for name, value in evaluated_vector.items():
        _require_text(name, f"{label}.evaluated_decision_vector key")
        _require_real(value, f"{label}.evaluated_decision_vector['{name}']")
    if decision_vector is not None:
        for name, value in decision_vector.items():
            _require_text(name, f"{label}.decision_vector key")
            _require_real(value, f"{label}.decision_vector['{name}']")
    for name, value in objective_values.items():
        _require_text(name, f"{label}.objective_values key")
        _require_real(value, f"{label}.objective_values['{name}']")
    for name, value in constraint_values.items():
        _require_text(name, f"{label}.constraint_values key")
        _require_real(value, f"{label}.constraint_values['{name}']")


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


def _require_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Real) or int(value) != value:
        raise OptimizationValidationError(f"{label} must be an integer.")
    return int(value)
