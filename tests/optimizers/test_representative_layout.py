# tests/optimizers/test_representative_layout.py
"""Representative bundle layout."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def test_write_representative_bundle_flat_layout(tmp_path: Path) -> None:
    from optimizers.artifacts import write_representative_bundle

    repr_root = tmp_path / "representatives" / "knee"
    write_representative_bundle(
        repr_root,
        case_yaml="{}",
        solution_yaml="{}",
        evaluation_yaml="{}",
        temperature_grid=np.zeros((4, 4)),
        gradient_grid=np.zeros((4, 4)),
    )

    expected_top = {"case.yaml", "solution.yaml", "evaluation.yaml", "fields"}
    actual_top = {p.name for p in repr_root.iterdir()}
    assert actual_top == expected_top

    fields = set(p.name for p in (repr_root / "fields").iterdir())
    assert fields == {"temperature_grid.npz", "gradient_magnitude_grid.npz"}

    assert not (repr_root / "figures").exists()
    assert not (repr_root / "logs").exists()
    assert not (repr_root / "summaries").exists()
    assert not (repr_root / "pages").exists()
