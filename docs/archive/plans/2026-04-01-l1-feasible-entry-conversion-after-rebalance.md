# L1 Feasible Entry Conversion After Rebalance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore first-feasible entry on the paper-facing `NSGA-II union-LLM L1` route after the full-chain rebalance improved reset diversity but still failed the bounded `seed11` gate.

**Architecture:** Keep the new phase-scoped prompt projection, deterministic policy phase contract, and stable-role reset kernel. Add a second pre-feasible layer focused on near-feasible conversion: domain summaries should expose violation-family progress and operator-conditioned entry evidence, while the policy kernel should distinguish "diversify" from "convert" without introducing benchmark-, seed-, or operator-name-specific patches. Validate this with deterministic tests and offline artifact comparison first, then re-run only bounded `seed11`; do not proceed to `seed17` or a new full ladder unless `seed11` reaches first feasible again.

**Tech Stack:** Python 3.12, pytest, existing `optimizers/operator_pool/*` controller stack, JSON artifact diagnostics, current `NSGA-II` union runtime, OpenAI-compatible live path only for the final bounded gate

---

## Evidence Snapshot

- The full-chain rebalance implementation is now in place and verified by a fresh deterministic slice:
  - `tests/optimizers/test_llm_prompt_projection.py`
  - `tests/optimizers/test_llm_client.py`
  - `tests/optimizers/test_llm_policy_kernel.py`
  - `tests/optimizers/test_llm_controller.py`
  - `tests/optimizers/test_llm_controller_state.py`
  - `tests/optimizers/test_optimizer_cli.py`
  - result: `71 passed`
- Reanalyzed historical full runs now show no late-run `unknown` dependency:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed11/controller_trace_summary_full_chain_rebalance.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/controller_trace_summary_full_chain_rebalance.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed23/controller_trace_summary_full_chain_rebalance.json`
- The new provider-free design gate summary is:
  - `scenario_runs/optimizations/diagnostics/2026-04-01-gpt54-full-chain-rebalance-gate-summary.json`
- That summary now supports the rebalance diagnosis:
  - historical full runs keep nonzero `prefeasible.global_explore_share_during_reset`
  - the first failed bounded `seed11` showed `global_explore_share_during_reset=0.0`
  - the historical late-run `unknown` bucket is eliminated across all reanalyzed artifacts
- A fresh bounded `seed11` rerun after the rebalance still failed first-feasible entry:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full-chain-rebalance-check/seed-11/optimization_result.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full-chain-rebalance-check/seed-11/controller_trace_summary_full_chain_rebalance.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full-chain-rebalance-check/seed-11/bounded_gate_comparison.json`
- The new bounded run improved reset behavior but still did not convert to feasible:
  - old failed bounded `seed11`: `first_feasible_eval=null`, `reset_window_count=48`, `global_explore_share_during_reset=0.0`, `max_stable_family_monopoly_streak=17`
  - new rebalance bounded `seed11`: `first_feasible_eval=null`, `reset_window_count=32`, `global_explore_share_during_reset=0.46875`, `max_stable_family_monopoly_streak=14`
  - legacy same-budget prefix still remains the matched entry reference: `first_feasible_eval=57`, `pareto_size=2`

## Root-Cause Update

The last round fixed one real problem, but not the final blocker.

1. The full-chain rebalance successfully stopped the pre-feasible reset loop from starving `global_explore`.
2. That means the earlier bounded failure was not only a "prompt pollution" problem.
3. The remaining blocker is now entry conversion: even with better stable-role diversity, the controller still does not transition from near-feasible search into first feasible within the bounded budget.
4. The next kernel should therefore not keep optimizing "diversity" alone; it must model whether the search is in:
   - generic pre-feasible exploration
   - near-feasible conversion pressure
   - post-feasible expansion
5. The missing local abstraction is not Pareto-facing anymore. It is entry-facing:
   - dominant active violation family
   - recent best-near-feasible improvement trend
   - evaluations since last meaningful violation-family relief
   - operator-conditioned evidence for converting the current near-feasible regime into first feasible

## File Structure

### Pre-Feasible Entry State

- Modify: `optimizers/operator_pool/domain_state.py`
  Add compact near-feasible conversion summaries and violation-family progress signals.
- Modify: `optimizers/operator_pool/reflection.py`
  Add operator-conditioned entry-conversion evidence keyed by generic regime tags, not operator-name patches.
- Modify: `optimizers/operator_pool/state_builder.py`
  Thread the new entry-facing summaries into controller state.
- Test: `tests/optimizers/test_llm_controller_state.py`

### Pre-Feasible Entry Kernel

- Modify: `optimizers/operator_pool/policy_kernel.py`
  Split pre-feasible behavior into `prefeasible_diversify` and `prefeasible_convert`, keeping stable-role reset while adding near-feasible conversion shaping.
- Modify: `optimizers/operator_pool/llm_controller.py`
  Update phase guidance so pre-feasible prompts distinguish role-diversity recovery from near-feasible conversion.
