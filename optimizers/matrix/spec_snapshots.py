from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from optimizers.io import load_optimization_spec
from optimizers.matrix.models import MatrixLeaf


def write_leaf_spec_snapshot(leaf: MatrixLeaf, snapshot_root: str | Path) -> Path:
    payload = load_optimization_spec(leaf.base_spec_path).to_dict()
    snapshot_payload = _leaf_payload(leaf, payload)
    snapshot_dir = Path(snapshot_root) / leaf.block_id / "specs"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / _snapshot_filename(leaf)
    snapshot_path.write_text(yaml.safe_dump(snapshot_payload, sort_keys=False), encoding="utf-8")
    return snapshot_path


def _leaf_payload(leaf: MatrixLeaf, payload: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(payload)
    result["spec_meta"]["spec_id"] = _snapshot_spec_id(leaf)
    result["benchmark_source"]["seed"] = int(leaf.benchmark_seed)
    result["algorithm"]["family"] = leaf.algorithm_family
    result["algorithm"]["backbone"] = leaf.algorithm_backbone
    result["algorithm"]["mode"] = "union" if leaf.mode == "llm" else leaf.mode
    result["algorithm"]["seed"] = int(leaf.algorithm_seed)
    result["algorithm"]["population_size"] = int(leaf.population_size)
    result["algorithm"]["num_generations"] = int(leaf.num_generations)
    if leaf.mode == "llm":
        operator_control = result.setdefault("operator_control", {})
        controller_parameters = operator_control.setdefault("controller_parameters", {})
        controller_parameters["provider_profile"] = str(leaf.llm_profile)
    else:
        result.pop("operator_control", None)
    return result


def _snapshot_filename(leaf: MatrixLeaf) -> str:
    return f"{leaf.scenario_id}__{leaf.method_id}__r{leaf.replicate_seed}.yaml"


def _snapshot_spec_id(leaf: MatrixLeaf) -> str:
    return f"{leaf.scenario_id}_{leaf.method_id}_r{leaf.replicate_seed}"
