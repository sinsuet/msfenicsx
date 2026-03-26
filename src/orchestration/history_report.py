from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import yaml

from optimization.variable_registry import variable_registry_by_path


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _run_sort_key(path: Path) -> tuple[int, str]:
    suffix = path.name.removeprefix("run_")
    if suffix.isdigit():
        return (int(suffix), path.name)
    return (10**9, path.name)


def _group_sort_key(path: Path) -> tuple[int, str]:
    suffix = path.name.removeprefix("group_")
    if suffix.isdigit():
        return (int(suffix), path.name)
    return (10**9, path.name)


def _read_summary_text_metrics(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    metrics: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        normalized_key = key.strip().split("(", 1)[0].strip()
        if normalized_key not in {"temperature_min", "temperature_max"}:
            continue
        try:
            metrics[normalized_key] = float(raw_value.strip())
        except ValueError:
            continue
    return metrics


def _chip_max_from_evaluation(evaluation: dict[str, Any]) -> float | None:
    value = evaluation.get("objective_summary", {}).get("chip_max_temperature")
    return float(value) if isinstance(value, (int, float)) else None


def _constraint_limit_from_evaluation(evaluation: dict[str, Any]) -> float | None:
    for item in evaluation.get("violations", []):
        if item.get("name") == "chip_max_temperature" and isinstance(item.get("limit"), (int, float)):
            return float(item["limit"])
    return None


def _constraint_limit_from_state(state_payload: dict[str, Any]) -> float | None:
    for item in state_payload.get("constraints", []):
        if item.get("name") == "chip_max_temperature" and isinstance(item.get("value"), (int, float)):
            return float(item["value"])
    return None


def _validation_status(decision: dict[str, Any], validation: dict[str, Any]) -> str:
    if decision.get("status") == "invalid_proposal":
        return "invalid"
    if validation.get("valid") is True:
        return "valid"
    if validation.get("valid") is False:
        return "invalid"
    return "unknown"


def _change_categories(changes: list[dict[str, Any]]) -> list[str]:
    registry = variable_registry_by_path()
    categories = {
        registry[item["path"]].category
        for item in changes
        if item.get("path") in registry
    }
    return sorted(categories)


def _relative_path(path: Path, root: Path) -> str | None:
    if not path.exists():
        return None
    return str(path.relative_to(root))


def _state_snapshot_summary(path: Path) -> dict[str, Any] | None:
    payload = _read_yaml_if_exists(path)
    if not payload:
        return None

    materials = payload.get("materials", {})
    components: list[dict[str, Any]] = []
    for component in payload.get("components", []):
        if not isinstance(component, dict):
            continue
        material_name = component.get("material")
        material = materials.get(material_name, {}) if isinstance(materials, dict) else {}
        conductivity = material.get("conductivity") if isinstance(material, dict) else None
        components.append(
            {
                "name": component.get("name"),
                "x0": component.get("x0"),
                "y0": component.get("y0"),
                "width": component.get("width"),
                "height": component.get("height"),
                "material": material_name,
                "conductivity": conductivity,
            }
        )

    return {
        "design_domain": payload.get("geometry", {}).get("design_domain", {}),
        "components": components,
        "constraints": payload.get("constraints", []),
        "units": payload.get("units", {}),
        "reference_conditions": payload.get("reference_conditions", {}),
    }


def _build_run_entry(run_dir: Path, runs_root: Path) -> dict[str, Any]:
    evaluation = _read_json_if_exists(run_dir / "evaluation.json")
    proposal = _read_json_if_exists(run_dir / "proposal.json")
    validation = _read_json_if_exists(run_dir / "proposal_validation.json")
    decision = _read_json_if_exists(run_dir / "decision.json")
    state_path = run_dir / "state.yaml"
    next_state_path = run_dir / "next_state.yaml"
    state_payload = _read_yaml_if_exists(state_path)

    figures_dir = run_dir / "outputs" / "figures"
    data_dir = run_dir / "outputs" / "data"
    summary_metrics = _read_summary_text_metrics(data_dir / "summary.txt")
    chip_max_before = _chip_max_from_evaluation(evaluation)
    changes = proposal.get("changes", [])

    return {
        "run_id": run_dir.name,
        "iteration": decision.get("iteration"),
        "status": decision.get("status", "incomplete"),
        "feasible": evaluation.get("feasible"),
        "constraint_limit": _constraint_limit_from_evaluation(evaluation) or _constraint_limit_from_state(state_payload),
        "chip_max_before": chip_max_before,
        "chip_max_temperature": chip_max_before,
        "temperature_min": evaluation.get("temperature_min", summary_metrics.get("temperature_min")),
        "temperature_max": evaluation.get("temperature_max", summary_metrics.get("temperature_max")),
        "objective_summary": evaluation.get("objective_summary", {}),
        "priority_actions": evaluation.get("priority_actions", []),
        "violations": evaluation.get("violations", []),
        "validation_status": _validation_status(decision, validation),
        "validation_valid": validation.get("valid"),
        "validation_reasons": validation.get("reasons", []),
        "decision_summary": proposal.get("decision_summary"),
        "changes": changes,
        "changed_paths": [item["path"] for item in changes if "path" in item],
        "change_categories": _change_categories(changes),
        "expected_effects": proposal.get("expected_effects", []),
        "risk_notes": proposal.get("risk_notes", []),
        "model_info": proposal.get("model_info", {}),
        "overview_html": _relative_path(figures_dir / "overview.html", runs_root),
        "temperature_html": _relative_path(figures_dir / "temperature.html", runs_root),
        "state_path": _relative_path(state_path, runs_root),
        "next_state_path": _relative_path(next_state_path, runs_root),
        "state_snapshot": _state_snapshot_summary(state_path),
        "next_state_snapshot": _state_snapshot_summary(next_state_path),
        "run_dir": str(run_dir),
        "relative_run_dir": str(run_dir.relative_to(runs_root)),
    }


def collect_history_summary(runs_root: str | Path) -> dict[str, Any]:
    runs_root = Path(runs_root)
    run_dirs = sorted(
        [path for path in runs_root.glob("run_*") if path.is_dir()],
        key=_run_sort_key,
    )
    entries = [_build_run_entry(run_dir, runs_root) for run_dir in run_dirs]

    for idx, entry in enumerate(entries):
        next_entry = entries[idx + 1] if idx + 1 < len(entries) else None
        chip_max_after = next_entry.get("chip_max_before") if next_entry is not None else None
        entry["chip_max_after"] = chip_max_after
        if isinstance(entry.get("chip_max_before"), (int, float)) and isinstance(chip_max_after, (int, float)):
            entry["delta_chip_max"] = float(chip_max_after - entry["chip_max_before"])
        else:
            entry["delta_chip_max"] = None
        entry["effect_observed_in_run"] = next_entry.get("run_id") if next_entry is not None else None
        entry["next_overview_html"] = next_entry.get("overview_html") if next_entry is not None else None
        entry["next_temperature_html"] = next_entry.get("temperature_html") if next_entry is not None else None

    numeric_runs = [item for item in entries if isinstance(item.get("chip_max_before"), (int, float))]
    best_run = min(numeric_runs, key=lambda item: item["chip_max_before"]) if numeric_runs else None
    first_feasible = next((item["run_id"] for item in entries if item.get("feasible") is True), None)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_root": str(runs_root),
        "run_count": len(entries),
        "initial_overview_html": entries[0].get("overview_html") if entries else None,
        "initial_temperature_html": entries[0].get("temperature_html") if entries else None,
        "best_run_id": best_run.get("run_id") if best_run else None,
        "best_chip_max": best_run.get("chip_max_before") if best_run else None,
        "first_feasible_run": first_feasible,
        "runs": entries,
    }


