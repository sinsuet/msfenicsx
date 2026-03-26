from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any

import yaml

from compiler.single_run import run_case_from_state
from evaluator.report import evaluate_case
from llm_adapters.dashscope_qwen import propose_next_changes
from optimization.variable_registry import variable_registry_by_path
from thermal_state import ThermalDesignState, load_state
from validation import validate_proposal_against_state

from .run_manager import RunManager


def _to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    return value


def _set_path(payload: Any, dotted_path: str, new_value: Any) -> None:
    parts = dotted_path.split(".")
    cursor = payload
    for part in parts[:-1]:
        if isinstance(cursor, list):
            cursor = cursor[int(part)]
        else:
            cursor = cursor[part]
    last = parts[-1]
    if isinstance(cursor, list):
        cursor[int(last)] = new_value
    else:
        cursor[last] = new_value


def _state_from_payload(payload: dict[str, Any], working_path: Path) -> ThermalDesignState:
    working_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return load_state(working_path)


def _apply_changes_to_state(
    state: ThermalDesignState,
    changes: list[dict[str, Any]],
) -> ThermalDesignState:
    payload = _to_plain_data(state)
    for change in changes:
        _set_path(payload, change["path"], change["new"])
    with tempfile.TemporaryDirectory(prefix="msfenicsx_state_") as tmp_dir:
        working_path = Path(tmp_dir) / "next_state.yaml"
        return _state_from_payload(payload, working_path)


