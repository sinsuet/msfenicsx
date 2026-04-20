from __future__ import annotations

import json
from pathlib import Path

import pytest

from optimizers.mode_summary import build_mode_summaries
from tests.optimizers.experiment_fixtures import create_mode_root, create_mode_root_with_seed_bundles


def test_build_mode_summaries_preserves_progress_metrics(tmp_path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))

    build_mode_summaries(mode_root)
    payload = json.loads((mode_root / "summaries" / "seed_summary.json").read_text(encoding="utf-8"))
    final_timeline = payload["rows"][0]["final_timeline"]

    assert payload["rows"][0]["label"] == "seed-11"
    assert final_timeline["evaluation_index"] == 4
    assert final_timeline["first_feasible_eval_so_far"] == 3
    assert final_timeline["best_temperature_max_so_far"] == 297.0
    assert final_timeline["best_gradient_rms_so_far"] == 8.8


def test_build_mode_summaries_supports_concrete_run_root(tmp_path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    concrete_root = mode_root / "seeds" / "seed-11"

    build_mode_summaries(concrete_root)
    payload = json.loads((concrete_root / "summaries" / "seed_summary.json").read_text(encoding="utf-8"))

    assert payload["rows"][0]["bundle_root"] == "."
    assert payload["rows"][0]["seed"] == 11
    assert (concrete_root / "summaries" / "mode_summary.json").exists()


def test_build_mode_summaries_rejects_nested_seed_bundle_layout(tmp_path: Path) -> None:
    mode_root = create_mode_root(tmp_path, mode="raw")
    nested_root = mode_root / "seeds" / "seed-11" / "opt-7"
    (nested_root / "traces").mkdir(parents=True, exist_ok=True)
    (nested_root / "optimization_result.json").write_text("{}", encoding="utf-8")
    (nested_root / "traces" / "evaluation_events.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="nested seed bundle layout"):
        build_mode_summaries(mode_root)
