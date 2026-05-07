"""Tests for optimizers/suite_parallel.py — parallel leaf execution."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from optimizers.io import save_optimization_spec
from optimizers.models import OptimizationSpec
from optimizers.operator_pool.operators import approved_operator_pool
from optimizers.suite_parallel import (
    LeafResult,
    SuiteLeaf,
    expand_leaves,
    write_run_index_header,
)


def _make_spec_dict(mode: str) -> dict:
    base = {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": f"s5-test-{mode}",
            "description": f"Test spec for {mode}.",
        },
        "benchmark_source": {
            "template_path": "scenarios/templates/s5_aggressive15.yaml",
            "seed": 11,
        },
        "design_variables": [
            {
                "variable_id": "c01_x",
                "path": "components[0].pose.x",
                "lower_bound": 0.1,
                "upper_bound": 0.9,
            },
            {
                "variable_id": "c01_y",
                "path": "components[0].pose.y",
                "lower_bound": 0.1,
                "upper_bound": 0.68,
            },
        ],
        "algorithm": {
            "family": "genetic",
            "backbone": "nsga2",
            "mode": "union" if mode != "raw" else "raw",
            "population_size": 4,
            "num_generations": 1,
            "seed": 7,
        },
        "evaluation_protocol": {
            "evaluation_spec_path": "scenarios/evaluation/s5_aggressive15_eval.yaml",
            "legality_policy_id": "projection_plus_local_restore",
        },
    }
    if mode != "raw":
        controller = "llm" if mode == "llm" else "random_uniform"
        base["operator_control"] = {
            "controller": controller,
            "registry_profile": "primitive_structured",
            "operator_pool": list(approved_operator_pool("primitive_structured")),
        }
    return base


def _write_spec(tmp_path: Path, mode: str) -> tuple[Path, OptimizationSpec]:
    payload = _make_spec_dict(mode)
    spec = OptimizationSpec.from_dict(payload)
    spec_path = tmp_path / f"{mode}_spec.yaml"
    save_optimization_spec(spec.to_dict(), spec_path)
    return spec_path, spec


def _make_spec_by_mode(tmp_path: Path, modes: tuple[str, ...] = ("raw", "union", "llm")) -> dict[str, tuple[Path, OptimizationSpec]]:
    result = {}
    for mode in modes:
        spec_path, spec = _write_spec(tmp_path, mode)
        result[mode] = (spec_path, spec)
    return result


class TestExpandLeaves:
    def test_three_modes_three_seeds(self, tmp_path: Path) -> None:
        spec_by_mode = _make_spec_by_mode(tmp_path)
        leaves = expand_leaves(spec_by_mode, ["raw", "union", "llm"], [11, 17, 23])
        assert len(leaves) == 9
        modes = {(leaf.mode, leaf.seed) for leaf in leaves}
        for mode in ("raw", "union", "llm"):
            for seed in (11, 17, 23):
                assert (mode, seed) in modes

    def test_single_seed(self, tmp_path: Path) -> None:
        spec_by_mode = _make_spec_by_mode(tmp_path)
        leaves = expand_leaves(spec_by_mode, ["raw", "union"], [11])
        assert len(leaves) == 2
        assert all(leaf.seed == 11 for leaf in leaves)

    def test_preserves_mode_order(self, tmp_path: Path) -> None:
        spec_by_mode = _make_spec_by_mode(tmp_path)
        leaves = expand_leaves(spec_by_mode, ["raw", "union", "llm"], [11, 17])
        modes = [leaf.mode for leaf in leaves]
        assert modes == ["raw", "raw", "union", "union", "llm", "llm"]

    def test_single_mode_five_seeds(self, tmp_path: Path) -> None:
        spec_by_mode = _make_spec_by_mode(tmp_path, modes=("raw",))
        leaves = expand_leaves(spec_by_mode, ["raw"], [11, 17, 23, 29, 31])
        assert len(leaves) == 5
        assert all(leaf.mode == "raw" for leaf in leaves)
        assert [leaf.seed for leaf in leaves] == [11, 17, 23, 29, 31]

    def test_seeded_spec_has_correct_seed(self, tmp_path: Path) -> None:
        spec_by_mode = _make_spec_by_mode(tmp_path, modes=("raw",))
        leaves = expand_leaves(spec_by_mode, ["raw"], [11, 17])
        for leaf in leaves:
            assert leaf.optimization_spec.benchmark_source["seed"] == leaf.seed


class TestRunIndexHeader:
    def test_header_fields(self, tmp_path: Path) -> None:
        index_path = tmp_path / "run_index.csv"
        write_run_index_header(index_path)
        assert index_path.exists()
        with index_path.open() as handle:
            reader = csv.reader(handle)
            header = next(reader)
        assert header == [
            "mode", "seed", "population_size", "num_generations",
            "status", "started_at", "finished_at", "wall_seconds",
            "output_root", "failure_reason",
        ]

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        index_path = tmp_path / "sub" / "dir" / "run_index.csv"
        write_run_index_header(index_path)
        assert index_path.exists()


class TestSuiteLeafDataclass:
    def test_immutable(self) -> None:
        leaf = SuiteLeaf(
            mode="raw",
            seed=11,
            spec_path=Path("/tmp/spec.yaml"),
            optimization_spec=OptimizationSpec.from_dict(_make_spec_dict("raw")),
            evaluation_spec_path=Path("/tmp/eval.yaml"),
        )
        with pytest.raises(AttributeError):
            leaf.mode = "union"  # type: ignore[misc]

    def test_leaf_result_defaults(self) -> None:
        result = LeafResult(
            mode="raw",
            seed=11,
            status="completed",
            started_at="2026-05-08T00:00:00",
            finished_at="2026-05-08T00:30:00",
            wall_seconds=1800.0,
            output_root="/tmp/run",
        )
        assert result.failure_reason is None
