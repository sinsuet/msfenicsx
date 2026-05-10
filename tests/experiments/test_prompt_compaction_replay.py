import json
from types import SimpleNamespace

from scenario_runs.prompt_compaction_replay import replay_compacted_prompts as replay


def test_compact_decision_v2_prompt_uses_evidence_first_system_and_bucketed_user() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="compact_decision_v2",
    )

    payload = json.loads(user_prompt)

    assert payload["prompt_version"] == "compact_decision_v2"
    assert "Evidence-first ranking" in system_prompt
    assert "Do not reward an operator just because it matches the generic task label" in system_prompt
    assert "candidate_operator_ids" not in payload
    assert payload["run"] == {
        "evals_used": 83,
        "evals_left": 120,
        "feasible": "high",
        "pareto": 2,
        "sink_budget": "full",
    }
    assert payload["spatial"] == {
        "hotspot_in_sink": False,
        "hotspot_offset": "left",
        "sink_budget": "full_sink",
    }
    assert payload["generation"] == {
        "accepted": 4,
        "target": 40,
        "dominant": "sink_shift",
        "dominant_share": "high",
    }
    assert payload["operators"][0] == {
        "id": "component_swap_2",
        "task": "global_layout_expand",
        "fit": {"app": "high", "entry": "supported", "preserve": "supported", "expand": "trusted"},
        "evidence": {"frontier": "positive", "pde": "strong", "cheap_skip": "low"},
        "effect": {"peak": "unknown", "grad": "improve"},
        "risk": {"feas": "medium", "recent": "low"},
        "portfolio": "repay_task_debt",
    }


def test_compact_decision_v3_keeps_numeric_operator_evidence_without_candidate_duplication() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="compact_decision_v3",
    )

    payload = json.loads(user_prompt)

    assert payload["prompt_version"] == "compact_decision_v3"
    assert "Evidence-first ranking" in system_prompt
    assert "candidate_operator_ids" not in payload
    assert payload["operators"][0]["evidence"] == {
        "frontier": "positive",
        "pde_n": 10,
        "pde_fr": 0.9,
        "cheap_skip": 0.0,
    }
    assert payload["operators"][0]["risk"] == {"feas": "medium", "recent": "low"}
    assert payload["operators"][0]["portfolio"] == "repay_task_debt"


def test_compact_guided_prompt_uses_structured_system_and_tighter_operator_schema() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="compact_guided",
    )

    payload = json.loads(user_prompt)
    operator_ids = [row["id"] for row in payload["operators"]]

    assert payload["prompt_version"] == "compact_guided"
    assert "## 1. Hard Constraints" in system_prompt
    assert "## 2. Ranking Priorities" in system_prompt
    assert "## 3. Post-Feasible Expand Policy" in system_prompt
    assert operator_ids == ["component_swap_2", "sink_resize"]
    assert "candidate_operator_ids" not in payload
    assert payload["operators"][0]["active_role"] == "component_swap"
    assert payload["operators"][0]["active_pde_n"] == 10
    assert payload["operators"][0]["active_pde_fr"] == 0.9
    assert "role" not in payload["operators"][0]
    assert "pf_role" not in payload["operators"][0]
    assert "pde_n" not in payload["operators"][0]
    assert "pde_fr" not in payload["operators"][0]


def test_compact_core_prompt_preserves_candidates_and_numeric_schema() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="compact_core",
    )

    payload = json.loads(user_prompt)
    operator_ids = [row["id"] for row in payload["operators"]]

    assert payload["prompt_version"] == "compact_core"
    assert operator_ids == ["component_swap_2", "sink_resize"]
    assert payload["decision"]["preferred_effect"] == "gradient_improve"
    assert payload["retrieval"]["positive_families"] == ["stable_global"]
    assert "score, risk, confidence must be numbers in [0,1]" in system_prompt
    assert "parent_panel" not in user_prompt


def test_compact_core_structured_uses_sectioned_system_with_core_user_schema() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="compact_core_structured",
    )

    payload = json.loads(user_prompt)
    first_operator = payload["operators"][0]

    assert payload["prompt_version"] == "compact_core_structured"
    assert "## Output Contract" in system_prompt
    assert "## Ranking Priorities" in system_prompt
    assert "## Policy Hooks" in system_prompt
    assert "candidate_operator_ids" not in payload
    assert first_operator["id"] == "component_swap_2"
    assert first_operator["task"] == "global_layout_expand"
    assert first_operator["pde_n"] == 10
    assert first_operator["pde_fr"] == 0.9
    assert first_operator["pf_pde_n"] == 10
    assert first_operator["pf_pde_fr"] == 0.9
    assert first_operator["role"] == "component_swap"
    assert first_operator["pf_role"] == "component_swap"


