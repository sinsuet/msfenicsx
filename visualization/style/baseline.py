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

SPATIAL_BOARD_EDGE: str = "#1A1A1A"
SPATIAL_LAYOUT_OUTLINE: str = "#2A2A2A"
SPATIAL_LAYOUT_FILL: str = "#D8D2C4"
SPATIAL_FIELD_OUTLINE: str = "#F7F7F4"
SPATIAL_SINK_COLOR: str = "#00A9B7"
SPATIAL_SINK_EDGE: str = "#0D3B40"
SPATIAL_INFO_BG: str = "#F5F1E8"
SPATIAL_INFO_EDGE: str = "#D8D0C2"
SPATIAL_INFO_TEXT: str = "#222222"
SPATIAL_LABEL_LIGHT_FILL: str = "#FFFDF8"
SPATIAL_LABEL_LIGHT_TEXT: str = "#111111"
SPATIAL_LABEL_DARK_FILL: str = "#1B1B1B"
SPATIAL_LABEL_DARK_TEXT: str = "#FFFDF8"

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
