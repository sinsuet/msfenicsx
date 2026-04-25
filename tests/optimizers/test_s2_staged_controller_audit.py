from __future__ import annotations

import json
from pathlib import Path

import pytest

from optimizers.analytics.staged_audit import (
    compare_history_prefix_by_mode,
    summarize_llm_prompt_surface,
    summarize_prompt_chain_progress,
    summarize_prompt_contract_mismatches,
    summarize_unique_llm_decisions,
)


def _write_optimization_result(path: Path, history: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"history": history}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _history_row(
    evaluation_index: int,
    *,
    feasible: bool,
    source: str = "optimizer",
    peak: float = 330.0,
    gradient: float = 12.0,
    c02: float = 0.0,
) -> dict[str, object]:
    return {
        "evaluation_index": evaluation_index,
        "source": source,
        "feasible": feasible,
        "decision_vector": {"x0": float(evaluation_index), "x1": float(evaluation_index) / 10.0},
        "objective_values": {
            "minimize_peak_temperature": peak,
            "minimize_temperature_gradient_rms": gradient,
        },
        "constraint_values": {
            "c02_peak_temperature_limit": c02,
            "radiator_span_budget": 0.0,
        },
    }


def _prompt_markdown(user_payload: dict[str, object], *, decision_id: str) -> str:
    return (
        "---\n"
        "kind: request\n"
        f"decision_ids: [{decision_id}]\n"
        "---\n\n"
        "# System\n\n"
        "stub system\n\n"
        "# User\n\n"
        f"{json.dumps(user_payload, ensure_ascii=True)}\n"
    )


def _load_jsonl_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_compare_history_prefix_by_mode_reports_shared_rows_and_first_divergence(tmp_path: Path) -> None:
    shared_prefix = [
        _history_row(1, feasible=False, source="baseline", c02=2.8),
        _history_row(2, feasible=False, c02=4.0),
        _history_row(3, feasible=False, c02=3.2),
    ]
    raw_history = [*shared_prefix, _history_row(4, feasible=False, peak=329.1, gradient=13.2)]
    union_history = [*shared_prefix, _history_row(4, feasible=True, peak=327.4, gradient=12.9)]
    llm_history = [*shared_prefix, _history_row(4, feasible=True, peak=326.8, gradient=12.5)]

    roots = {
        "raw": tmp_path / "raw",
        "union": tmp_path / "union",
        "llm": tmp_path / "llm",
    }
    _write_optimization_result(roots["raw"] / "optimization_result.json", raw_history)
    _write_optimization_result(roots["union"] / "optimization_result.json", union_history)
    _write_optimization_result(roots["llm"] / "optimization_result.json", llm_history)

    summary = compare_history_prefix_by_mode(roots, prefix_rows=4)

    assert summary["shared_prefix_identical"] is False
    assert summary["first_divergence_history_row"] == 4
    assert summary["first_feasible_eval_by_mode"] == {"raw": None, "union": 4, "llm": 4}
    assert summary["shared_prefix_rows"][0]["history_row"] == 1
    assert summary["shared_prefix_rows"][2]["history_row"] == 3
    assert summary["shared_prefix_rows"][2]["matches_all_modes"] is True
    assert summary["shared_prefix_rows"][3]["matches_all_modes"] is False


def test_summarize_prompt_contract_mismatches_reports_current_0421_llm_breaks() -> None:
    trace_path = _repo_root() / "scenario_runs" / "s2_staged" / "0421_0207__llm" / "traces" / "llm_request_trace.jsonl"
    rows = _load_jsonl_rows(trace_path)

    summary = summarize_prompt_contract_mismatches(rows)

    assert summary["phase_mismatch_count"] == 146
    assert summary["hidden_positive_match_requests"] == 101
    assert summary["hidden_positive_match_family_counts"] == {
        "budget_guard": 41,
        "sink_retarget": 4,
        "stable_global": 19,
        "stable_local": 60,
    }
    assert summary["hidden_positive_credit_requests"] == 0
    assert summary["hidden_positive_credit_family_counts"] == {}
    assert summary["recover_pool_size_summary"]["count"] == 131
    assert summary["recover_pool_size_summary"]["min"] == 1
    assert summary["recover_pool_size_summary"]["max"] == 4
    assert summary["recover_pool_size_summary"]["avg"] == pytest.approx(2.954198473282443)