def test_compact_core_sectioned_keeps_core_system_semantics_with_sections() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="compact_core_sectioned",
    )

    payload = json.loads(user_prompt)
    first_operator = payload["operators"][0]

    assert payload["prompt_version"] == "compact_core_sectioned"
    assert "## Task" in system_prompt
    assert "## Ranking Criteria" in system_prompt
    assert "## Output" in system_prompt
    assert "bounded hotspot-spread trials" not in system_prompt
    assert "candidate_operator_ids" not in payload
    assert first_operator["id"] == "component_swap_2"
    assert first_operator["pf_pde_n"] == 10
    assert first_operator["pf_role"] == "component_swap"


def test_compact_core_trim_keeps_flat_operator_schema_with_low_risk_field_removal() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="compact_core_trim",
    )

    payload = json.loads(user_prompt)
    first_operator = payload["operators"][0]

    assert payload["prompt_version"] == "compact_core_trim"
    assert "score, risk, confidence must be numbers in [0,1]" in system_prompt
    assert "candidate_operator_ids" not in payload
    assert first_operator["id"] == "component_swap_2"
    assert first_operator["task"] == "global_layout_expand"
    assert first_operator["pde_n"] == 10
    assert first_operator["pde_fr"] == 0.9
    assert first_operator["cheap_skip"] == 0.0
    assert "pf_pde_n" not in first_operator
    assert "pf_pde_fr" not in first_operator
    assert "pf_cheap_skip" not in first_operator
    assert "role" not in first_operator
    assert "pf_role" not in first_operator


def test_original_prompt_variant_returns_saved_prompt_unchanged() -> None:
    system_prompt, user_prompt = replay.build_compacted_prompt(
        _request_row(),
        variant="original",
    )

    assert system_prompt == "original system"
    assert user_prompt == _request_row()["user_prompt"]


def test_select_representative_rows_prioritizes_positive_gain_and_operator_diversity() -> None:
    rows = replay.select_representative_rows(
        request_rows=[
            {"decision_id": "d1", "user_prompt": "{}", "system_prompt": "", "candidate_operator_ids": []},
            {"decision_id": "d2", "user_prompt": "{}", "system_prompt": "", "candidate_operator_ids": []},
            {"decision_id": "d3", "user_prompt": "{}", "system_prompt": "", "candidate_operator_ids": []},
        ],
        response_rows={
            "d1": {"selected_operator_id": "component_swap_2", "selected_rank": 1},
            "d2": {"selected_operator_id": "component_swap_2", "selected_rank": 1},
            "d3": {"selected_operator_id": "sink_resize", "selected_rank": 1},
        },
        outcome_rows={
            "d1": {"hypervolume_gain": "1.0", "improved_hypervolume": "True", "applied": "True"},
            "d2": {"hypervolume_gain": "3.0", "improved_hypervolume": "True", "applied": "True"},
            "d3": {"hypervolume_gain": "2.0", "improved_hypervolume": "True", "applied": "True"},
        },
        max_rows=2,
    )

    assert [row["decision_id"] for row in rows] == ["d2", "d3"]


