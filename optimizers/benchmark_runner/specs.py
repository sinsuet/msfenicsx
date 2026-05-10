"""Contracts and YAML loading for the unified benchmark runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


MODE_ORDER = ("raw", "union", "llm")
DEFAULT_REPLICATE_SEEDS = (11, 17, 23, 29, 31)


@dataclass(frozen=True)
class ResourcePolicy:
    max_concurrent_leaves: int = 4
    leaf_evaluation_workers: int = 32


@dataclass(frozen=True)
class ComparisonPolicy:
    by_seed: bool = True
    aggregate: bool = True


@dataclass(frozen=True)
class BenchmarkLeaf:
    scenario_id: str
    method_id: str
    method_slug: str
    mode: str
    optimization_spec: Path
    benchmark_seed: int
    algorithm_seed: int
    population_size: int
    num_generations: int
    evaluation_workers: int
    llm_profile: str | None = None


@dataclass(frozen=True)
class CampaignSpec:
    campaign_id: str
    scenario_id: str
    scenario_runs_root: Path
    leaves: tuple[BenchmarkLeaf, ...]
    resource_policy: ResourcePolicy = field(default_factory=ResourcePolicy)
    comparison_policy: ComparisonPolicy = field(default_factory=ComparisonPolicy)
    compare_with: tuple[Path, ...] = ()


def build_single_leaf_campaign(
    *,
    optimization_spec: Path,
    mode: str,
    llm_profile: str | None,
    benchmark_seed: int,
    algorithm_seed: int,
    population_size: int,
    num_generations: int,
    evaluation_workers: int,
    scenario_runs_root: Path,
    campaign_id: str | None,
    compare_with: list[Path] | tuple[Path, ...] = (),
) -> CampaignSpec:
    scenario_id = _scenario_id_from_spec_path(Path(optimization_spec))
    method_id = _method_id(mode=mode, llm_profile=llm_profile, explicit_method_id=None, optimization_spec=optimization_spec)
    method_slug = _method_slug(method_id)
    effective_campaign_id = campaign_id or f"{scenario_id}_{method_slug}_seed_{int(benchmark_seed)}"
    leaf = BenchmarkLeaf(
        scenario_id=scenario_id,
        method_id=method_id,
        method_slug=method_slug,
        mode=str(mode),
        optimization_spec=Path(optimization_spec),
        benchmark_seed=int(benchmark_seed),
        algorithm_seed=int(algorithm_seed),
        population_size=int(population_size),
        num_generations=int(num_generations),
        evaluation_workers=int(evaluation_workers),
        llm_profile=None if llm_profile is None else str(llm_profile),
    )
    return CampaignSpec(
        campaign_id=effective_campaign_id,
        scenario_id=scenario_id,
        scenario_runs_root=Path(scenario_runs_root),
        leaves=(leaf,),
        resource_policy=ResourcePolicy(max_concurrent_leaves=1, leaf_evaluation_workers=int(evaluation_workers)),
        compare_with=tuple(Path(path) for path in compare_with),
    )


def load_campaigns_from_batch_spec(path: str | Path) -> list[CampaignSpec]:
    batch_path = Path(path)
    payload = yaml.safe_load(batch_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Batch spec must be a mapping: {batch_path}")
    campaign_payloads = payload.get("campaigns")
    if campaign_payloads is None:
        campaign_payloads = [payload]
    if not isinstance(campaign_payloads, list) or not campaign_payloads:
        raise ValueError("Batch spec campaigns must be a non-empty list.")
    return [_campaign_from_payload(dict(item), base_path=batch_path) for item in campaign_payloads]


def _campaign_from_payload(payload: dict[str, Any], *, base_path: Path) -> CampaignSpec:
    campaign_id = str(payload["campaign_id"])
    scenario_id = str(payload["scenario_id"])
    scenario_runs_root = Path(payload.get("scenario_runs_root", "./scenario_runs"))
    replicate_seeds = [int(seed) for seed in payload.get("replicate_seeds", DEFAULT_REPLICATE_SEEDS)]
    seed_offset = int(payload.get("algorithm_seed_offset", 1000))
    population_size = int(payload["population_size"])
    num_generations = int(payload["num_generations"])
    resource_payload = dict(payload.get("resource_policy", {}))
    resource_policy = ResourcePolicy(
        max_concurrent_leaves=int(resource_payload.get("max_concurrent_leaves", 4)),
        leaf_evaluation_workers=int(resource_payload.get("leaf_evaluation_workers", 32)),
    )
    comparison_payload = dict(payload.get("comparison_policy", {}))
    comparison_policy = ComparisonPolicy(
        by_seed=bool(comparison_payload.get("by_seed", True)),
        aggregate=bool(comparison_payload.get("aggregate", True)),
    )
    leaves: list[BenchmarkLeaf] = []
    for method in payload.get("methods", []):
        method_payload = dict(method)
        mode = str(method_payload["mode"])
        optimization_spec = _resolve_spec_path(base_path, method_payload["optimization_spec"])
        llm_profile = method_payload.get("llm_profile")
        method_id = _method_id(
            mode=mode,
            llm_profile=None if llm_profile is None else str(llm_profile),
            explicit_method_id=method_payload.get("method_id"),
            optimization_spec=optimization_spec,
        )
        for seed in replicate_seeds:
            leaves.append(
                BenchmarkLeaf(
                    scenario_id=scenario_id,
                    method_id=method_id,
                    method_slug=_method_slug(method_id),
                    mode=mode,
                    optimization_spec=optimization_spec,
                    benchmark_seed=int(seed),
                    algorithm_seed=int(seed) + seed_offset,
                    population_size=population_size,
                    num_generations=num_generations,
                    evaluation_workers=resource_policy.leaf_evaluation_workers,
                    llm_profile=None if llm_profile is None else str(llm_profile),
                )
            )
    if not leaves:
        raise ValueError(f"Campaign {campaign_id} must define at least one leaf.")
    return CampaignSpec(
        campaign_id=campaign_id,
        scenario_id=scenario_id,
        scenario_runs_root=scenario_runs_root,
        leaves=tuple(leaves),
        resource_policy=resource_policy,
        comparison_policy=comparison_policy,
        compare_with=tuple(Path(path) for path in payload.get("compare_with", [])),
    )


def _resolve_spec_path(base_path: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute() or path.exists():
        return path
    candidate = base_path.resolve().parent / path
    return candidate if candidate.exists() else path


def _scenario_id_from_spec_path(path: Path) -> str:
    name = path.stem
    for suffix in ("_spea2_raw", "_moead_raw", "_llm_direct", "_llm_no_repair", "_raw", "_union", "_llm"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _method_id(
    *,
    mode: str,
    llm_profile: str | None,
    explicit_method_id: Any,
    optimization_spec: Path,
) -> str:
    if explicit_method_id:
        return str(explicit_method_id)
    if mode == "llm":
        if Path(optimization_spec).stem.endswith("_llm_direct"):
            return f"llm_direct:{llm_profile or 'default'}"
        if Path(optimization_spec).stem.endswith("_llm_no_repair"):
            return f"llm_no_repair:{llm_profile or 'default'}"
        return f"llm:{llm_profile or 'default'}"
    stem = Path(optimization_spec).stem
    if stem.endswith("_spea2_raw"):
        return "spea2_raw"
    if stem.endswith("_moead_raw"):
        return "moead_raw"
    if mode == "raw":
        return "nsga2_raw"
    if mode == "union":
        return "nsga2_union"
    raise ValueError(f"Unsupported mode: {mode}")


def _method_slug(method_id: str) -> str:
    if method_id == "nsga2_raw":
        return "raw"
    if method_id == "nsga2_union":
        return "union"
    return method_id.replace(":", "-").replace("_", "-")
