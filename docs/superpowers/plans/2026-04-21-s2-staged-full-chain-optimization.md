# S2 Staged Full-Chain Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Status: historical S2 controller plan; current active paper-facing debugging has moved to `s5_aggressive15` in the S5-S7 family.

**Goal:** Activate the full `s2_staged` controller chain so `llm` could convert earlier in PDE terms, transition from recover into preserve and expand, and improve front diversity without losing its historical hypervolume advantage.

**Architecture:** The source of truth is `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-21-s2-staged-full-chain-optimization-design.md`. The work stays controller-side: add convert family floors, preserve dwell and recover hysteresis, stable-local handoff visibility, and delayed expand diversity floors while keeping the shared operator registry fixed across `union` and `llm`.

**Tech Stack:** Python 3.11+, pytest, JSONL traces, pymoo, conda env `msfenicsx`.

---

## File Structure

### Primary implementation files

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Modify: `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

### Primary focused tests

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`

### Runtime verification targets

- Old official raw seed run:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11`
- Old official union seed run:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11`
- New llm rerun root:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged`
- New compare bundle root:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/$(date +%m%d_%H%M)__raw_union_old_vs_llm_chain_opt`

---

### Task 1: Lock The New Chain Audit In Tests

**Files:**

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- Modify: `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

- [ ] **Step 1: Write the failing audit tests**

```python
def test_prompt_surface_summarizes_convert_route_coverage() -> None:
    summary = summarize_prompt_chain_progress(request_rows)
    assert summary["convert_route_family_mode_counts"] == {"convert_family_mix": 1}
    assert summary["convert_semantic_trial_mode_counts"] == {"encourage_bounded_trial": 1}


def test_prompt_surface_summarizes_phase_occupancy_and_handoff_gaps() -> None:
    summary = summarize_prompt_chain_progress(request_rows)
    assert summary["phase_counts"]["post_feasible_preserve"] >= 1
    assert summary["phase_counts"]["post_feasible_expand"] >= 1
    assert summary["hidden_positive_credit_family_counts"] == {}
```

- [ ] **Step 2: Run the audit test file and confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s2_staged_controller_audit.py -v
```

Expected:

- FAIL on missing helper `summarize_prompt_chain_progress(...)` or missing keys
- FAIL because existing fixtures still describe zero preserve/expand occupancy

- [ ] **Step 3: Add the audit helper**

Implement in `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`:

```python
def summarize_prompt_chain_progress(
    request_rows: Sequence[Mapping[str, Any]],
    *,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    return {
        "phase_counts": dict(phase_counts),
        "convert_route_family_mode_counts": dict(convert_route_family_mode_counts),
        "convert_semantic_trial_mode_counts": dict(convert_semantic_trial_mode_counts),
        "recover_pool_size_summary": _pool_size_summary(recover_pool_sizes),
        "hidden_positive_credit_family_counts": dict(sorted(hidden_positive_credit_family_counts.items())),
    }
```

The helper must derive:

- full phase occupancy counts
- convert-only `route_family_mode` and `semantic_trial_mode`
- recover pool size summary
- hidden positive credit counts by family

- [ ] **Step 4: Re-run the audit tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s2_staged_controller_audit.py -v
```

Expected:

- PASS on the updated fixture expectations

- [ ] **Step 5: Commit**

```bash
git add tests/optimizers/test_s2_staged_controller_audit.py optimizers/analytics/staged_audit.py
git commit -m "test: add staged chain occupancy audit"
```

### Task 2: Open Convert With State-Conditioned Family Floors

**Files:**

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`

- [ ] **Step 1: Write the failing convert tests**

