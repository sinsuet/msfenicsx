"""Operator x phase usage heatmap."""

from __future__ import annotations


def test_operator_phase_heatmap_counts() -> None:
    from optimizers.analytics.heatmap import operator_phase_heatmap

    operator_rows = [
        {"operator_name": "global_explore", "decision_id": "g000-e0001-d00"},
        {"operator_name": "local_refine", "decision_id": "g001-e0010-d00"},
        {"operator_name": "global_explore", "decision_id": "g001-e0011-d00"},
        {"operator_name": "slide_sink", "decision_id": None},  # raw/union
    ]
    controller_rows = [
        {"decision_id": "g000-e0001-d00", "phase": "prefeasible"},
        {"decision_id": "g001-e0010-d00", "phase": "post_feasible_recover"},
        {"decision_id": "g001-e0011-d00", "phase": "post_feasible_expand"},
    ]
    grid = operator_phase_heatmap(operator_rows, controller_rows)

    assert grid["global_explore"]["prefeasible"] == 1
    assert grid["global_explore"]["post_feasible_expand"] == 1
    assert grid["local_refine"]["post_feasible_recover"] == 1
    assert grid["slide_sink"]["n/a"] == 1


def test_operator_phase_heatmap_no_controller_rows_single_na_column() -> None:
    from optimizers.analytics.heatmap import operator_phase_heatmap

    operator_rows = [
        {"operator_name": "native_sbx_pm", "decision_id": None},
        {"operator_name": "native_sbx_pm", "decision_id": None},
    ]
    grid = operator_phase_heatmap(operator_rows, [])
    assert grid["native_sbx_pm"] == {"n/a": 2}
