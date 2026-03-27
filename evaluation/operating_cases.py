"""Helpers for multicase evaluation and CLI operating-case inputs."""

from __future__ import annotations

from pathlib import Path

from core.schema.io import load_case, load_solution


def parse_named_paths(items: list[str], label: str) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for item in items:
        operating_case_id, separator, raw_path = item.partition("=")
        if separator != "=" or not operating_case_id.strip() or not raw_path.strip():
            raise ValueError(f"{label} entries must use the form <operating_case_id>=<path>.")
        if operating_case_id in parsed:
            raise ValueError(f"Duplicate {label} entry for operating case '{operating_case_id}'.")
        parsed[operating_case_id] = Path(raw_path)
    return parsed


def load_named_cases(items: list[str]) -> dict[str, object]:
    return {operating_case_id: load_case(path) for operating_case_id, path in parse_named_paths(items, "--case").items()}


def load_named_solutions(items: list[str]) -> dict[str, object]:
    return {
        operating_case_id: load_solution(path)
        for operating_case_id, path in parse_named_paths(items, "--solution").items()
    }