```python
def test_prefeasible_convert_restores_budget_guard_when_sink_budget_is_tight() -> None:
    policy = build_policy_snapshot(
        _prefeasible_convert_budget_tight_state(),
        ALL_OPERATOR_IDS,
    )
    assert "repair_sink_budget" in policy.allowed_operator_ids


def test_prefeasible_convert_request_surface_exposes_convert_family_mix() -> None:
    axes = LLMOperatorController._build_decision_axes(_prefeasible_convert_state())
    assert axes["route_family_mode"] == "convert_family_mix"
    assert axes["semantic_trial_mode"] == "encourage_bounded_trial"


def test_prefeasible_convert_retrieval_panel_keeps_convert_phase_visible() -> None:
    state = _build_phase_alignment_state(policy_phase="prefeasible_convert")
    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    assert retrieval_panel["query_regime"]["phase"] == "prefeasible_convert"
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because `prefeasible_convert` still exposes `route_family_mode = none`
- FAIL because semantic convert families remain filtered out

- [ ] **Step 3: Implement the convert floors**

Add the policy-side family floor in `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`:

```python
def _prefeasible_convert_family_floor(
    state: ControllerState,
    candidate_ids: Sequence[str],
) -> tuple[str, ...]:
    prompt_panels = state.metadata.get("prompt_panels", {})
    spatial_panel = prompt_panels.get("spatial_panel", {}) if isinstance(prompt_panels, Mapping) else {}
    regime_panel = prompt_panels.get("regime_panel", {}) if isinstance(prompt_panels, Mapping) else {}
    allowed = [
        operator_id
        for operator_id in candidate_ids
        if operator_id in {"native_sbx_pm", "global_explore", "local_refine"}
    ]
    sink_bucket = str(spatial_panel.get("sink_budget_bucket", ""))
    preferred_effect = str((regime_panel.get("objective_balance") or {}).get("preferred_effect", ""))
    if sink_bucket in {"tight", "full_sink"} and "repair_sink_budget" in candidate_ids:
        allowed.append("repair_sink_budget")
    if preferred_effect == "gradient_improve":
        for operator_id in ("reduce_local_congestion", "rebalance_layout", "smooth_high_gradient_band"):
            if operator_id in candidate_ids:
                allowed.append(operator_id)
    return tuple(dict.fromkeys(allowed))
```

Expose the same contract in `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`:

```python
if phase == "prefeasible_convert" and route_family_candidates:
    route_stage = "family_then_operator"
    route_family_mode = "convert_family_mix"
    semantic_trial_mode = "encourage_bounded_trial"
```

And in `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py` keep
the convert retrieval surface explicit:

```python
if normalized_phase == "prefeasible_convert":
    return ["prefeasible_search"]
```

- [ ] **Step 4: Re-run the focused convert tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS with convert-specific family floors visible in policy and request trace

- [ ] **Step 5: Commit**

```bash
git add tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py optimizers/operator_pool/policy_kernel.py optimizers/operator_pool/state_builder.py optimizers/operator_pool/llm_controller.py
git commit -m "feat: open staged convert family mix"
```

### Task 3: Add Preserve Dwell And Recover Reentry Hysteresis

**Files:**

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`

- [ ] **Step 1: Write the failing preserve-dwell tests**

```python
def test_build_progress_state_tracks_preserve_dwell_after_recover_cools() -> None:
    progress = build_progress_state(history_with_cooling_recover_pressure)
    assert progress["post_feasible_mode"] == "preserve"
    assert progress["preserve_dwell_remaining"] >= 2


def test_detect_search_phase_keeps_preserve_live_during_dwell_window() -> None:
    policy = build_policy_snapshot(_preserve_dwell_state(), ALL_OPERATOR_IDS)
    assert policy.phase == "post_feasible_preserve"
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because preserve dwell fields do not exist yet
- FAIL because the controller still returns immediately to recover-only behavior

- [ ] **Step 3: Implement preserve dwell**

In `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`, add explicit
state:

```python
_PRESERVE_DWELL_MIN = 3

progress_state["preserve_dwell_count"] = int(preserve_dwell_count)
progress_state["preserve_dwell_remaining"] = max(0, _PRESERVE_DWELL_MIN - preserve_dwell_count)
progress_state["recover_reentry_pressure"] = recover_reentry_pressure
```

Then consume it in `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`:

```python
if post_feasible_mode == "preserve" and int(progress_state.get("preserve_dwell_remaining", 0)) > 0:
    return "post_feasible_preserve"
if post_feasible_mode == "recover" and _post_feasible_recover_exit_ready(state):
    return "post_feasible_preserve"
