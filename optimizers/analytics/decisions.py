"""Per-controller-decision outcome analytics (llm runs only)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def decision_outcomes(
    controller_rows: Iterable[dict[str, Any]],
    llm_response_rows: Iterable[dict[str, Any]],
    operator_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join controller/llm/operator rows by decision_id into one row each."""
    llm_by_id = {str(r["decision_id"]): r for r in llm_response_rows}
    op_ids_applied = {
        str(r["decision_id"])
        for r in operator_rows
        if r.get("decision_id") and r.get("offspring")
    }

    out: list[dict[str, Any]] = []
    for controller_row in controller_rows:
        decision_id = str(controller_row["decision_id"])
        llm_row = llm_by_id.get(decision_id, {})
        tokens = (llm_row.get("tokens") or {}).get("total", 0)
        out.append(
            {
                "decision_id": decision_id,
                "phase": controller_row.get("phase"),
                "operator_selected": controller_row.get("operator_selected"),
                "applied": decision_id in op_ids_applied,
                "tokens_total": int(tokens),
                "latency_ms": float(llm_row.get("latency_ms", 0.0)),
            }
        )
    return out
