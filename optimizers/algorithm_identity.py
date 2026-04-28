"""Display labels and compact identity helpers for optimizer algorithms."""

from __future__ import annotations


_BACKBONE_LABELS = {
    "cmopso": "CMOPSO",
    "ctaea": "C-TAEA",
    "moead": "MOEA/D",
    "nsga2": "NSGA-II",
    "nsga3": "NSGA-III",
    "rvea": "RVEA",
    "spea2": "SPEA2",
}


def algorithm_label(backbone: str | None) -> str:
    normalized = "" if backbone is None else str(backbone).strip().lower()
    if not normalized:
        return "Unknown"
    return _BACKBONE_LABELS.get(normalized, normalized.upper())
