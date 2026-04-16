# L1 Full-Chain Rebalance After Bounded Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore pre-feasible entry performance while preserving deterministic phase attribution and post-feasible kernelization, using a full-chain rebalance instead of another local patch.

**Architecture:** Keep the validated reusable controller-kernel direction, but split raw controller state from a phase-scoped prompt-projection layer so post-feasible enrichment cannot perturb pre-feasible prompting. Rework pre-feasible reset logic from a generic “stable-family collapse” into a role-diversified shortlist kernel, then validate the whole chain through deterministic tests, offline artifact reanalysis, and only then bounded live gates.

**Tech Stack:** Python 3.12, pytest, JSON/JSONL diagnostics, existing OpenAI-compatible client boundary, current `NSGA-II` union runtime, existing controller/operator trace artifacts

---

## Evidence Snapshot

- The current deterministic contract work is validated:
  - local `policy_phase` attribution no longer depends on provider-returned `phase`
  - enriched offline diagnostics now reclassify late-run rows into `post_feasible` instead of `unknown`
- The new offline gate summary at `scenario_runs/optimizations/diagnostics/2026-04-01-gpt54-post-feasible-design-gate-summary.json` now explains the previous late-run ambiguity:
  - `seed11`: `post_feasible.decision_count=64`, `frontier_add_count=4`, `feasible_regression_count=55`
  - `seed17`: `post_feasible.decision_count=82`, `frontier_add_count=11`, `feasible_regression_count=57`
  - `seed23`: `post_feasible.decision_count=64`, `frontier_add_count=3`, `feasible_regression_count=55`
- The first bounded live gate failed before first feasible:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-post-feasible-check/seed-11/bounded_gate_comparison.json`
  - bounded run: `81` evaluations, `feasible_rate=0.0`, `first_feasible_eval=null`, `pareto_size=0`
  - legacy same-budget prefix: `first_feasible_eval=57`, `feasible_rate=0.02469`, `pareto_size=2`
- The bounded `seed11` controller trace shows a full-chain regression rather than a post-feasible-only miss:
  - selected operators concentrated in `native_sbx_pm=34`, `local_refine=29`, `sbx_pm_global=1`, `hot_pair_to_sink=1`
  - `prefeasible_stagnation` held for all controller rows
  - `prefeasible_forced_reset` fired `48` times and `recent_operator_dominance` fired `14` times
- Root-cause implication:
  - post-feasible kernelization is not the only active change anymore
  - the prompt/state/kernel stack is now too conservative before first feasible
  - another single-point fix is likely to repeat the same pattern

## Full-Chain Root-Cause Hypothesis

The current regression is best explained by a full-chain interaction, not by one bad threshold.

1. Deterministic attribution and frontier-aware summaries were added repository-wide.
2. Those summaries are now visible to the controller prompt even in pre-feasible phases.
3. Pre-feasible reset logic still narrows to “stable families”, but stable families are not internally diversified by role.
4. The prompt now repeatedly sees:
   - `prefeasible_stagnation`
   - `prefeasible_forced_reset`
   - strong “stable repeatable evidence” language
   - a three-operator shortlist where `native_sbx_pm` and `local_refine` already dominate recent counts
5. Under live `GPT-5.4`, this likely shifts selection from “balanced stable shortlist” to “native/local monopoly”.
6. That prevents first feasible entry, so the new post-feasible kernel never activates.

This means the next step must rebalance:

- prompt projection
- pre-feasible shortlist construction
- stable-family anti-monopoly logic
- offline gating

without changing:

- action registry
- repair
- expensive evaluation loop
- survival semantics

## File Structure

### Prompt Projection Boundary

- Create: `optimizers/operator_pool/prompt_projection.py`
  Phase-scoped prompt metadata assembly. This file should decide what the `LLM` sees before first feasible versus after first feasible.
- Modify: `optimizers/operator_pool/llm_controller.py`
  Replace direct prompt assembly from raw `state.metadata` with the new prompt-projection boundary.
- Test: `tests/optimizers/test_llm_controller.py`
- Create: `tests/optimizers/test_llm_prompt_projection.py`
  Focused tests for prompt visibility rules and phase-specific payload shaping.

### Pre-Feasible Rebalance

- Modify: `optimizers/operator_pool/policy_kernel.py`
  Replace “stable-family collapse” with a role-diversified pre-feasible shortlist kernel.
- Modify: `optimizers/operator_pool/domain_state.py`
  Add compact pre-feasible family-mix / stagnation helpers that are generic and prompt-safe.
- Modify: `optimizers/operator_pool/state_builder.py`
  Expose new stable-role / recent-family summaries into controller state.
- Test: `tests/optimizers/test_llm_policy_kernel.py`
- Test: `tests/optimizers/test_llm_controller_state.py`

### Post-Feasible Isolation

- Modify: `optimizers/operator_pool/policy_kernel.py`
  Keep the new post-feasible expand/preserve/recover modes, but ensure they activate only after real feasible entry.
- Modify: `optimizers/operator_pool/llm_controller.py`
  Keep post-feasible guidance but move it behind the prompt-projection boundary.
- Test: `tests/optimizers/test_llm_policy_kernel.py`
- Test: `tests/optimizers/test_llm_controller.py`

### Offline Diagnostics And Gates

- Modify: `optimizers/operator_pool/diagnostics.py`
  Add stable-family monopoly diagnostics and reset-window summaries.
- Modify: `optimizers/cli.py`
  Preserve backward-compatible analyzer CLI while extending gate outputs.
- Test: `tests/optimizers/test_optimizer_cli.py`

### Reporting

- Modify: `docs/reports/R71_msfenicsx_l1_post_feasible_attribution_and_bounded_validation_20260401.md`
  Record that the first bounded gate failed before feasible entry.
- Create: `docs/reports/R72_msfenicsx_l1_full_chain_rebalance_design_gate_20260401.md`
  Record the full-chain diagnosis and the rebalance decision gate.

## Task 1: Freeze The Full-Chain Regression Into Deterministic Tests

**Files:**
- Create: `tests/optimizers/test_llm_prompt_projection.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write failing prompt-projection tests**

