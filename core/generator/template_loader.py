"""Load scenario templates for the generation pipeline."""

from __future__ import annotations

from pathlib import Path

from core.schema.io import load_template
from core.schema.models import ScenarioTemplate


def load_template_model(path: str | Path) -> ScenarioTemplate:
    return load_template(path)
