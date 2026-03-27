"""Artifact writers for multicase Pareto optimizer runs."""

from __future__ import annotations

import json
from pathlib import Path

from core.schema.io import save_case, save_solution
from evaluation.io import save_multicase_report
from optimizers.drivers.raw_driver import OptimizationRun
from optimizers.io import save_optimization_result
from optimizers.problem import CandidateArtifacts


def write_optimization_artifacts(output_root: str | Path, run: OptimizationRun) -> Path:
    resolved_output_root = Path(output_root)
    _initialize_bundle_root(resolved_output_root, include_representatives=True)
    save_optimization_result(run.result, resolved_output_root / "optimization_result.json")
    save_optimization_result({"pareto_front": run.result.pareto_front}, resolved_output_root / "pareto_front.json")
    representatives_root = resolved_output_root / "representatives"
    for name, artifacts in run.representative_artifacts.items():
        _write_representative_bundle(representatives_root / name.replace("_", "-"), artifacts)
    manifest = {
        "run_id": run.result.run_meta["run_id"],
        "optimization_spec_id": run.result.run_meta["optimization_spec_id"],
        "evaluation_spec_id": run.result.run_meta["evaluation_spec_id"],
        "snapshots": {
            "optimization_result": "optimization_result.json",
            "pareto_front": "pareto_front.json",
        },
        "directories": _bundle_directories(include_representatives=True),
    }
    _write_manifest(resolved_output_root / "manifest.json", manifest)
    return resolved_output_root


def _write_representative_bundle(bundle_root: Path, artifacts: CandidateArtifacts) -> None:
    _initialize_bundle_root(bundle_root)
    cases_root = bundle_root / "cases"
    solutions_root = bundle_root / "solutions"
    case_snapshots: dict[str, str] = {}
    solution_snapshots: dict[str, str] = {}
    for operating_case_id, case in artifacts.cases.items():
        save_case(case, cases_root / f"{operating_case_id}.yaml")
        case_snapshots[operating_case_id] = f"cases/{operating_case_id}.yaml"
    for operating_case_id, solution in artifacts.solutions.items():
        save_solution(solution, solutions_root / f"{operating_case_id}.yaml")
        solution_snapshots[operating_case_id] = f"solutions/{operating_case_id}.yaml"
    if artifacts.evaluation is not None:
        save_multicase_report(artifacts.evaluation, bundle_root / "evaluation.yaml")
    manifest = {
        "case_snapshots": case_snapshots,
        "solution_snapshots": solution_snapshots,
        "evaluation_snapshot": "evaluation.yaml" if artifacts.evaluation is not None else None,
        "directories": _bundle_directories(),
    }
    _write_manifest(bundle_root / "manifest.json", manifest)


def _initialize_bundle_root(bundle_root: Path, *, include_representatives: bool = False) -> None:
    bundle_root.mkdir(parents=True, exist_ok=True)
    for directory_name in _bundle_directories(include_representatives=include_representatives).values():
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)
    (bundle_root / "cases").mkdir(parents=True, exist_ok=True)
    (bundle_root / "solutions").mkdir(parents=True, exist_ok=True)


def _bundle_directories(*, include_representatives: bool = False) -> dict[str, str]:
    directories = {
        "logs": "logs",
        "fields": "fields",
        "tensors": "tensors",
        "figures": "figures",
    }
    if include_representatives:
        directories["representatives"] = "representatives"
    return directories


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