Add tests that require:

```python
def test_prefeasible_prompt_projection_omits_post_feasible_frontier_fields():
    payload = build_prompt_projection(_prefeasible_state())
    assert "recent_frontier_add_count" not in payload["archive_state"]
    assert "post_feasible_avg_objective_delta" not in payload["operator_summary"]["local_refine"]
```

```python
def test_post_feasible_prompt_projection_keeps_frontier_and_regression_fields():
    payload = build_prompt_projection(_post_feasible_state())
    assert "recent_frontier_add_count" in payload["archive_state"]
    assert "post_feasible_avg_objective_delta" in payload["operator_summary"]["radiator_expand"]
```

- [ ] **Step 2: Write failing pre-feasible shortlist tests**

Add tests that require:

```python
def test_prefeasible_reset_keeps_global_explore_visibility_when_no_feasible_exists():
    policy = build_policy_snapshot(_seed11_reset_state(), ...)
    assert "sbx_pm_global" in policy.allowed_operator_ids
```

```python
def test_prefeasible_reset_limits_same_role_monopoly_without_custom_operator_patch():
    policy = build_policy_snapshot(_seed11_reset_state(), ...)
    assert policy.candidate_annotations["native_sbx_pm"]["prefeasible_role"] == "stable_baseline"
    assert policy.candidate_annotations["local_refine"]["prefeasible_role"] == "stable_local"
```

- [ ] **Step 3: Write failing diagnostics tests**

Add tests that require:

```python
def test_analyze_controller_trace_reports_prefeasible_stable_family_monopoly_metrics(tmp_path):
    summary = analyze_controller_trace(...)
    assert summary["prefeasible"]["max_stable_family_monopoly_streak"] >= 1
    assert "global_explore_share_during_reset" in summary["prefeasible"]
```

