# tests/optimizers/test_multi_seed_layout.py
"""Flat for N=1, seeds/seed-<n>/ for N>=2, aggregate/ only for N>=3."""

from __future__ import annotations

from pathlib import Path


def test_resolve_seed_run_root_flat_for_single_seed(tmp_path: Path) -> None:
    from optimizers.run_layout import resolve_seed_run_root

    run_root = tmp_path / "0416_2030__llm"
    path = resolve_seed_run_root(run_root, seed=11, total_seeds=1)
    assert path == run_root


def test_resolve_seed_run_root_wraps_for_multiple_seeds(tmp_path: Path) -> None:
    from optimizers.run_layout import resolve_seed_run_root

    run_root = tmp_path / "0416_2030__llm"
    path = resolve_seed_run_root(run_root, seed=11, total_seeds=3)
    assert path == run_root / "seeds" / "seed-11"


def test_should_write_aggregate_true_only_for_three_or_more(tmp_path: Path) -> None:
    from optimizers.run_layout import should_write_aggregate

    assert should_write_aggregate(total_seeds=1) is False
    assert should_write_aggregate(total_seeds=2) is False
    assert should_write_aggregate(total_seeds=3) is True
    assert should_write_aggregate(total_seeds=30) is True