```

- [ ] **Step 4: Re-run the preserve-dwell tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS with non-zero preserve dwell state

- [ ] **Step 5: Commit**

```bash
git add tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller_state.py optimizers/operator_pool/domain_state.py optimizers/operator_pool/policy_kernel.py
git commit -m "feat: add preserve dwell hysteresis"
```

### Task 4: Restore Stable-Local Handoff Visibility

**Files:**

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`

- [ ] **Step 1: Write the failing handoff tests**

```python
def test_recover_handoff_restores_positive_stable_local_family_visibility() -> None:
    policy = build_policy_snapshot(_post_feasible_recover_positive_stable_local_credit_state(), ALL_OPERATOR_IDS)
    assert "native_sbx_pm" in policy.allowed_operator_ids
    assert "local_refine" in policy.allowed_operator_ids


def test_request_trace_marks_stable_local_handoff_window() -> None:
    request_entry = _request_trace_entry_for_handoff_state()
    assert request_entry["stable_local_handoff_active"] is True
    assert "stable_local" in request_entry["visible_route_families"]
```

- [ ] **Step 2: Run the focused handoff tests and confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because the audit still allows positive `stable_local` credit to remain hidden

- [ ] **Step 3: Implement the handoff window**

Aggregate the handoff signal in `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`:

```python
return {
    "positive_families": sorted(set(positive_families)),
    "negative_families": sorted(set(negative_families)),
    "handoff_families": sorted(set(handoff_families)),
}
```

Project it in `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`:

```python
"route_family_credit": {
    "positive_families": positive_families,
    "negative_families": negative_families,
    "handoff_families": handoff_families,
},
"stable_local_handoff_active": "stable_local" in handoff_families,
```

Keep the prompt projection coherent in
`/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`:

```python
projection["prompt_panels"]["retrieval_panel"]["stable_local_handoff_active"] = bool(
    retrieval_panel.get("stable_local_handoff_active", False)
)
```

Consume it in `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`:

```python
retrieval_panel = state.metadata.get("prompt_panels", {}).get("retrieval_panel", {})
if bool(retrieval_panel.get("stable_local_handoff_active", False)):
    allowed_operator_ids.extend(
        operator_id for operator_id in candidate_ids if operator_id in {"native_sbx_pm", "local_refine"}
    )
```

- [ ] **Step 4: Re-run the focused handoff tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS with visible stable-local handoff in policy and request trace

- [ ] **Step 5: Commit**

```bash
git add tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py optimizers/operator_pool/reflection.py optimizers/operator_pool/state_builder.py optimizers/operator_pool/prompt_projection.py optimizers/operator_pool/policy_kernel.py
git commit -m "feat: restore stable local handoff visibility"
```

### Task 5: Activate Expand Only After Preserve Exists

**Files:**

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`

- [ ] **Step 1: Write the failing expand-activation tests**

```python
def test_preserve_state_promotes_to_expand_when_frontier_pressure_stays_high() -> None:
    policy = build_policy_snapshot(_post_feasible_preserve_frontier_pressure_state(), ALL_OPERATOR_IDS)
    assert policy.phase == "post_feasible_expand"


def test_expand_keeps_diversity_floor_for_underused_frontier_family() -> None:
    policy = build_policy_snapshot(_post_feasible_expand_diversity_floor_state(), ALL_OPERATOR_IDS)
    assert any(
        operator_id in policy.allowed_operator_ids
        for operator_id in ("spread_hottest_cluster", "reduce_local_congestion", "rebalance_layout")
    )
```

- [ ] **Step 2: Run the focused expand tests and confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because live expand promotion is still unreachable from preserve

- [ ] **Step 3: Implement delayed expand activation**

Add promotion logic in `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`:

```python
if (
    int(progress_state.get("preserve_dwell_remaining", 0)) == 0
    and int(archive_state.get("pareto_size", 0)) <= 1
    and int(progress_state.get("recent_frontier_stagnation_count", 0)) >= 2
):
    progress_state["post_feasible_mode"] = "expand"