- [ ] **Step 4: Run the focused red tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_prompt_projection.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because prompt visibility is not phase-scoped
- FAIL because pre-feasible reset still reasons only at family level
- FAIL because diagnostics do not yet expose stable-family monopoly metrics

## Task 2: Introduce A Phase-Scoped Prompt Projection Layer

**Files:**
- Create: `optimizers/operator_pool/prompt_projection.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Create: `tests/optimizers/test_llm_prompt_projection.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the minimal projection boundary**

Implementation rules:

- prompt projection must be a dedicated optimizer-layer boundary rather than ad-hoc logic in `_build_prompt_metadata(...)`
- pre-feasible projection must omit post-feasible-only metrics and annotations
- post-feasible projection must retain frontier-aware summaries
- prompt projection must preserve compactness and deterministic field ordering

- [ ] **Step 2: Keep raw controller state richer than prompt state**

Required behavior:

- `state.metadata` may remain rich for diagnostics and local policy
- prompt projection should include only phase-relevant subsets
- no provider-dependent branching

- [ ] **Step 3: Re-run focused projection/controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_prompt_projection.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

## Task 3: Rebuild Pre-Feasible Reset Around Stable Roles, Not Just Stable Families

**Files:**
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Extend state with generic pre-feasible role evidence**

Add compact state such as:

- `progress_state.prefeasible_reset_window_count`
- `progress_state.prefeasible_recent_stable_family_mix`
- `operator_summary[*].recent_family_share`
- `operator_summary[*].recent_role_share`

Keep all of these generic and operator-name-free.

- [ ] **Step 2: Replace reset shortlist semantics**

Implementation rules:

- pre-feasible reset must no longer mean “any stable family is fine”
- define stable roles from operator behavior profile, for example:
  - baseline repair
  - global stable exploration
  - local cleanup
- when reset is active before first feasible:
  - maintain at least one global stable exploration path if available
  - prevent one stable role from monopolizing the shortlist across long windows
  - keep custom families suppressed unless supported by generic evidence

- [ ] **Step 3: Add a generic anti-monopoly rule for stable families**

Required behavior:

- if `native_baseline` or `local_refine` dominates recent valid selections during repeated reset windows, bias the shortlist toward underused stable roles
- do not hardcode `sbx_pm_global` by name as a permanent exception
- derive the rule from stable role / exploration class metadata

- [ ] **Step 4: Re-run focused kernel/state/controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

## Task 4: Isolate Post-Feasible Logic So It Cannot Perturb First-Feasible Entry

**Files:**
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/prompt_projection.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Add explicit activation boundaries**

Required behavior:

- `post_feasible_expand`, `post_feasible_preserve`, and `post_feasible_recover` activate only when:
  - `first_feasible_found is True`
  - `first_feasible_eval is not None`
- pre-feasible prompts must not contain post-feasible role labels such as:
  - `trusted_preserve`
  - `supported_expand`
  - `risky_expand`

- [ ] **Step 2: Keep post-feasible kernel intact but phase-scoped**

Implementation rules:

- preserve the current post-feasible role logic
- do not let post-feasible role annotations influence pre-feasible filtering
- do not let post-feasible system guidance appear before first feasible

- [ ] **Step 3: Re-run focused post-feasible tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

## Task 5: Extend Offline Diagnostics For Stable-Family Monopoly And Reset Drift

**Files:**
- Modify: `optimizers/operator_pool/diagnostics.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Add monopoly-oriented metrics**

Required diagnostics:

- `prefeasible.max_stable_family_monopoly_streak`
- `prefeasible.max_stable_role_monopoly_streak`
- `prefeasible.reset_window_count`
- `prefeasible.global_explore_share_during_reset`
- `prefeasible.local_refine_share_during_reset`
- `prefeasible.native_baseline_share_during_reset`

- [ ] **Step 2: Keep backward compatibility**

Implementation rules:

- `analyze-controller-trace --controller-trace ... --output ...` must still work without sidecars
- richer outputs must appear only when the required artifacts exist

- [ ] **Step 3: Re-run diagnostics tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

## Task 6: Re-Gate Existing Artifacts Before Any New Live Run

**Files:**
- No source edits required

- [ ] **Step 1: Run the full deterministic optimizer slice**

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

- [ ] **Step 2: Reanalyze the existing full `11/17/23` artifacts**

Run enriched diagnostics on:

- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed11`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed23`

Required outcomes:

- no late-run `unknown` bucket dependence
- pre-feasible stable-role monopoly is measurable
- the historical strong runs show better global-stable diversity before first feasible than the failed bounded run

- [ ] **Step 3: Reanalyze the failed bounded `seed11` artifact**

Run enriched diagnostics on:

- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-post-feasible-check/seed-11`

Required outputs:

- explain why no first feasible was reached
- quantify reset-window inflation
- quantify starvation of global stable exploration

- [ ] **Step 4: Save an updated provider-free design gate summary**

Write an aggregate summary to a path such as:

- `scenario_runs/optimizations/diagnostics/2026-04-01-gpt54-full-chain-rebalance-gate-summary.json`

## Task 7: Run Only The Minimal Bounded Live Ladder

**Files:**
- No repository source edits required

- [ ] **Step 1: Re-run bounded `seed11` only**

Use the same bounded budget as the failed gate and compare against the same-budget legacy prefix.

Success conditions:

- first feasible is reached again
- pre-feasible stable-family monopoly shrinks materially
- `global_explore` is visible during reset windows
- bounded post-feasible metrics are not worse than the current legacy prefix

- [ ] **Step 2: Run bounded `seed17` only if `seed11` passes**

Success conditions:

- `prefeasible.max_speculative_family_streak` remains `0`
- `first_feasible_eval` does not materially regress
- no return to historical speculative-family collapse

- [ ] **Step 3: Stop immediately if either bounded gate fails**

Do not run a new full ladder if:

- `seed11` still misses feasible entry or does not recover bounded Pareto growth
- `seed17` regresses on the validated pre-feasible stability gains

## Task 8: Only Then Run The Next Full Ladder And Report

**Files:**
- Modify: `docs/reports/R71_msfenicsx_l1_post_feasible_attribution_and_bounded_validation_20260401.md`
- Create: `docs/reports/R72_msfenicsx_l1_full_chain_rebalance_design_gate_20260401.md`

- [ ] **Step 1: Run a new matched full `11/17/23` ladder only if both bounded gates pass**

- [ ] **Step 2: Record both gains and tradeoffs**

Required reporting:

- deterministic phase attribution status
- pre-feasible stable-role diversity metrics
- post-feasible frontier-add / regression / preservation metrics
- seed-level wins and losses
- explicit statement of whether `union-uniform` is now matched or still mixed

- [ ] **Step 3: Update active docs**

Update:

- `README.md`
- `AGENTS.md` only if repository guidance actually changed
- the relevant report docs under `docs/reports/`

## Acceptance Criteria

This full-chain rebalance is complete only when all of the following are true:

1. pre-feasible prompt payloads no longer carry post-feasible-only noise
2. pre-feasible reset windows preserve generic stable-role diversity instead of collapsing into a native/local monopoly
3. the bounded `seed11` gate reaches first feasible again at the matched budget
4. the bounded `seed17` gate preserves the current no-collapse gains
5. offline diagnostics explain both late-run attribution and pre-feasible monopoly behavior without another full rerun
6. only then is a new full matched ladder justified

## Non-Goals

This plan does not propose:

- changing the action registry
- changing repair
- changing the expensive thermal evaluation loop
- adding benchmark-seed-specific permanent exceptions
- running more live seeds before the offline and bounded gates pass
