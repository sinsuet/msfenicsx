"""Scientific rcParams baseline — IEEE/Elsevier double-column ready."""

from __future__ import annotations

import matplotlib as mpl

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
    mpl.rcParams["font.family"] = "serif"
    mpl.rcParams["font.serif"] = FONT_FAMILY
    mpl.rcParams["font.size"] = BASE_FONT_SIZE
    mpl.rcParams["mathtext.fontset"] = FONT_FAMILY_MATH
    mpl.rcParams["axes.linewidth"] = 0.6
    mpl.rcParams["axes.labelsize"] = BASE_FONT_SIZE
    mpl.rcParams["axes.titlesize"] = BASE_FONT_SIZE + 1
    mpl.rcParams["xtick.direction"] = "in"
    mpl.rcParams["ytick.direction"] = "in"
    mpl.rcParams["legend.frameon"] = False
    mpl.rcParams["figure.constrained_layout.use"] = True
    mpl.rcParams["savefig.bbox"] = "tight"
    mpl.rcParams["savefig.pad_inches"] = 0.02
