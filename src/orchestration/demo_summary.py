from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from optimization.variable_registry import variable_registry_by_path


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_sort_key(path: Path) -> tuple[int, str]:
    suffix = path.name.removeprefix("run_")
    if suffix.isdigit():
        return (int(suffix), path.name)
    return (10**9, path.name)


def _chip_max_from_evaluation(evaluation: dict[str, Any]) -> float | None:
    objective_summary = evaluation.get("objective_summary", {})
    value = objective_summary.get("chip_max_temperature")
    return float(value) if isinstance(value, (int, float)) else None


def _constraint_limit_from_evaluation(evaluation: dict[str, Any]) -> float | None:
    for item in evaluation.get("violations", []):
        if item.get("name") == "chip_max_temperature" and isinstance(item.get("limit"), (int, float)):
            return float(item["limit"])
    return None


def _change_categories(changes: list[dict[str, Any]]) -> list[str]:
    registry = variable_registry_by_path()
    categories = {
        registry[item["path"]].category
        for item in changes
        if item.get("path") in registry
    }
    return sorted(categories)


def _validation_status(decision: dict[str, Any], validation: dict[str, Any]) -> str:
    if decision.get("status") == "invalid_proposal":
        return "invalid"
    if validation.get("valid") is True:
        return "valid"
    if validation.get("valid") is False:
        return "invalid"
    return "unknown"


def collect_demo_summary(runs_root: str | Path) -> dict[str, Any]:
    runs_root = Path(runs_root)
    run_dirs = sorted(
        [path for path in runs_root.glob("run_*") if path.is_dir()],
        key=_run_sort_key,
    )

    raw_runs: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        evaluation = _read_json_if_exists(run_dir / "evaluation.json")
        proposal = _read_json_if_exists(run_dir / "proposal.json")
        validation = _read_json_if_exists(run_dir / "proposal_validation.json")
        decision = _read_json_if_exists(run_dir / "decision.json")
        changes = proposal.get("changes", [])
        changed_paths = [item["path"] for item in changes if "path" in item]
        raw_runs.append(
            {
                "run_id": run_dir.name,
                "iteration": decision.get("iteration"),
                "status": decision.get("status", "incomplete"),
                "chip_max_before": _chip_max_from_evaluation(evaluation),
                "constraint_limit": _constraint_limit_from_evaluation(evaluation),
                "llm_decision_summary": proposal.get("decision_summary"),
                "changed_paths": changed_paths,
                "change_categories": _change_categories(changes),
                "validation_status": _validation_status(decision, validation),
                "validation_reasons": validation.get("reasons", []),
                "run_dir": str(run_dir),
            }
        )

    for idx, item in enumerate(raw_runs):
        next_item = raw_runs[idx + 1] if idx + 1 < len(raw_runs) else None
        chip_max_before = item["chip_max_before"]
        chip_max_after = next_item["chip_max_before"] if next_item is not None else None
        item["chip_max_after"] = chip_max_after
        if (
            isinstance(chip_max_before, (int, float))
            and isinstance(chip_max_after, (int, float))
        ):
            item["delta_chip_max"] = float(chip_max_after - chip_max_before)
        else:
            item["delta_chip_max"] = None

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_root": str(runs_root),
        "run_count": len(raw_runs),
        "runs": raw_runs,
    }


def write_demo_summary_json(runs_root: str | Path, output_path: str | Path | None = None) -> Path:
    runs_root = Path(runs_root)
    if output_path is None:
        output_path = runs_root / "demo_summary.json"
    output_path = Path(output_path)
    payload = collect_demo_summary(runs_root)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def write_demo_summary_csv(runs_root: str | Path, output_path: str | Path | None = None) -> Path:
    runs_root = Path(runs_root)
    if output_path is None:
        output_path = runs_root / "demo_summary.csv"
    output_path = Path(output_path)
    payload = collect_demo_summary(runs_root)
    fieldnames = [
        "run_id",
        "iteration",
        "status",
        "chip_max_before",
        "chip_max_after",
        "delta_chip_max",
        "constraint_limit",
        "validation_status",
        "changed_paths",
        "change_categories",
        "llm_decision_summary",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in payload["runs"]:
            writer.writerow(
                {
                    **{key: item.get(key) for key in fieldnames},
                    "changed_paths": ";".join(item.get("changed_paths", [])),
                    "change_categories": ";".join(item.get("change_categories", [])),
                }
            )
    return output_path


def write_demo_summary_markdown(runs_root: str | Path, output_path: str | Path | None = None) -> Path:
    runs_root = Path(runs_root)
    if output_path is None:
        output_path = runs_root / "demo_summary.md"
    output_path = Path(output_path)
    payload = collect_demo_summary(runs_root)
    lines = [
        "# Demo Summary",
        "",
        "| Run | Iteration | Status | Chip Max Before | Chip Max After | Delta | Changes | Categories |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["runs"]:
        lines.append(
            "| "
            f"{item['run_id']} | "
            f"{item.get('iteration')} | "
            f"{item.get('validation_status')} | "
            f"{item.get('chip_max_before')} | "
            f"{item.get('chip_max_after')} | "
            f"{item.get('delta_chip_max')} | "
            f"{', '.join(item.get('changed_paths', [])) or '-'} | "
            f"{', '.join(item.get('change_categories', [])) or '-'} |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
