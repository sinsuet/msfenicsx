"""Verify the scientific rcParams baseline."""

from __future__ import annotations

import matplotlib


def test_apply_baseline_sets_expected_rcparams() -> None:
    import matplotlib.pyplot as plt
    from visualization.style.baseline import apply_baseline

    # Snapshot to restore afterwards
    original = matplotlib.rcParams.copy()
    try:
        apply_baseline()
        assert matplotlib.rcParams["font.family"][0] == "DejaVu Serif"
        assert matplotlib.rcParams["mathtext.fontset"] == "stix"
        assert float(matplotlib.rcParams["font.size"]) == 9.0
        assert float(matplotlib.rcParams["axes.linewidth"]) == 0.6
        assert matplotlib.rcParams["xtick.direction"] == "in"
        assert matplotlib.rcParams["ytick.direction"] == "in"
        assert matplotlib.rcParams["legend.frameon"] is False
        assert matplotlib.rcParams["figure.constrained_layout.use"] is True
    finally:
        matplotlib.rcParams.update(original)
        plt.close("all")


def test_palette_categorical_has_eight_okabe_ito_hex_values() -> None:
    from visualization.style.baseline import PALETTE_CATEGORICAL

    assert len(PALETTE_CATEGORICAL) == 8
    for entry in PALETTE_CATEGORICAL:
        assert entry.startswith("#") and len(entry) == 7


def test_dpi_constants() -> None:
    from visualization.style.baseline import DPI_DEFAULT, DPI_FIELD_HIRES, DPI_HIRES

    assert DPI_DEFAULT == 600
    assert DPI_HIRES == 1200
    assert DPI_FIELD_HIRES == 2400
