# S2 Staged Phase-2 Chain Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the remaining `s2_staged` controller-chain faults so current positive retrieval matches survive into the visible pool, recover can release under bounded regression, and expand can activate before diversity has already plateaued.

**Architecture:** Keep the shared operator registry unchanged and continue repairing only controller-side contracts. Split long-horizon family credit from current-match visibility floors, separate recover release from recover reentry pressure, and replace single-point expand admission with a diversity-deficit contract. Verify each layer with TDD, then rerun the official `llm` route with the stable `nohup + poll` execution path.

**Tech Stack:** Python 3.12, pytest, JSONL traces, `msfenicsx` conda env, existing `render-assets` and `compare-runs` pipeline.

---

## File Structure

### Primary implementation files

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Modify: `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

### Primary focused tests

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`

### Verification gate

- Run:
  - `/home/hymn/msfenicsx/tests/generator/test_s2_staged_template.py`
  - `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_baseline.py`
  - `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
  - `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
  - `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
  - `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`

### Rerun and artifact targets

- Old official suite:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm`
- Latest checked `llm` evidence before this cycle:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0421_1434__llm`
- Latest checked compare bundle before this cycle:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_1456__raw_union_old_vs_llm_expand_fix`

## Task 1: Lock The Match-Level Visibility Failure In Tests

**Files:**

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

- [ ] **Step 1: Write a failing audit test for hidden positive matches in the latest live trace**

```python
def test_summarize_prompt_contract_mismatches_reports_hidden_positive_match_families() -> None:
    request_rows = _load_request_rows(
        "/home/hymn/msfenicsx/scenario_runs/s2_staged/0421_1434__llm/traces/llm_request_trace.jsonl"
    )

    summary = summarize_prompt_contract_mismatches(request_rows)

    assert summary["hidden_positive_match_requests"] == 0
    assert summary["hidden_positive_match_family_counts"] == {}
```

- [ ] **Step 2: Write a failing state-level test for a mixed-sign family with a live positive match**

```python
def test_retrieval_panel_exposes_visibility_floor_from_positive_matches_even_when_family_credit_is_mixed() -> None:
    retrieval_panel = _build_retrieval_panel(
        operator_summary={
            "native_sbx_pm": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 0,
                        "feasible_regression_count": 1,
                        "penalty_event_count": 0,
                        "avg_objective_delta": 0.05,
                        "avg_total_violation_delta": 0.02,
                    }
                }
            },
            "local_refine": {
                "credit_by_regime": {
                    ("post_feasible_recover", "thermal_limit", "tight"): {
                        "frontier_add_count": 0,
                        "feasible_preservation_count": 1,
                        "feasible_regression_count": 1,
                        "penalty_event_count": 0,
                        "avg_objective_delta": -0.01,
                        "avg_total_violation_delta": -0.03,
                    }
                }
            },
        },
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
        regime_panel={"phase": "post_feasible_recover", "dominant_violation_family": "thermal_limit"},
        spatial_panel={"sink_budget_bucket": "tight"},
    )

    assert retrieval_panel["positive_match_families"] == ["stable_local"]
    assert retrieval_panel["visibility_floor_families"] == ["stable_local"]
```

- [ ] **Step 3: Run the failing audit/state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_s2_staged_controller_audit.py \
tests/optimizers/test_llm_controller_state.py \
-k "hidden_positive_match or visibility_floor" -v
```

Expected:

- FAIL because current audit helper does not distinguish match-level hidden families
- FAIL because retrieval panel does not emit explicit visibility-floor families

- [ ] **Step 4: Implement explicit match-level visibility-floor audit fields**

Add to `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`:

```python
{
    "hidden_positive_match_requests": hidden_positive_match_requests,
    "hidden_positive_match_family_counts": dict(hidden_positive_match_family_counts),
    "hidden_positive_credit_requests": hidden_positive_credit_requests,
    "hidden_positive_credit_family_counts": dict(hidden_positive_credit_family_counts),
}
```

Implement with these rules:

- `positive_matches` and current-match families drive the new `match` fields
- long-horizon aggregated `route_family_credit.positive_families` continue to drive the `credit` fields
- the helper must not rename one concept to the other

- [ ] **Step 5: Implement explicit retrieval-panel visibility floors**

In `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`, extend the retrieval panel with:

```python
positive_match_families = sorted({
    str(match["route_family"]).strip()
    for match in positive_matches
    if str(match.get("route_family", "")).strip()
})