def test_summarize_prompt_contract_mismatches_reports_hidden_positive_match_families_in_latest_0421_llm_trace() -> None:
    trace_path = _repo_root() / "scenario_runs" / "s2_staged" / "0421_1434__llm" / "traces" / "llm_request_trace.jsonl"
    rows = _load_jsonl_rows(trace_path)

    summary = summarize_prompt_contract_mismatches(rows)

    assert summary["hidden_positive_match_requests"] == 20
    assert summary["hidden_positive_match_family_counts"] == {
        "sink_retarget": 1,
        "stable_global": 14,
        "stable_local": 6,
    }
    assert summary["hidden_positive_credit_requests"] == 0
    assert summary["hidden_positive_credit_family_counts"] == {}


def test_summarize_prompt_contract_mismatches_examples_expose_recover_retrieval_drift() -> None:
    trace_path = _repo_root() / "scenario_runs" / "s2_staged" / "0421_0207__llm" / "traces" / "llm_request_trace.jsonl"
    rows = _load_jsonl_rows(trace_path)

    summary = summarize_prompt_contract_mismatches(rows)

    recover_example = next(
        example
        for example in summary["phase_mismatch_examples"]
        if example["policy_phase"] == "post_feasible_recover"
    )
    assert recover_example["retrieval_phase"] == "post_feasible_preserve"
    assert recover_example["phase_fallbacks"] == []
    assert recover_example["decision_id"] == "g004-e0062-d31"


def test_summarize_unique_llm_decisions_deduplicates_controller_rows() -> None:
    controller_rows = [
        {
            "decision_id": "g002-e0022-d00",
            "evaluation_index": 22,
            "phase": "post_feasible_recover",
            "policy_phase": "post_feasible_recover",
        },
        {
            "decision_id": "g002-e0022-d00",
            "evaluation_index": 23,
            "phase": "post_feasible_recover",
            "policy_phase": "post_feasible_recover",
        },
        {
            "decision_id": "g002-e0024-d01",
            "evaluation_index": 24,
            "phase": "feasible_refine",
            "policy_phase": "feasible_refine",
        },
    ]

    summary = summarize_unique_llm_decisions(controller_rows)

    assert summary["raw_row_count"] == 3
    assert summary["unique_decision_count"] == 2
    assert summary["duplicate_row_count"] == 1
    assert summary["policy_phase_counts"] == {
        "post_feasible_recover": 1,
        "feasible_refine": 1,
    }
    assert summary["first_decision_id"] == "g002-e0022-d00"
    assert summary["last_decision_id"] == "g002-e0024-d01"


