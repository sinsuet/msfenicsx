from __future__ import annotations

from pathlib import Path

from optimizers.mode_summary import build_mode_summaries
from tests.optimizers.experiment_fixtures import create_mode_root_with_seed_bundles
from visualization.mode_pages import render_mode_pages


def test_render_mode_index_links_seed_pages_and_representatives(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    build_mode_summaries(mode_root)

    output_path = render_mode_pages(mode_root)["index"]
    html = output_path.read_text(encoding="utf-8")

    assert output_path.exists()
    assert "seed-11" in html
    assert "knee" in html