negative_match_families = sorted({
    str(match["route_family"]).strip()
    for match in negative_matches
    if str(match.get("route_family", "")).strip()
})

visibility_floor_families = sorted({
    *positive_match_families,
    *handoff_families,
})
```

- [ ] **Step 6: Re-run the audit/state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_s2_staged_controller_audit.py \
tests/optimizers/test_llm_controller_state.py \
-k "hidden_positive_match or visibility_floor" -v
```

Expected:

- PASS

## Task 2: Restore Match-Level Visibility Floors In Policy And Trace Metadata

**Files:**

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write a failing policy test for mixed aggregate credit with a live positive match**

```python
def test_recover_restores_visibility_floor_family_even_when_aggregate_credit_is_not_positive() -> None:
    policy = build_policy_snapshot(
        _post_feasible_recover_visibility_floor_state(),
        ("native_sbx_pm", "global_explore", "local_refine", "move_hottest_cluster_toward_sink"),
    )

    assert "local_refine" in policy.allowed_operator_ids
```

- [ ] **Step 2: Write a failing controller-trace test for visibility-floor telemetry**

```python
def test_llm_controller_request_trace_records_visibility_floor_families(tmp_path: Path) -> None:
    controller = _build_fake_controller(tmp_path)

    controller.select_decision(
        _visibility_floor_state(),
        ("native_sbx_pm", "global_explore", "local_refine", "move_hottest_cluster_toward_sink"),
        np.random.default_rng(41),
    )

    request_entry = controller.request_trace[0]
    assert request_entry["visibility_floor_families"] == ["stable_local"]
```

- [ ] **Step 3: Run the failing policy/controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_llm_policy_kernel.py \
tests/optimizers/test_llm_controller.py \
-k "visibility_floor" -v
```

Expected:

- FAIL because the policy currently restores mainly from aggregated positive families plus handoff only

- [ ] **Step 4: Restore visibility from current-match floors first**

Update `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py` so
`_restore_positive_route_family_visibility(...)` uses:

```python
visibility_floor_families = {
    str(route_family).strip()
    for route_family in retrieval_panel.get("visibility_floor_families", [])
    if str(route_family).strip()
}

positive_visibility_families = (
    visibility_floor_families
    | (positive_families - negative_families)
    | handoff_families
)
```

Contract:

- `visibility_floor_families` always win visibility restoration in recover/preserve
- long-horizon mixed-sign aggregates may still affect ranking within a family, but not whether the family is visible at all

- [ ] **Step 5: Surface visibility-floor telemetry in request traces**

Update `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py` to emit:

```python
"positive_match_families": [str(route_family) for route_family in retrieval_panel.get("positive_match_families", [])],
"visibility_floor_families": [str(route_family) for route_family in retrieval_panel.get("visibility_floor_families", [])],
```

- [ ] **Step 6: Re-run the policy/controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_llm_policy_kernel.py \
tests/optimizers/test_llm_controller.py \
-k "visibility_floor" -v
```

Expected:

- PASS

## Task 3: Separate Recover Release From Recover Reentry Pressure

**Files:**

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write a failing state test for bounded-regression recover release**

```python
def test_build_progress_state_sets_recover_release_ready_when_preserve_signal_offsets_bounded_regression() -> None:
    progress = build_progress_state(history=history_with_two_regressions_and_two_preservations)

    assert progress["recover_pressure_level"] == "medium"
    assert progress["recover_release_ready"] is True
```

- [ ] **Step 2: Write a failing policy test for recover-to-preserve release under medium pressure**

```python
def test_detect_search_phase_uses_recover_release_ready_even_when_reentry_pressure_is_medium() -> None:
    policy = build_policy_snapshot(
        _recover_release_ready_state(),
        ("native_sbx_pm", "global_explore", "local_refine"),
    )

    assert policy.phase == "post_feasible_preserve"
```

- [ ] **Step 3: Write a failing controller trace test for the new release signal**

```python
def test_llm_controller_request_trace_records_recover_release_ready(tmp_path: Path) -> None:
    controller = _build_fake_controller(tmp_path)

    controller.select_decision(
        _recover_release_ready_controller_state(),
        ("native_sbx_pm", "local_refine", "global_explore"),
        np.random.default_rng(17),
    )

    request_entry = controller.request_trace[0]
    assert request_entry["recover_release_ready"] is True
```