def _build_dry_run_proposal(evaluation: dict[str, Any]) -> dict[str, Any]:
    if evaluation["feasible"]:
        return {
            "decision_summary": "constraints are already satisfied",
            "changes": [],
            "expected_effects": ["keep current feasible design"],
            "risk_notes": [],
            "model_info": {
                "provider": "dry_run",
                "model": "rule_based_stub",
                "requested_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        }

    return {
        "decision_summary": "increase heat spreading capacity above the chip",
        "changes": [
            {
                "path": "materials.spreader_material.conductivity",
                "action": "set",
                "old": 90.0,
                "new": 120.0,
                "reason": "reduce thermal resistance in the heat spreader",
            }
        ],
        "expected_effects": ["lower chip max temperature"],
        "risk_notes": ["material conductivity may exceed practical manufacturing assumptions"],
        "model_info": {
            "provider": "dry_run",
            "model": "rule_based_stub",
            "requested_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    }


def _build_history_summary(
    run_id: str,
    evaluation: dict[str, Any],
    *,
    prior_invalid_feedback: list[str],
    strategy_shift_hint: str | None = None,
) -> str:
    violations = evaluation.get("violations", [])
    if violations:
        parts = [f"{run_id} violated {', '.join(item['name'] for item in violations)}"]
    else:
        parts = [f"{run_id} satisfied all constraints; continue improving the objective if possible"]
    if prior_invalid_feedback:
        parts.append("previous invalid proposals:")
        parts.extend(prior_invalid_feedback)
    if strategy_shift_hint:
        parts.append(f"strategy shift suggestion: {strategy_shift_hint}")
    return " | ".join(parts)


def _extract_primary_objective(evaluation: dict[str, Any]) -> tuple[str, float] | None:
    for name, value in evaluation.get("objective_summary", {}).items():
        if isinstance(value, (int, float)):
            return name, float(value)
    return None


def _categorize_changes(changes: list[dict[str, Any]]) -> list[str]:
    registry = variable_registry_by_path()
    categories = {
        registry[change["path"]].category
        for change in changes
        if change.get("path") in registry
    }
    return sorted(categories)


def _build_strategy_shift_hint(
    *,
    objective_history: list[tuple[str, float]],
    recent_change_categories: list[list[str]],
    prior_invalid_feedback: list[str],
    improvement_threshold: float = 0.001,
    stagnation_window: int = 2,
) -> str | None:
    if len(objective_history) < stagnation_window + 1:
        return None

    recent_objectives = objective_history[-(stagnation_window + 1) :]
    objective_name = recent_objectives[-1][0]
    if any(name != objective_name for name, _ in recent_objectives):
        return None

    improvements = [
        previous_value - current_value
        for (_, previous_value), (_, current_value) in zip(
            recent_objectives,
            recent_objectives[1:],
        )
    ]
    if any(delta >= improvement_threshold for delta in improvements):
        return None

    invalid_feedback_text = " ".join(prior_invalid_feedback).lower()
    if any(
        token in invalid_feedback_text
        for token in ("overlap", "inside envelope", "outside", "design domain", "clearance")
    ):
        return (
            f"recent {objective_name} improvement is below {improvement_threshold:.4f} "
            f"for {stagnation_window} consecutive iterations; geometry changes are hitting "
            "legality limits, so prefer material tuning or smaller position/size refinements"
        )

    if len(recent_change_categories) >= stagnation_window:
        recent_categories = recent_change_categories[-stagnation_window:]
        if all(categories == ["material"] for categories in recent_categories):
            return (
                f"recent {objective_name} improvement is below {improvement_threshold:.4f} "
                f"for {stagnation_window} consecutive iterations; try geometry variables or "
                "a coordinated multi-variable change"
            )
        if all(categories == ["geometry"] for categories in recent_categories):
            return (
                f"recent {objective_name} improvement is below {improvement_threshold:.4f} "
                f"for {stagnation_window} consecutive iterations; try material variables or "
                "smaller position/size refinements"
            )

    return (
        f"recent {objective_name} improvement is below {improvement_threshold:.4f} "
        f"for {stagnation_window} consecutive iterations; try a different variable category "
        "or a coordinated multi-variable change"
    )


def run_optimization_loop(
    *,
    state_path: str | Path,
    runs_root: str | Path,
    max_iters: int = 3,
    dry_run_llm: bool = False,
    max_invalid_proposals: int = 2,
    model: str = "qwen3.5-plus",
    enable_thinking: bool = False,
    continue_when_feasible: bool = False,
) -> dict[str, Any]:
    current_state = load_state(state_path)
    runs_root = Path(runs_root)
    manager = RunManager(runs_root)
    invalid_proposal_streak = 0
    completed_iterations = 0
    final_status = "max_iters_reached"
    last_run_id: str | None = None
    prior_invalid_feedback: list[str] = []
    objective_history: list[tuple[str, float]] = []
    recent_change_categories: list[list[str]] = []

    for iteration in range(1, max_iters + 1):
        completed_iterations = iteration
        run_dir = manager.create_run_dir()
        last_run_id = run_dir.name
        manager.save_state_snapshot(current_state, run_dir)

        simulation = run_case_from_state(current_state, output_root=run_dir / "outputs")
        evaluation = evaluate_case(current_state, simulation["metrics"])
        manager.write_json(run_dir, "evaluation.json", evaluation)
        primary_objective = _extract_primary_objective(evaluation)
        if primary_objective is not None:
            objective_history.append(primary_objective)

        if evaluation["feasible"] and not (continue_when_feasible and not dry_run_llm):
            proposal = _build_dry_run_proposal(evaluation)
            manager.write_json(run_dir, "proposal.json", proposal)
            manager.write_json(
                run_dir,
                "decision.json",
                {
                    "iteration": iteration,
                    "run_id": run_dir.name,
                    "status": "feasible",
                    "applied_changes": [],
                },
            )
            final_status = "feasible"
            break

        if dry_run_llm:
            proposal = _build_dry_run_proposal(evaluation)
        else:
            strategy_shift_hint = _build_strategy_shift_hint(
                objective_history=objective_history,
                recent_change_categories=recent_change_categories,
                prior_invalid_feedback=prior_invalid_feedback,
            )
            history_summary = _build_history_summary(
                run_dir.name,
                evaluation,
                prior_invalid_feedback=prior_invalid_feedback,
                strategy_shift_hint=strategy_shift_hint,
            )
            proposal = propose_next_changes(
                state=current_state,
                evaluation=evaluation,
                history_summary=history_summary,
                output_dir=run_dir,
                model=model,
                enable_thinking=enable_thinking,
            )
        manager.write_json(run_dir, "proposal.json", proposal)
        proposal_validation = validate_proposal_against_state(current_state, proposal)
        manager.write_json(run_dir, "proposal_validation.json", proposal_validation)

        if not proposal["changes"]:
            invalid_proposal_streak += 1
            prior_invalid_feedback.append(
                f"{run_dir.name} invalid proposal: empty changes list"
            )
            manager.write_json(
                run_dir,
                "decision.json",
                {
                    "iteration": iteration,
                    "run_id": run_dir.name,
                    "status": "invalid_proposal",
                    "applied_changes": [],
                },
            )
            if invalid_proposal_streak >= max_invalid_proposals:
                final_status = "invalid_proposal_limit"
                break
            continue

        if not proposal_validation["valid"]:
            invalid_proposal_streak += 1
            prior_invalid_feedback.append(
                f"{run_dir.name} invalid proposal: {'; '.join(proposal_validation['reasons'])}"
            )
            manager.write_json(
                run_dir,
                "decision.json",
                {
                    "iteration": iteration,
                    "run_id": run_dir.name,
                    "status": "invalid_proposal",
                    "applied_changes": [],
                    "validation_reasons": proposal_validation["reasons"],
                },
            )
            if invalid_proposal_streak >= max_invalid_proposals:
                final_status = "invalid_proposal_limit"
                break
            continue

        invalid_proposal_streak = 0
        prior_invalid_feedback = []
        recent_change_categories.append(_categorize_changes(proposal["changes"]))
        next_state = _apply_changes_to_state(current_state, proposal["changes"])
        manager.save_state_snapshot(next_state, run_dir, filename="next_state.yaml")
        manager.write_json(
            run_dir,
            "decision.json",
            {
                "iteration": iteration,
                "run_id": run_dir.name,
                "status": "proposal_applied",
                "applied_changes": proposal["changes"],
            },
        )
        current_state = next_state

    return {
        "iterations": completed_iterations,
        "status": final_status,
        "last_run_id": last_run_id,
        "runs_root": str(runs_root),
    }
