"""Per-decision outcome table: applied? HV gain? token cost?"""

from __future__ import annotations


def test_decision_outcomes_joins_controller_and_llm_rows() -> None:
    from optimizers.analytics.decisions import decision_outcomes

    controller_rows = [
        {"decision_id": "g000-e0001-d00", "phase": "prefeasible", "operator_selected": "g_exp"},
        {"decision_id": "g001-e0010-d00", "phase": "post_feasible_expand", "operator_selected": "l_ref"},
    ]
    llm_response_rows = [
        {"decision_id": "g000-e0001-d00", "tokens": {"total": 300}, "latency_ms": 850},
        {"decision_id": "g001-e0010-d00", "tokens": {"total": 500}, "latency_ms": 1200},
    ]
    operator_rows = [
        {
            "decision_id": "g000-e0001-d00",
            "parents": ["ind1"],
            "offspring": ["ind2"],
        },
    ]
    rows = decision_outcomes(controller_rows, llm_response_rows, operator_rows)
    assert len(rows) == 2
    by_id = {r["decision_id"]: r for r in rows}
    assert by_id["g000-e0001-d00"]["applied"] is True
    assert by_id["g001-e0010-d00"]["applied"] is False
    assert by_id["g000-e0001-d00"]["tokens_total"] == 300
    assert by_id["g001-e0010-d00"]["tokens_total"] == 500