- [ ] **Step 4: Run the failing recover tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_llm_controller_state.py \
tests/optimizers/test_llm_policy_kernel.py \
tests/optimizers/test_llm_controller.py \
-k "recover_release_ready" -v
```

Expected:

- FAIL because the current contract still ties release to `recover_pressure_level == low`

- [ ] **Step 5: Add `recover_release_ready` to progress state**

Implement in `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`:

```python
regression_surplus = max(0, recent_feasible_regression_count - recent_feasible_preservation_count)
recover_release_ready = (
    preserve_dwell_signal > 0
    and regression_surplus <= 1
)
```

Keep:

- `recover_reentry_pressure` as the risk signal
- `recover_pressure_level` as the coarse pressure bucket

but stop using them as the only release decision.

- [ ] **Step 6: Consume the new release signal in policy and request traces**

Update:

- `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
  - `_post_feasible_recover_exit_ready(...)` should prefer `recover_release_ready`
- `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
  - request traces should expose `recover_release_ready`

- [ ] **Step 7: Re-run the recover tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_llm_controller_state.py \
tests/optimizers/test_llm_policy_kernel.py \
tests/optimizers/test_llm_controller.py \
-k "recover_release_ready" -v
```

Expected:

- PASS

## Task 4: Replace Single-Point Expand Gating With Diversity Deficit

**Files:**

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write a failing state test for diversity deficit**

```python
def test_build_progress_state_sets_diversity_deficit_medium_for_two_point_stagnant_front() -> None:
    progress = build_progress_state(history=history_with_two_point_front_and_frontier_stagnation)

    assert progress["diversity_deficit_level"] == "medium"
```

- [ ] **Step 2: Write a failing policy test for expand promotion under bounded regression**

```python
def test_preserve_state_promotes_to_expand_when_diversity_deficit_is_medium_and_regression_is_bounded() -> None:
    policy = build_policy_snapshot(
        _post_feasible_preserve_diversity_deficit_state(),
        ("native_sbx_pm", "local_refine", "spread_hottest_cluster", "reduce_local_congestion"),
    )

    assert policy.phase == "post_feasible_expand"
```

- [ ] **Step 3: Write a failing policy test for saturation demotion only after diversity deficit cools**

```python
def test_expand_saturation_does_not_demote_while_diversity_deficit_remains_medium() -> None:
    policy = build_policy_snapshot(
        _post_feasible_expand_saturated_medium_diversity_deficit_state(),
        ("native_sbx_pm", "local_refine", "spread_hottest_cluster", "smooth_high_gradient_band"),
    )

    assert policy.phase == "post_feasible_expand"
```

- [ ] **Step 4: Run the failing expand tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_llm_controller_state.py \
tests/optimizers/test_llm_policy_kernel.py \
-k "diversity_deficit or saturated_medium" -v
```

Expected:

- FAIL because current expand admission still requires `pareto_size <= 1` plus zero regression

- [ ] **Step 5: Add `diversity_deficit_level` to progress state**

In `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`, derive:

```python
if int(frontier_summary["pareto_size"]) <= 1:
    diversity_deficit_level = "high"
elif (
    int(frontier_summary["pareto_size"]) == 2
    and int(frontier_summary["recent_frontier_stagnation_count"]) >= 2
):
    diversity_deficit_level = "medium"
else:
    diversity_deficit_level = "low"
```

- [ ] **Step 6: Update expand promotion and saturation rules**

In `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`, change the expand contract to:

```python
regression_surplus = max(
    0,
    int(archive_state.get("recent_feasible_regression_count", 0))
    - int(archive_state.get("recent_feasible_preservation_count", 0)),
)

expand_allowed = (
    diversity_deficit_level in {"high", "medium"}
    and regression_surplus <= 0
)

expand_saturated = (
    expand_saturation_count >= _EXPAND_SATURATION_THRESHOLD
    and diversity_deficit_level == "low"
)
```

- [ ] **Step 7: Surface the new diversity signal in request traces**

Update `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py` to emit:

```python
"diversity_deficit_level": str(regime_panel.get("diversity_deficit_level", "low")),
```

- [ ] **Step 8: Re-run the expand tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/optimizers/test_llm_controller_state.py \
tests/optimizers/test_llm_policy_kernel.py \
-k "diversity_deficit or saturated_medium" -v
```

Expected:

- PASS

## Task 5: Run The Full Focused Verification Gate

