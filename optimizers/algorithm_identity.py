"""Display labels and compact identity helpers for optimizer algorithms."""

from __future__ import annotations


_BACKBONE_LABELS = {
    "moead": "MOEA/D",
    "nsga2": "NSGA-II",
    "spea2": "SPEA2",
}


def algorithm_label(backbone: str | None) -> str:
    normalized = "" if backbone is None else str(backbone).strip().lower()
    if not normalized:
        return "Unknown"
    return _BACKBONE_LABELS.get(normalized, normalized.upper())
