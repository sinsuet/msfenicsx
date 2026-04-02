from __future__ import annotations

from pathlib import Path

from optimizers.llm_decision_summary import build_llm_decision_summaries
from tests.optimizers.experiment_fixtures import create_mode_root_with_seed_bundles
from visualization.llm_pages import render_llm_pages


def test_render_llm_decisions_page_includes_prompt_and_selected_operator(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))
    build_llm_decision_summaries(llm_mode_root)

    outputs = render_llm_pages(llm_mode_root)
    html = outputs["decisions"].read_text(encoding="utf-8")

    assert "system prompt" in html.lower()
    assert "selected operator" in html.lower()
