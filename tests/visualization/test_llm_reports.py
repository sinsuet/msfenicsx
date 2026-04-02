from __future__ import annotations

from pathlib import Path

from optimizers.llm_decision_summary import build_llm_decision_summaries
from tests.optimizers.experiment_fixtures import create_mode_root_with_seed_bundles
from visualization.llm_reports import render_llm_reports


def test_render_llm_experiment_summary_writes_markdown_with_tables(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))
    build_llm_decision_summaries(llm_mode_root)

    report_paths = render_llm_reports(llm_mode_root, comparison_root=None)
    markdown = report_paths["markdown"].read_text(encoding="utf-8")

    assert "| Mode |" in markdown
    assert "Key Improvement Points" in markdown
    assert "Risk" in markdown
