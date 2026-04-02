from __future__ import annotations

from tests.optimizers.experiment_fixtures import create_template_root_with_modes
from visualization.template_comparison import render_template_comparisons


def test_render_template_comparison_builds_three_mode_summary(tmp_path) -> None:
    template_root = create_template_root_with_modes(tmp_path)

    outputs = render_template_comparisons(template_root)

    assert (template_root / "comparisons" / "raw-vs-union-vs-llm" / "overview.html").exists()
    assert "raw-vs-union-vs-llm" in outputs