def write_history_summary(runs_root: str | Path, output_path: str | Path | None = None) -> Path:
    runs_root = Path(runs_root)
    if output_path is None:
        output_path = runs_root / "history_summary.json"
    output_path = Path(output_path)
    payload = collect_history_summary(runs_root)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def _first_numeric(values: list[Any]) -> float | None:
    for value in values:
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _last_numeric(values: list[Any]) -> float | None:
    for value in reversed(values):
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _first_matching_run_id(runs: list[dict[str, Any]], predicate) -> str | None:
    for run in runs:
        if predicate(run):
            return run["run_id"]
    return None


def _build_group_entry(group_dir: Path, root: Path) -> dict[str, Any]:
    history_summary_path = group_dir / "history_summary.json"
    history_html_path = group_dir / "history.html"
    if history_summary_path.exists():
        history_summary = json.loads(history_summary_path.read_text(encoding="utf-8"))
    else:
        history_summary = collect_history_summary(group_dir)

    runs = history_summary.get("runs", [])
    chip_values = [run.get("chip_max_before") for run in runs]

    return {
        "group_id": group_dir.name,
        "run_count": len(runs),
        "initial_chip_max": _first_numeric(chip_values),
        "latest_observed_chip_max": _last_numeric(chip_values),
        "best_chip_max": history_summary.get("best_chip_max"),
        "first_feasible_run": history_summary.get("first_feasible_run"),
        "first_base_k_run": _first_matching_run_id(
            runs,
            lambda run: any(
                change.get("path") == "materials.base_material.conductivity"
                for change in run.get("changes", [])
            ),
        ),
        "applied_run_count": sum(1 for run in runs if run.get("status") == "proposal_applied"),
        "invalid_run_count": sum(1 for run in runs if run.get("validation_status") == "invalid"),
        "latest_status": runs[-1].get("status") if runs else None,
        "history_summary": _relative_path(history_summary_path, root),
        "history_html": _relative_path(history_html_path, root),
        "group_figures": {
            "chip_max_trend": _relative_path(group_dir / "figures" / "chip_max_trend.png", root),
            "delta_trend": _relative_path(group_dir / "figures" / "delta_trend.png", root),
            "category_timeline": _relative_path(group_dir / "figures" / "category_timeline.png", root),
        },
    }