**Files:**

- No new code expected

- [ ] **Step 1: Run the required focused test set**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/generator/test_s2_staged_template.py \
tests/optimizers/test_s2_staged_baseline.py \
tests/optimizers/test_s2_staged_controller_audit.py \
tests/optimizers/test_llm_policy_kernel.py \
tests/optimizers/test_llm_controller.py \
tests/optimizers/test_llm_controller_state.py \
-v
```

Expected:

- PASS on all focused tests

- [ ] **Step 2: If the gate fails, return only to the owning task**

Allowed next action:

- fix only the failing contract

Not allowed:

- start the official rerun with a known red focused gate

## Task 6: Run The New Official `s2_staged` `llm` Rerun And Rebuild Evidence

**Files:**

- Output only under `/home/hymn/msfenicsx/scenario_runs/s2_staged/`
- Output only under `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/`

- [ ] **Step 1: Launch the new official rerun with `nohup`**

Run:

```bash
NEW_RUN="/home/hymn/msfenicsx/scenario_runs/s2_staged/$(date +%m%d_%H%M)__llm"
PID_FILE="/tmp/$(basename "$NEW_RUN").pid"
nohup /home/hymn/miniconda3/bin/conda run -n msfenicsx \
python -m optimizers.cli optimize-benchmark \
--optimization-spec /home/hymn/msfenicsx/scenarios/optimization/s2_staged_llm.yaml \
--evaluation-workers 2 \
--output-root "$NEW_RUN" \
>"/tmp/$(basename "$NEW_RUN").log" 2>&1 &
echo $! > "$PID_FILE"
cat "$PID_FILE"
```

Expected:

- one background PID saved to `"$PID_FILE"`
- a new canonical `__llm` run root under `scenario_runs/s2_staged/`

- [ ] **Step 2: Poll until the PID exits and verify the run completed**

Run:

```bash
PID="$(cat "$PID_FILE")"
while ps -p "$PID" > /dev/null; do sleep 30; done
test -f "$NEW_RUN/run.yaml"
test -f "$NEW_RUN/analytics/progress_timeline.csv"
```

Expected:

- both file checks succeed

- [ ] **Step 3: Render assets for the completed run**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx \
python -m optimizers.cli render-assets \
--run "$NEW_RUN"
```

Expected:

- fresh `analytics/` and `figures/` under the new run root

- [ ] **Step 4: Build the external compare bundle**

Run:

```bash
COMPARE_OUT="/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/$(date +%m%d_%H%M)__raw_union_old_vs_llm_phase2_chain_release"
/home/hymn/miniconda3/bin/conda run -n msfenicsx \
python -m optimizers.cli compare-runs \
--run /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11 \
--run /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11 \
--run "$NEW_RUN" \
--output "$COMPARE_OUT"
```

Expected:

- a new compare bundle outside the source runs

- [ ] **Step 5: Re-audit the new request trace for the chain outcomes**

Run:

```bash
export NEW_RUN
/home/hymn/miniconda3/bin/conda run -n msfenicsx python - <<'PY'
import json
import os
from pathlib import Path
from optimizers.analytics.staged_audit import (
    summarize_prompt_chain_progress,
    summarize_prompt_contract_mismatches,
)

run_root = Path(os.environ["NEW_RUN"])
rows = [json.loads(line) for line in (run_root / "traces" / "llm_request_trace.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
print(json.dumps(summarize_prompt_chain_progress(rows), indent=2))
print(json.dumps(summarize_prompt_contract_mismatches(rows), indent=2))
PY
```

Expected:

- `hidden_positive_match_requests == 0`
- non-zero `post_feasible_preserve`
- non-zero `post_feasible_expand`

- [ ] **Step 6: Re-answer the paper-facing questions from fresh artifacts only**

Answer from:

- `$NEW_RUN/analytics/progress_timeline.csv`
- `$COMPARE_OUT/analytics/summary_rows.json`
- `$COMPARE_OUT/analytics/timeline_rollups.json`
- the audited request trace summaries

Questions to answer:

1. Does `llm` finally beat `union` on `first_feasible`?
2. Does `llm` beat `union` on `first_feasible_pde_eval`?
3. Does `llm` keep final hypervolume advantage over `union`?
4. Does `llm` keep or exceed `union` on final front diversity?
5. If anything still fails, is the bottleneck now in:
   - convert
   - recover release
   - preserve stability
   - expand activation
