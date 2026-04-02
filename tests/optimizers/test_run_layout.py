from __future__ import annotations

from datetime import datetime
from pathlib import Path

from optimizers.run_layout import build_run_id, initialize_run_root


def test_build_run_id_orders_modes_stably() -> None:
    run_id = build_run_id(datetime(2026, 4, 2, 15, 30), ["llm", "raw", "union"])

    assert run_id == "0402_1530__raw_union_llm"


def test_initialize_run_root_creates_shared_and_mode_directories(tmp_path: Path) -> None:
    run_root = initialize_run_root(
        tmp_path / "scenario_runs",
        scenario_template_id="s1_typical",
        run_id="0402_1530__raw_union",
        modes=["raw", "union"],
    )

    assert run_root == tmp_path / "scenario_runs" / "s1_typical" / "0402_1530__raw_union"
    assert (run_root / "shared").is_dir()
    assert (run_root / "raw").is_dir()
    assert (run_root / "union").is_dir()
    assert not (run_root / "comparison").exists()