def collect_history_collection_summary(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    group_dirs = sorted(
        [path for path in root.glob("group_*") if path.is_dir()],
        key=_group_sort_key,
    )
    groups = [_build_group_entry(group_dir, root) for group_dir in group_dirs]
    observed_values = [item["latest_observed_chip_max"] for item in groups if isinstance(item.get("latest_observed_chip_max"), (int, float))]
    best_group = min(
        (item for item in groups if isinstance(item.get("best_chip_max"), (int, float))),
        key=lambda item: item["best_chip_max"],
        default=None,
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "group_count": len(groups),
        "feasible_group_count": sum(
            1 for item in groups if isinstance(item.get("latest_observed_chip_max"), (int, float)) and item["latest_observed_chip_max"] <= 85.0
        ),
        "average_latest_chip_max": (sum(observed_values) / len(observed_values)) if observed_values else None,
        "best_group_id": best_group.get("group_id") if best_group else None,
        "best_group_chip_max": best_group.get("best_chip_max") if best_group else None,
        "aggregate_figures": {
            "trajectories": _relative_path(root / "figures" / "consistency_10x15_trajectories.png", root),
            "final_chip_max": _relative_path(root / "figures" / "consistency_10x15_final_chip_max.png", root),
            "first_base_k_round": _relative_path(root / "figures" / "consistency_10x15_first_base_k_round.png", root),
        },
        "groups": groups,
    }


def write_history_collection_summary(root: str | Path, output_path: str | Path | None = None) -> Path:
    root = Path(root)
    if output_path is None:
        output_path = root / "history_summary.json"
    output_path = Path(output_path)
    payload = collect_history_collection_summary(root)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
