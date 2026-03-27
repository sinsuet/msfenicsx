"""Artifact writers for multicase Pareto optimizer runs."""

from __future__ import annotations

from pathlib import Path

from core.schema.io import save_case, save_solution
from evaluation.io import save_multicase_report
from optimizers.io import save_optimization_result
from optimizers.pymoo_driver import CandidateArtifacts, OptimizationRun


def write_optimization_artifacts(output_root: str | Path, run: OptimizationRun) -> Path:
    resolved_output_root = Path(output_root)
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    save_optimization_result(run.result, resolved_output_root / "optimization_result.json")
    save_optimization_result({"pareto_front": run.result.pareto_front}, resolved_output_root / "pareto_front.json")
    representatives_root = resolved_output_root / "representatives"
    for name, artifacts in run.representative_artifacts.items():
        _write_representative_bundle(representatives_root / name.replace("_", "-"), artifacts)
    return resolved_output_root


def _write_representative_bundle(bundle_root: Path, artifacts: CandidateArtifacts) -> None:
    bundle_root.mkdir(parents=True, exist_ok=True)
    for operating_case_id, case in artifacts.cases.items():
        save_case(case, bundle_root / f"case_{operating_case_id}.yaml")
    for operating_case_id, solution in artifacts.solutions.items():
        save_solution(solution, bundle_root / f"solution_{operating_case_id}.yaml")
    if artifacts.evaluation is not None:
        save_multicase_report(artifacts.evaluation, bundle_root / "evaluation.yaml")
