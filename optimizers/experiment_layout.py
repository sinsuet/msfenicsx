"""Helpers for template-first single-mode experiment containers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from optimizers.algorithm_config import resolve_algorithm_profile_path
from optimizers.io import resolve_benchmark_template_path, resolve_evaluation_spec_path


EXPERIMENT_DIRECTORIES = {
    "spec_snapshot": "spec_snapshot",
    "runs": "runs",
    "summaries": "summaries",
    "figures": "figures",
    "dashboards": "dashboards",
    "logs": "logs",
    "representatives": "representatives",
}


def allocate_experiment_root(
    *,
    scenario_runs_root: str | Path,
    scenario_template_id: str,
    mode_id: str,
    started_at: datetime | None = None,
) -> Path:
    root = Path(scenario_runs_root)
    effective_started_at = datetime.now() if started_at is None else started_at
    stem = f"{mode_id}__{effective_started_at:%m%d_%H%M}"
    experiment_root = root / scenario_template_id / "experiments" / stem
    if not experiment_root.exists():
        return experiment_root
    suffix = 1
    while True:
        candidate = experiment_root.with_name(f"{stem}__{suffix:02d}")
        if not candidate.exists():
            return candidate
        suffix += 1


def initialize_experiment_directories(experiment_root: str | Path) -> None:
    root = Path(experiment_root)
    root.mkdir(parents=True, exist_ok=True)
    for directory_name in EXPERIMENT_DIRECTORIES.values():
        (root / directory_name).mkdir(parents=True, exist_ok=True)


def build_experiment_manifest(
    *,
    scenario_template_id: str,
    mode_id: str,
    benchmark_seeds: list[int],
    optimization_spec_path: str | Path,
    started_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "scenario_template_id": str(scenario_template_id),
        "mode_id": str(mode_id),
        "benchmark_seeds": [int(seed) for seed in benchmark_seeds],
        "optimization_spec_path": str(optimization_spec_path),
        "created_at": (datetime.now() if started_at is None else started_at).isoformat(),
        "directories": dict(EXPERIMENT_DIRECTORIES),
    }


def resolve_experiment_mode_id(
    optimization_spec: Any,
    *,
    strict_nsga2: bool = False,
) -> str:
    payload = _coerce_payload(optimization_spec)
    algorithm = payload["algorithm"]
    backbone = str(algorithm["backbone"])
    mode = str(algorithm["mode"])
    controller = None
    if isinstance(payload.get("operator_control"), dict):
        controller = str(payload["operator_control"].get("controller", "")).strip() or None

    if backbone == "nsga2":
        if mode == "raw":
            return "nsga2_raw"
        if controller == "random_uniform":
            return "nsga2_union"
        if controller == "llm":
            return "nsga2_llm"
    if strict_nsga2:
        raise ValueError(
            "Three-mode experiment containers are defined only for the paper-facing NSGA-II ladder "
            f"(received backbone={backbone!r}, mode={mode!r}, controller={controller!r})."
        )
    if mode == "raw":
        return f"{backbone}_raw"
    controller_suffix = "controller" if controller is None else controller
    return f"{backbone}_{mode}_{controller_suffix}"


def resolve_scenario_template_id(template_path: str | Path) -> str:
    payload = yaml.safe_load(Path(template_path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        template_meta = payload.get("template_meta")
        if isinstance(template_meta, dict) and template_meta.get("template_id"):
            return str(template_meta["template_id"])
    return Path(template_path).stem


def snapshot_experiment_inputs(
    *,
    experiment_root: str | Path,
    optimization_spec_path: str | Path,
    optimization_spec: Any,
) -> dict[str, str]:
    root = Path(experiment_root) / EXPERIMENT_DIRECTORIES["spec_snapshot"]
    root.mkdir(parents=True, exist_ok=True)
    spec_payload = _coerce_payload(optimization_spec)

    snapshot_paths: dict[str, str] = {}
    source_to_snapshot = {
        "optimization_spec": (Path(optimization_spec_path), root / "optimization_spec.yaml"),
        "scenario_template": (
            resolve_benchmark_template_path(optimization_spec_path, spec_payload),
            root / "scenario_template.yaml",
        ),
        "evaluation_spec": (
            resolve_evaluation_spec_path(optimization_spec_path, spec_payload),
            root / "evaluation_spec.yaml",
        ),
    }
    if spec_payload["algorithm"].get("profile_path"):
        source_to_snapshot["algorithm_profile"] = (
            resolve_algorithm_profile_path(
                optimization_spec_path,
                spec_payload["algorithm"]["profile_path"],
            ),
            root / "algorithm_profile.yaml",
        )

    for snapshot_id, (source_path, destination_path) in source_to_snapshot.items():
        destination_path.write_text(Path(source_path).read_text(encoding="utf-8"), encoding="utf-8")
        snapshot_paths[snapshot_id] = str(destination_path.relative_to(Path(experiment_root)).as_posix())
    return snapshot_paths


def save_experiment_manifest(path: str | Path, payload: dict[str, Any]) -> Path:
    manifest_path = Path(path)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _coerce_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return dict(value)
    raise TypeError(f"Unsupported optimization spec payload type: {type(value)!r}")
