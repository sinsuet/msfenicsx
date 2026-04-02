from __future__ import annotations

from pathlib import Path

import pytest

from visualization.report_beamer_pack import build_beamer_pack_context, render_beamer_pack


def test_build_beamer_pack_context_extracts_seed23_metrics() -> None:
    context = build_beamer_pack_context()

    raw_seed23 = context["seeds"]["seed23"]["modes"]["raw"]
    union_seed23 = context["seeds"]["seed23"]["modes"]["union"]
    llm_seed23 = context["seeds"]["seed23"]["modes"]["llm"]

    assert raw_seed23["aggregate"]["feasible_rate"] == pytest.approx(0.09302325581395349)
    assert union_seed23["aggregate"]["feasible_rate"] == pytest.approx(0.007751937984496124)
    assert llm_seed23["aggregate"]["feasible_rate"] == pytest.approx(0.14728682170542637)

    assert raw_seed23["representative"]["evaluation_index"] == 123
    assert union_seed23["representative"]["evaluation_index"] == 127
    assert llm_seed23["representative"]["evaluation_index"] == 73


def test_build_beamer_pack_context_counts_seed23_llm_operator_usage() -> None:
    context = build_beamer_pack_context()

    operator_counts = context["seeds"]["seed23"]["operator_counts"]["llm"]

    assert operator_counts["battery_to_warm_zone"] == 44
    assert operator_counts["hot_pair_separate"] == 27
    assert operator_counts["radiator_align_hot_pair"] == 18
    assert operator_counts["native_sbx_pm"] == 8


def test_render_beamer_pack_writes_expected_pngs(tmp_path: Path) -> None:
    outputs = render_beamer_pack(output_dir=tmp_path, include_pdf=False)

    output_names = {path.name for path in outputs}
    expected_names = {
        "01_benchmark_layout_overview.png",
        "02_design_variables_schematic.png",
        "03_raw_union_llm_architecture.png",
        "04_seed23_initial_and_final_layouts.png",
        "05_seed23_metrics_comparison.png",
        "06_seed23_representative_objectives.png",
        "07_seed23_operator_mix.png",
        "08_seed17_best_snapshot.png",
    }

    assert expected_names.issubset(output_names)
    for filename in expected_names:
        assert (tmp_path / filename).exists()
        assert (tmp_path / filename).stat().st_size > 0