- Modify: `optimizers/operator_pool/prompt_projection.py`
  Expose entry-facing fields only when they are relevant and keep post-feasible fields hidden before actual feasible entry.
- Test: `tests/optimizers/test_llm_policy_kernel.py`
- Test: `tests/optimizers/test_llm_controller.py`
- Test: `tests/optimizers/test_llm_prompt_projection.py`

### Offline Diagnostics For Entry Conversion

- Modify: `optimizers/operator_pool/diagnostics.py`
  Add metrics for dominant violation-family persistence, near-feasible relief streaks, and first-feasible conversion opportunity windows.
- Modify: `optimizers/cli.py`
  Preserve backward-compatible analyzer CLI while extending saved summaries.
- Test: `tests/optimizers/test_optimizer_cli.py`

### Reporting

- Create: `docs/reports/R72_msfenicsx_l1_feasible_entry_conversion_gate_20260401.md`
  Record the post-rebalance bounded result and the next-stage entry-conversion diagnosis.

## Task 1: Freeze The Post-Rebalance Entry Failure Into Deterministic Tests

**Files:**
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write failing state-summary tests**

Add tests that require:

```python
def test_build_controller_state_tracks_near_feasible_entry_progress_and_dominant_violation_family():
    state = build_controller_state(...)
    assert state.metadata["progress_state"]["prefeasible_mode"] == "convert"
    assert state.metadata["progress_state"]["evaluations_since_near_feasible_improvement"] >= 0
    assert state.metadata["archive_state"]["best_near_feasible"]["dominant_violation"]["constraint_id"] == "cold_battery_floor"
```

```python
def test_summarize_operator_history_tracks_violation_family_relief_counts():
    summary = summarize_operator_history(...)
    assert summary["local_refine"]["dominant_violation_relief_count"] >= 1
    assert "cold_dominant" in summary["local_refine"]["recent_entry_helpful_regimes"]
```

- [ ] **Step 2: Write failing kernel/controller tests**

Add tests that require:

```python
def test_policy_kernel_enters_prefeasible_convert_when_near_feasible_progress_stalls():
    policy = build_policy_snapshot(_near_feasible_convert_state(), ...)
    assert policy.phase == "prefeasible_convert"
```

```python
def test_prefeasible_convert_shortlist_keeps_stable_roles_and_supported_entry_candidates():
    policy = build_policy_snapshot(_near_feasible_convert_state(), ...)
    assert "sbx_pm_global" in policy.allowed_operator_ids
    assert policy.candidate_annotations["local_refine"]["prefeasible_role"] == "stable_local"
    assert policy.candidate_annotations["local_refine"]["entry_evidence_level"] in {"supported", "trusted"}
```

```python
def test_llm_controller_prefeasible_convert_prompt_mentions_entry_conversion_not_pareto_growth():
    controller.select_decision(_near_feasible_convert_state(), ...)
    assert "first feasible" in system_prompt
    assert "dominant violation" in system_prompt
    assert "pareto" not in system_prompt
```

- [ ] **Step 3: Write failing diagnostics tests**

Add tests that require:

```python
def test_analyze_controller_trace_reports_near_feasible_conversion_metrics(tmp_path):
    summary = analyze_controller_trace(...)
    assert "max_dominant_violation_persistence_streak" in summary["prefeasible"]
    assert "near_feasible_relief_count" in summary["prefeasible"]
```

- [ ] **Step 4: Run the focused red suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because the state does not yet expose entry-conversion evidence
- FAIL because pre-feasible logic still stops at diversity/reset and does not model `prefeasible_convert`
- FAIL because diagnostics do not yet quantify near-feasible conversion stalls

## Task 2: Add Near-Feasible Entry State And Operator Evidence

**Files:**
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/reflection.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Implement compact entry-facing progress state**

Required behavior:

- `progress_state.prefeasible_mode` should distinguish:
  - `diversify`
  - `convert`
- add compact fields such as:
  - `evaluations_since_near_feasible_improvement`
  - `recent_dominant_violation_family`
  - `recent_dominant_violation_persistence_count`
- keep the state prompt-safe and generic

- [ ] **Step 2: Implement operator-conditioned entry evidence**

Required behavior:

- extend `operator_summary[*]` with generic entry-facing fields such as:
  - `dominant_violation_relief_count`
  - `near_feasible_improvement_count`
  - `avg_near_feasible_violation_delta`
  - `recent_entry_helpful_regimes`
- do not encode hardcoded operator-specific exceptions

- [ ] **Step 3: Re-run focused state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS

## Task 3: Split Pre-Feasible Policy Into Diversify And Convert

