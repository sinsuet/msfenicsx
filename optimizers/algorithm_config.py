"""Resolution helpers for optimizer backbone defaults, profiles, and inline parameters."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from optimizers.validation import OptimizationValidationError, validate_algorithm_profile_payload


DEFAULT_ALGORITHM_PARAMETERS = {
    ("genetic", "nsga2", "raw"): {
        "crossover": {"operator": "sbx", "eta": 15, "prob": 0.9},
        "mutation": {"operator": "pm", "eta": 20},
    },
    ("genetic", "nsga2", "union"): {
        "crossover": {"operator": "sbx", "eta": 15, "prob": 0.9},
        "mutation": {"operator": "pm", "eta": 20},
    },
    ("genetic", "spea2", "raw"): {
        "crossover": {"operator": "sbx", "eta": 15, "prob": 0.9},
        "mutation": {"operator": "pm", "eta": 20},
    },
    ("genetic", "nsga3", "raw"): {
        "reference_directions": {"scheme": "uniform"},
        "crossover": {"operator": "sbx", "eta": 15, "prob": 0.9},
        "mutation": {"operator": "pm", "eta": 20},
    },
    ("genetic", "nsga3", "union"): {
        "reference_directions": {"scheme": "uniform"},
        "crossover": {"operator": "sbx", "eta": 15, "prob": 0.9},
        "mutation": {"operator": "pm", "eta": 20},
    },
    ("genetic", "ctaea", "raw"): {
        "reference_directions": {"scheme": "energy"},
        "crossover": {"operator": "sbx", "eta": 30, "prob": 1.0, "n_offsprings": 1},
        "mutation": {"operator": "pm", "eta": 20},
    },
    ("genetic", "ctaea", "union"): {
        "reference_directions": {"scheme": "energy"},
        "crossover": {"operator": "sbx", "eta": 30, "prob": 1.0, "n_offsprings": 1},
        "mutation": {"operator": "pm", "eta": 20},
    },
    ("genetic", "rvea", "raw"): {
        "reference_directions": {"scheme": "energy"},
    },
    ("genetic", "rvea", "union"): {
        "reference_directions": {"scheme": "energy"},
    },
    ("decomposition", "moead", "raw"): {
        "reference_directions": {"scheme": "energy"},
        "neighbors": {"strategy": "half_population", "min_size": 2},
    },
    ("decomposition", "moead", "union"): {
        "reference_directions": {"scheme": "energy"},
        "neighbors": {"strategy": "half_population", "min_size": 2},
    },
    ("swarm", "cmopso", "raw"): {
        "elite_archive": {"strategy": "half_population", "min_size": 5},
    },
    ("swarm", "cmopso", "union"): {
        "elite_archive": {"strategy": "half_population", "min_size": 5},
    },
}


def load_algorithm_profile(path: str | Path) -> dict[str, Any]:
    resolved_path = Path(path)
    with resolved_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Algorithm profile {resolved_path} must deserialize to a mapping.")
    validate_algorithm_profile_payload(payload)
    return payload


def resolve_algorithm_profile_path(spec_path: str | Path | None, profile_path: str | Path) -> Path:
    candidate_path = Path(profile_path)
    if candidate_path.is_absolute():
        return candidate_path
    if candidate_path.exists():
        return candidate_path.resolve()
    if spec_path is not None:
        return (Path(spec_path).resolve().parent / candidate_path).resolve()
    return candidate_path


def resolve_algorithm_config(spec_path: str | Path | None, optimization_spec: Any) -> dict[str, Any]:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    algorithm = deepcopy(spec_payload["algorithm"])
    family = str(algorithm["family"])
    backbone = str(algorithm["backbone"])
    mode = str(algorithm["mode"])

    merged_parameters = deepcopy(DEFAULT_ALGORITHM_PARAMETERS.get((family, backbone, mode), {}))
    if "profile_path" in algorithm:
        profile_path = resolve_algorithm_profile_path(spec_path, algorithm["profile_path"])
        profile_payload = load_algorithm_profile(profile_path)
        if (
            profile_payload["family"] != family
            or profile_payload["backbone"] != backbone
            or profile_payload["mode"] != mode
        ):
            raise OptimizationValidationError(
                "algorithm.profile_path must reference a profile with matching family/backbone/mode."
            )
        merged_parameters = _deep_merge(merged_parameters, profile_payload["parameters"])
    if "parameters" in algorithm:
        merged_parameters = _deep_merge(merged_parameters, algorithm["parameters"])
    algorithm["parameters"] = merged_parameters
    return algorithm


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged
