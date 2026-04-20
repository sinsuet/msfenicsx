"""Per-controller-decision outcome analytics."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from optimizers.analytics.pareto import hypervolume_2d


def decision_outcomes(
    controller_rows: Iterable[dict[str, Any]],
    llm_response_rows: Iterable[dict[str, Any]],
    operator_rows: Iterable[dict[str, Any]],
    *,
    evaluation_rows: Iterable[dict[str, Any]] | None = None,
    reference_point: tuple[float, float] = (400.0, 20.0),
) -> list[dict[str, Any]]:
    """Join controller/llm/operator rows by decision_id into one row each."""
    llm_by_id = {
        str(r["decision_id"]): r
        for r in llm_response_rows
        if r.get("decision_id") is not None
    }
    op_ids_applied = {
        str(r["decision_id"])
        for r in operator_rows
        if r.get("decision_id") and r.get("offspring")
    }
    hv_by_id = _hypervolume_gain_by_decision(
        evaluation_rows or (),
        reference_point=reference_point,
    )

    out: list[dict[str, Any]] = []
    for controller_row in controller_rows:
        if controller_row.get("decision_id") is None:
            continue
        decision_id = str(controller_row["decision_id"])
        llm_row = llm_by_id.get(decision_id, {})
        hv_gain = hv_by_id.get(decision_id)
        tokens = (llm_row.get("tokens") or {}).get("total", 0)
        out.append(
            {
                "decision_id": decision_id,
                "phase": controller_row.get("phase"),
                "operator_selected": controller_row.get("operator_selected") or controller_row.get("selected_operator_id"),
                "applied": decision_id in op_ids_applied,
                "improved_hypervolume": None if hv_gain is None else bool(hv_gain > 0.0),
                "hypervolume_gain": hv_gain,
                "tokens_total": int(tokens),
                "latency_ms": float(llm_row.get("latency_ms", 0.0)),
            }
        )
    return out


def _hypervolume_gain_by_decision(
    evaluation_rows: Iterable[dict[str, Any]],
    *,
    reference_point: tuple[float, float],
) -> dict[str, float]:
    ordered_rows = sorted(
        [dict(row) for row in evaluation_rows if row.get("decision_id")],
        key=lambda row: int(row.get("eval_index", row.get("evaluation_index", 0))),
    )
    if not ordered_rows:
        return {}

    gains: dict[str, float] = {}
    seen_points: list[tuple[float, float]] = []
    current_decision_id: str | None = None
    decision_before_hv = 0.0
    decision_points: list[tuple[float, float]] = []

    def finalize_pending() -> None:
        nonlocal seen_points, current_decision_id, decision_before_hv, decision_points
        if current_decision_id is None:
            return
        after_hv = hypervolume_2d(seen_points + decision_points, reference_point=reference_point) if (seen_points or decision_points) else 0.0
        gains[current_decision_id] = float(after_hv - decision_before_hv)
        seen_points.extend(decision_points)
        current_decision_id = None
        decision_before_hv = 0.0
        decision_points = []

    for row in ordered_rows:
        decision_id = str(row["decision_id"])
        if current_decision_id is None:
            current_decision_id = decision_id
            decision_before_hv = hypervolume_2d(seen_points, reference_point=reference_point) if seen_points else 0.0
        elif decision_id != current_decision_id:
            finalize_pending()
            current_decision_id = decision_id
            decision_before_hv = hypervolume_2d(seen_points, reference_point=reference_point) if seen_points else 0.0
        if row.get("status") != "ok" or not row.get("objectives"):
            continue
        objectives = row["objectives"]
        decision_points.append(
            (
                float(objectives["temperature_max"]),
                float(objectives["temperature_gradient_rms"]),
            )
        )
    finalize_pending()
    return gains