**Files:**
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/prompt_projection.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_llm_prompt_projection.py`

- [ ] **Step 1: Add `prefeasible_convert` activation rules**

Implementation rules:

- activate `prefeasible_convert` only when:
  - no feasible solution exists yet
  - search is in a near-feasible regime
  - recent violation-family relief has stalled enough to justify entry conversion shaping
- keep `prefeasible_diversify` or existing `prefeasible_progress/stagnation` semantics for earlier search

- [ ] **Step 2: Shape the convert shortlist generically**

Required behavior:

- keep stable-role diversity from the rebalance round
- also keep at least one supported entry-facing candidate when generic evidence exists
- use regime/evidence fields rather than operator names
- keep speculative custom families suppressed unless they have real conversion evidence

- [ ] **Step 3: Update prompt projection and prompt guidance**

Required behavior:

- pre-feasible convert prompts should surface:
  - dominant violation family
  - near-feasible improvement trend
  - entry-facing operator evidence
- they must still omit:
  - post-feasible frontier metrics
  - Pareto-role labels
- system prompt wording should distinguish:
  - stable-role diversity recovery
  - first-feasible conversion pressure

- [ ] **Step 4: Re-run focused kernel/controller/projection tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_prompt_projection.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

## Task 4: Extend Offline Diagnostics For Entry Conversion

**Files:**
- Modify: `optimizers/operator_pool/diagnostics.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Add entry-conversion diagnostics**

Required metrics:

- `prefeasible.max_dominant_violation_persistence_streak`
- `prefeasible.near_feasible_relief_count`
- `prefeasible.evaluations_since_last_near_feasible_relief`
- `prefeasible.entry_convert_window_count`
- `prefeasible.supported_entry_candidate_share`

- [ ] **Step 2: Preserve backward compatibility**

Implementation rules:

- `analyze-controller-trace --controller-trace ... --output ...` must still work without sidecars
- new fields should appear only when evidence exists

- [ ] **Step 3: Re-run diagnostics tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

## Task 5: Re-Gate Existing Artifacts Before Any New Live Run

**Files:**
- No source edits required

- [ ] **Step 1: Run the fresh deterministic optimizer slice**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_prompt_projection.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 2: Reanalyze the key artifact set**

Re-run enriched diagnostics on:

- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed11`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed23`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-post-feasible-check/seed-11`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full-chain-rebalance-check/seed-11`

Required outcomes:

- no late-run `unknown` bucket returns
- historical full runs and failed bounded runs are distinguishable by entry-conversion diagnostics, not only by reset diversity
- the new bounded run shows improved diversity but still weak entry-conversion evidence, justifying the next fix

- [ ] **Step 3: Save an updated provider-free gate summary**

Write a new aggregate summary to:

- `scenario_runs/optimizations/diagnostics/2026-04-01-gpt54-entry-conversion-gate-summary.json`

## Task 6: Run Only The Minimal Bounded Live Gate Again

**Files:**
- No repository source edits required

- [ ] **Step 1: Re-run bounded `seed11` only**

Use the same bounded budget and compare against:

- previous failed bounded `seed11`
- rebalance bounded `seed11`
- legacy same-budget prefix

Success conditions:

- `first_feasible_eval` is no longer `null`
- `global_explore_share_during_reset` stays nonzero
- reset pressure does not regress back toward the first failed bounded run
- bounded Pareto size is not worse than the same-budget legacy prefix once feasible entry is restored

- [ ] **Step 2: Stop immediately if bounded `seed11` still misses feasible entry**

Do not continue to:

- bounded `seed17`
- any new full `11/17/23` ladder

if `seed11` still reports:

- `first_feasible_eval=null`
- `pareto_size=0`

- [ ] **Step 3: Run bounded `seed17` only if bounded `seed11` passes**

Success conditions:

- preserve the earlier no-collapse gains
- avoid reintroducing speculative custom collapse
- avoid material regression in time-to-first-feasible versus the validated route

## Task 7: Report Only After Bounded Gates Pass

**Files:**
- Create: `docs/reports/R72_msfenicsx_l1_feasible_entry_conversion_gate_20260401.md`

- [ ] **Step 1: Write the report after the bounded gate decision**

Required reporting:

- what the rebalance fixed
- what it still failed to fix
- the new entry-conversion diagnosis
- bounded `seed11` and `seed17` outcomes if `seed17` is reached

- [ ] **Step 2: Update active docs only if the bounded gate passes**

Update:

- `README.md` only if workflow or current recommended gate order changed
- `AGENTS.md` only if repository guidance changed

## Acceptance Criteria

This next round is complete only when all of the following are true:

1. pre-feasible logic distinguishes diversity recovery from near-feasible conversion
2. controller state and diagnostics expose generic entry-conversion evidence
3. bounded `seed11` reaches first feasible again within the matched budget
4. reset diversity gains from the rebalance round are preserved
5. only then is bounded `seed17` justified
6. only then is another full matched ladder justified

## Non-Goals

This plan does not propose:

- changing the action registry
- changing repair
- changing the expensive evaluation loop
- reintroducing benchmark-, seed-, or operator-name-specific permanent exceptions
- running `seed17` or a new full ladder before bounded `seed11` passes