def test_summarize_llm_prompt_surface_reports_effective_pool_and_gradient_visibility() -> None:
    user_payload = {
        "metadata": {
            "decision_axes": {
                "semantic_trial_mode": "none",
                "route_family_mode": "recover_family_mix",
            },
            "decision_guardrail": {
                "original_candidate_operator_ids": [
                    "native_sbx_pm",
                    "local_refine",
                    "smooth_high_gradient_band",
                    "reduce_local_congestion",
                ],
                "effective_candidate_operator_ids": [
                    "local_refine",
                    "smooth_high_gradient_band",
                ],
                "filtered_operator_ids": [
                    "native_sbx_pm",
                    "reduce_local_congestion",
                ],
            },
            "prompt_panels": {
                "regime_panel": {
                    "objective_balance": {"preferred_effect": "gradient_improve"},
                },
                "operator_panel": {
                    "local_refine": {"applicability": "high"},
                    "smooth_high_gradient_band": {"applicability": "high"},
                },
            },
        }
    }
    rows = [
        {
            "decision_id": "g002-e0022-d00",
            "user_prompt": json.dumps(user_payload, ensure_ascii=True),
        }
    ]

    summary = summarize_llm_prompt_surface(rows)

    assert summary["request_count"] == 1
    assert summary["effective_pool_size"]["min"] == 2
    assert summary["effective_pool_size"]["max"] == 2
    assert summary["route_family_mode_counts"] == {"recover_family_mix": 1}
    assert summary["semantic_trial_mode_counts"] == {"none": 1}
    assert summary["visible_route_family_counts"]["congestion_relief"] == 1
    assert summary["filtered_route_family_counts"]["congestion_relief"] == 1
    assert summary["gradient_improve"]["request_count"] == 1
    assert summary["gradient_improve"]["with_congestion_relief_visible_count"] == 1


def test_summarize_llm_prompt_surface_can_read_prompt_store_markdown_via_prompt_ref(tmp_path: Path) -> None:
    prompt_root = tmp_path / "run"
    prompt_path = prompt_root / "prompts" / "abc123.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        _prompt_markdown(
            {
                "metadata": {
                    "decision_axes": {
                        "semantic_trial_mode": "encourage_bounded_trial",
                        "route_family_mode": "bounded_expand_mix",
                    },
                    "decision_guardrail": {
                        "original_candidate_operator_ids": [
                            "native_sbx_pm",
                            "spread_hottest_cluster",
                            "reduce_local_congestion",
                        ],
                        "effective_candidate_operator_ids": [
                            "spread_hottest_cluster",
                        ],
                        "filtered_operator_ids": [
                            "native_sbx_pm",
                            "reduce_local_congestion",
                        ],
                    },
                    "prompt_panels": {
                        "regime_panel": {
                            "objective_balance": {"preferred_effect": "gradient_improve"},
                        },
                        "operator_panel": {
                            "spread_hottest_cluster": {"applicability": "high"},
                        },
                    },
                }
            },
            decision_id="g003-e0042-d00",
        ),
        encoding="utf-8",
    )
    rows = [
        {
            "decision_id": "g003-e0042-d00",
            "prompt_ref": "prompts/abc123.md",
        }
    ]

    summary = summarize_llm_prompt_surface(rows, run_root=prompt_root)

    assert summary["request_count"] == 1
    assert summary["route_family_mode_counts"]["bounded_expand_mix"] == 1
    assert summary["semantic_trial_mode_counts"]["encourage_bounded_trial"] == 1
    assert summary["effective_pool_size"]["min"] == 1
    assert summary["gradient_improve"]["with_congestion_relief_visible_count"] == 0


def test_summarize_llm_prompt_surface_prefers_request_side_fields_without_prompt_reparse() -> None:
    rows = [
        {
            "decision_id": "g004-e0061-d00",
            "original_candidate_pool_size": 4,
            "effective_candidate_pool_size": 2,
            "visible_route_families": ["stable_local", "congestion_relief"],
            "filtered_route_families": ["sink_retarget"],
            "route_family_mode": "recover_family_mix",
            "semantic_trial_mode": "encourage_bounded_trial",
            "preferred_effect": "gradient_improve",
        }
    ]

    summary = summarize_llm_prompt_surface(rows)

    assert summary["request_count"] == 1
    assert summary["original_pool_size"]["min"] == 4
    assert summary["effective_pool_size"]["max"] == 2
    assert summary["route_family_mode_counts"] == {"recover_family_mix": 1}
    assert summary["semantic_trial_mode_counts"] == {"encourage_bounded_trial": 1}
    assert summary["visible_route_family_counts"]["congestion_relief"] == 1
    assert summary["filtered_route_family_counts"]["sink_retarget"] == 1
    assert summary["gradient_improve"]["with_congestion_relief_visible_count"] == 1