```

Keep the LLM-facing route surface in `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`:

```python
if phase == "post_feasible_expand":
    route_family_mode = "bounded_expand_mix"
    semantic_trial_mode = "encourage_bounded_trial"
```

And preserve at least one underused expand family in
`/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`:

```python
for operator_id in ("spread_hottest_cluster", "reduce_local_congestion", "rebalance_layout"):
    if operator_id in candidate_ids and operator_id not in allowed_operator_ids:
        allowed_operator_ids.append(operator_id)
        break
```

- [ ] **Step 4: Re-run the expand tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS with explicit `post_feasible_expand` activation and diversity floors

- [ ] **Step 5: Commit**

```bash
git add tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py optimizers/operator_pool/domain_state.py optimizers/operator_pool/policy_kernel.py optimizers/operator_pool/llm_controller.py
git commit -m "feat: activate delayed staged expand diversity"
```

### Task 6: Run The Required Focused Gate

**Files:**

- Test: `/home/hymn/msfenicsx/tests/generator/test_s2_staged_template.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_baseline.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Run the exact focused gate**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_s2_staged_template.py tests/optimizers/test_s2_staged_baseline.py tests/optimizers/test_s2_staged_controller_audit.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS across all six files

- [ ] **Step 2: If the gate fails, fix the smallest broken chain segment first**

Run only the failing slice before widening scope:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py -v
```

Expected:

- the failing test points to exactly one chain segment before the next edit

The recovery rule for this task is:

- if convert tests fail, do not touch preserve or expand yet
- if preserve tests fail, do not force expand activation yet
- if handoff tests fail, do not rerun the benchmark yet

- [ ] **Step 3: Commit**

```bash
git add tests/generator/test_s2_staged_template.py tests/optimizers/test_s2_staged_baseline.py tests/optimizers/test_s2_staged_controller_audit.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py optimizers/operator_pool/domain_state.py optimizers/operator_pool/state_builder.py optimizers/operator_pool/policy_kernel.py optimizers/operator_pool/reflection.py optimizers/operator_pool/prompt_projection.py optimizers/operator_pool/llm_controller.py optimizers/analytics/staged_audit.py
git commit -m "feat: complete staged full chain optimization"
```

### Task 7: Official Rerun, Render, Compare, And Report

**Files:**

- Run output: `/home/hymn/msfenicsx/scenario_runs/s2_staged`
- Compare output: `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/$(date +%m%d_%H%M)__raw_union_old_vs_llm_chain_opt`

- [ ] **Step 1: Run the official llm rerun**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s2_staged_llm.yaml --evaluation-workers 2 --output-root ./scenario_runs/s2_staged
```

Expected:

- the run completes successfully and refreshes the active llm run root under
  `/home/hymn/msfenicsx/scenario_runs/s2_staged`

- [ ] **Step 2: Render assets**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli render-assets --run ./scenario_runs/s2_staged
```

Expected:

- figures and analytics are regenerated beside the new run traces

- [ ] **Step 3: Build the compare bundle**

Run:

```bash
COMPARE_ROOT=./scenario_runs/compare_reports/s2_staged/$(date +%m%d_%H%M)__raw_union_old_vs_llm_chain_opt
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli compare-runs --run ./scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11 --run ./scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11 --run ./scenario_runs/s2_staged --output "$COMPARE_ROOT"
```

Expected:

- a fresh external compare bundle is written outside the source runs

- [ ] **Step 4: Record the final answers from artifacts only**

Pull the final answers from:

- `analytics/summary_rows.json`
- `traces/llm_request_trace.jsonl`
- `traces/controller_trace.jsonl`

The post-rerun report must answer:

1. does `llm` now beat `union` on `first_feasible`?
2. does `llm` keep the final Pareto / hypervolume advantage?
3. does `llm` now beat `union` on PDE first feasible?
4. if not, which segment still fails:
   - convert entry
   - recover to preserve handoff
   - stable-local handoff
   - expand diversity

- [ ] **Step 5: Commit**

```bash
git add scenario_runs/s2_staged scenario_runs/compare_reports/s2_staged
git commit -m "docs: capture staged full chain optimization rerun"
```
