"""Scientific rcParams baseline — IEEE/Elsevier double-column ready."""

from __future__ import annotations

import matplotlib

FONT_FAMILY: list[str] = ["DejaVu Serif", "Noto Serif CJK SC", "serif"]
FONT_FAMILY_MATH: str = "stix"
BASE_FONT_SIZE: int = 9

DPI_DEFAULT: int = 600
DPI_HIRES: int = 1200
DPI_FIELD_HIRES: int = 2400

COLORMAP_TEMPERATURE: str = "inferno"
COLORMAP_GRADIENT: str = "viridis"

# Okabe-Ito colorblind-safe palette.
PALETTE_CATEGORICAL: list[str] = [
    "#000000",
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]


def apply_baseline() -> None:
    """Apply the scientific baseline to matplotlib rcParams."""
    matplotlib.rcParams["font.family"] = FONT_FAMILY
    matplotlib.rcParams["font.serif"] = FONT_FAMILY
    matplotlib.rcParams["font.size"] = BASE_FONT_SIZE
    matplotlib.rcParams["mathtext.fontset"] = FONT_FAMILY_MATH
    matplotlib.rcParams["axes.linewidth"] = 0.6
    matplotlib.rcParams["axes.labelsize"] = BASE_FONT_SIZE
    matplotlib.rcParams["axes.titlesize"] = BASE_FONT_SIZE + 1
    matplotlib.rcParams["xtick.direction"] = "in"
    matplotlib.rcParams["ytick.direction"] = "in"
    matplotlib.rcParams["xtick.labelsize"] = BASE_FONT_SIZE - 1
    matplotlib.rcParams["ytick.labelsize"] = BASE_FONT_SIZE - 1
    matplotlib.rcParams["legend.frameon"] = False
    matplotlib.rcParams["legend.fontsize"] = BASE_FONT_SIZE - 1
    matplotlib.rcParams["figure.constrained_layout.use"] = True
    matplotlib.rcParams["savefig.bbox"] = "tight"
    matplotlib.rcParams["savefig.pad_inches"] = 0.02