def test_replay_rows_parallelism_preserves_report_order() -> None:
    request_rows = [
        _joined_request_row("d1", "component_swap_2"),
        _joined_request_row("d2", "sink_resize"),
        _joined_request_row("d3", "component_swap_2"),
    ]

    def fake_request_operator_rank_advice(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        operator_id = payload["operators"][0]["id"]
        return SimpleNamespace(
            ranked_operators=[SimpleNamespace(operator_id=operator_id)]
        )

    report = replay.replay_rows(
        request_rows,
        variants=["compact_guided"],
        controller_parameters={},
        live=True,
        parallelism=3,
        request_operator_rank_advice=fake_request_operator_rank_advice,
    )

    assert [row["decision_id"] for row in report["rows"]] == ["d1", "d2", "d3"]
    assert report["summary"]["compact_guided"]["valid_count"] == 3
    assert report["summary"]["compact_guided"]["operator_match_count"] == 2


def _joined_request_row(decision_id: str, baseline_operator: str) -> dict:
    row = _request_row()
    row["decision_id"] = decision_id
    row["_baseline_response"] = {
        "selected_operator_id": baseline_operator,
        "selected_rank": 1,
        "phase": "post_feasible_expand",
        "llm_ranked_operators": [{"operator_id": baseline_operator}],
    }
    row["_outcome"] = {
        "hypervolume_gain": "1.0",
        "improved_hypervolume": "True",
        "applied": "True",
    }
    return row


def _request_row() -> dict:
    return {
        "decision_id": "d1",
        "system_prompt": "original system",
        "user_prompt": json.dumps(
            {
                "family": "genetic",
                "backbone": "nsga2",
                "generation_index": 3,
                "evaluation_index": 83,
                "candidate_operator_ids": ["component_swap_2", "sink_resize"],
                "metadata": {
                    "decision_axes": {
                        "primary_objective": "frontier_expand",
                        "preferred_effect": "gradient_improve",
                        "semantic_task_debts": ["global_layout_expand"],
                        "semantic_task_saturations": ["sink_alignment"],
                    },
                    "phase_policy": {
                        "phase": "post_feasible_expand",
                        "reason_codes": ["post_feasible_semantic_portfolio_debt"],
                        "reset_active": False,
                    },
                    "decision_guardrail": {
                        "discouraged_operator_ids": ["sink_shift"],
                        "dominant_operator_id": "sink_shift",
                        "dominant_operator_share": 0.8,
                    },
                    "prompt_panels": {
                        "run_panel": {
                            "evaluations_used": 83,
                            "evaluations_remaining": 120,
                            "feasible_rate": 0.8,
                            "pareto_size": 2,
                            "peak_temperature": 320.0,
                            "temperature_gradient_rms": 14.0,
                            "sink_budget_utilization": 1.0,
                        },
                        "spatial_panel": {
                            "hotspot_inside_sink_window": False,
                            "hotspot_to_sink_offset": -0.1,
                            "sink_budget_bucket": "full_sink",
                        },
                        "retrieval_panel": {
                            "positive_match_families": ["stable_global"],
                            "negative_match_families": ["stable_local"],
                            "visibility_floor_families": ["stable_global", "stable_local"],
                            "positive_matches": [
                                {
                                    "operator_id": "component_swap_2",
                                    "route_family": "stable_global",
                                    "similarity_score": 6,
                                }
                            ],
                        },
                        "generation_panel": {
                            "accepted_count": 4,
                            "target_offsprings": 40,
                            "dominant_operator_id": "sink_shift",
                            "dominant_operator_share": 0.75,
                        },
                        "semantic_task_panel": {
                            "active_bottleneck": "sink_misaligned_hotspot",
                            "recommended_task_order": ["global_layout_expand", "sink_budget_shape"],
                        },
                        "parent_panel": {"strongest_feasible_parent": {"evaluation_index": 1}},
                        "operator_panel": {
                            "columns": [
                                "operator_id",
                                "applicability",
                                "entry_fit",
                                "preserve_fit",
                                "expand_fit",
                                "frontier_evidence",
                                "expected_gradient_effect",
                                "expected_feasibility_risk",
                                "recent_regression_risk",
                                "pde_attempt_count",
                                "pde_feasible_rate",
                                "cheap_skip_rate",
                                "post_feasible_pde_attempt_count",
                                "post_feasible_pde_feasible_rate",
                                "post_feasible_cheap_skip_rate",
                                "role",
                                "post_feasible_role",
                                "semantic_task",
                                "portfolio_priority",
                            ],
                            "rows": [
                                [
                                    "component_swap_2",
                                    "high",
                                    "supported",
                                    "supported",
                                    "trusted",
                                    "positive",
                                    "improve",
                                    "medium",
                                    "low",
                                    10,
                                    0.9,
                                    0.0,
                                    10,
                                    0.9,
                                    0.0,
                                    "component_swap",
                                    "component_swap",
                                    "global_layout_expand",
                                    "repay_task_debt",
                                ],
                                [
                                    "sink_resize",
                                    "medium",
                                    "weak",
                                    "supported",
                                    "limited",
                                    "limited",
                                    "neutral",
                                    "high",
                                    "medium",
                                    5,
                                    0.8,
                                    0.1,
                                    5,
                                    0.8,
                                    0.1,
                                    "sink_resize",
                                    "sink_resize",
                                    "sink_budget_shape",
                                    "neutral",
                                ],
                            ],
                        },
                    },
                },
            },
            separators=(",", ":"),
        ),
        "candidate_operator_ids": ["component_swap_2", "sink_resize"],
    }