def test_summarize_prompt_chain_progress_tracks_convert_and_phase_occupancy() -> None:
    rows = [
        {
            "decision_id": "g003-e0042-d15",
            "policy_phase": "prefeasible_convert",
            "route_family_mode": "convert_family_mix",
            "semantic_trial_mode": "encourage_bounded_trial",
            "effective_candidate_pool_size": 4,
            "visible_route_families": ["stable_local", "budget_guard"],
            "user_prompt": json.dumps(
                {
                    "metadata": {
                        "prompt_panels": {
                            "retrieval_panel": {
                                "route_family_credit": {
                                    "positive_families": ["budget_guard"],
                                    "negative_families": [],
                                }
                            }
                        }
                    }
                },
                ensure_ascii=True,
            ),
        },
        {
            "decision_id": "g004-e0062-d31",
            "policy_phase": "post_feasible_recover",
            "route_family_mode": "recover_family_mix",
            "semantic_trial_mode": "none",
            "effective_candidate_pool_size": 3,
            "visible_route_families": ["stable_local"],
            "user_prompt": json.dumps(
                {
                    "metadata": {
                        "prompt_panels": {
                            "retrieval_panel": {
                                "route_family_credit": {
                                    "positive_families": ["stable_local"],
                                    "negative_families": [],
                                }
                            }
                        }
                    }
                },
                ensure_ascii=True,
            ),
        },
        {
            "decision_id": "g004-e0064-d32",
            "policy_phase": "post_feasible_preserve",
            "route_family_mode": "preserve_family_mix",
            "semantic_trial_mode": "encourage_bounded_trial",
            "effective_candidate_pool_size": 4,
            "visible_route_families": ["stable_local", "congestion_relief"],
        },
        {
            "decision_id": "g004-e0066-d33",
            "policy_phase": "post_feasible_expand",
            "route_family_mode": "bounded_expand_mix",
            "semantic_trial_mode": "encourage_bounded_trial",
            "effective_candidate_pool_size": 5,
            "visible_route_families": ["layout_rebalance", "hotspot_spread"],
        },
    ]

    summary = summarize_prompt_chain_progress(rows)

    assert summary["phase_counts"] == {
        "prefeasible_convert": 1,
        "post_feasible_recover": 1,
        "post_feasible_preserve": 1,
        "post_feasible_expand": 1,
    }
    assert summary["convert_route_family_mode_counts"] == {"convert_family_mix": 1}
    assert summary["convert_semantic_trial_mode_counts"] == {"encourage_bounded_trial": 1}
    assert summary["recover_pool_size_summary"]["count"] == 1
    assert summary["recover_pool_size_summary"]["min"] == 3
    assert summary["recover_pool_size_summary"]["max"] == 3
    assert summary["hidden_positive_credit_family_counts"] == {}


def test_summarize_prompt_chain_progress_reports_hidden_handoff_credit() -> None:
    rows = [
        {
            "decision_id": "g005-e0070-d40",
            "policy_phase": "post_feasible_recover",
            "route_family_mode": "recover_family_mix",
            "semantic_trial_mode": "none",
            "effective_candidate_pool_size": 2,
            "visible_route_families": ["stable_global"],
            "user_prompt": json.dumps(
                {
                    "metadata": {
                        "prompt_panels": {
                            "retrieval_panel": {
                                "route_family_credit": {
                                    "positive_families": ["stable_local"],
                                    "negative_families": [],
                                }
                            }
                        }
                    }
                },
                ensure_ascii=True,
            ),
        }
    ]

    summary = summarize_prompt_chain_progress(rows)

    assert summary["phase_counts"] == {"post_feasible_recover": 1}
    assert summary["convert_route_family_mode_counts"] == {}
    assert summary["convert_semantic_trial_mode_counts"] == {}
    assert summary["recover_pool_size_summary"]["count"] == 1
    assert summary["hidden_positive_credit_family_counts"] == {"stable_local": 1}
