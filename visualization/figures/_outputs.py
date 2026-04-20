"""Shared output-path helpers for figure renderers."""

from __future__ import annotations

from pathlib import Path


def paired_pdf_path(output: Path) -> Path:
    output = Path(output)
    return output.parent / "pdf" / f"{output.stem}.pdf"


def ensure_output_parent(output: Path) -> Path:
    resolved = Path(output)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved
