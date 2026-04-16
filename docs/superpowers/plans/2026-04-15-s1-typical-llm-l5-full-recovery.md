# S1 Typical LLM L5 Full Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover `nsga2_llm` on `s1_typical` to a paper-safe controller-only implementation that preserves the new route-family diversity gains while materially improving feasible rate and Pareto quality toward or beyond the current `L3 mid` baseline.

**Architecture:** Keep the experiment class unchanged: same problem, same operator pool, same repair/evaluation/solver chain, controller-only differences only. The next recovery line should move from isolated fixes to a coordinated controller package: `expand` semantic budgeting, post-feasible phase arbitration, and stronger diagnostics so we can attribute gains to controller policy rather than hidden runtime variance.

**Tech Stack:** Python 3.12, pytest, existing `optimizers/operator_pool/*` controller stack, OpenAI-compatible `gpt-5.4`, scenario-driven benchmark CLI.

---

### Scope And Boundaries

**Paper-safe invariant**
- `raw / union / llm` stay on the same `s1_typical` problem.
- `union` and `llm` keep the same mixed action registry.
- No changes to:
  - `scenarios/templates/s1_typical.yaml`
  - repair
  - cheap constraints
  - solver
  - evaluation spec
  - survival / backbone / budget class

**Files likely involved**
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/prompt_projection.py`
- Modify: `optimizers/llm_summary.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

**Artifacts to compare after each live rung**
- `optimization_result.json`
- `llm_metrics.json`
- `controller_trace_summary.json`
- `controller_trace.json`
- `llm_request_trace.jsonl`
- `evaluation_events.jsonl`

### Root-Cause Summary

The current evidence says the `llm` route no longer fails because of transport or prompt-schema instability. The remaining performance gap is controller policy:

- `L4` successfully fixed `expand` route-family collapse.
- A first follow-up fix removed `recover` single-semantic collapse.
- A second follow-up fix removed hard recover priority in phase arbitration.
- After those fixes, the remaining bottleneck is now inside `post_feasible_expand`:
  - semantic routes are visible
  - semantic routes are not converting into Pareto additions
  - recent cheap-constraint regressions still arrive in short bursts
  - stable routes continue to own almost all final Pareto points

This means the next stage should not keep tuning one scalar at a time. It should implement one coherent controller package:

1. `expand` semantic budgeting
2. regression-aware semantic ranking
3. phase-local diagnostics for semantic success/failure attribution
4. matched smoke plus full confirmation

### Recommended Approach

**Approach A: Full controller recovery package (Recommended)**
- Add regression-aware semantic budgeting in `post_feasible_expand`
- Add per-family recent success/failure accounting
- Keep current recover-floor and arbitration fixes
- Improve diagnostics so each semantic family has visible:
  - recent preserve count
  - recent regression count
  - recent frontier add count
  - current budget eligibility

**Why recommend this**
- It directly addresses the remaining observed failure mode.
- It stays inside the controller-only paper boundary.
- It reduces the chance of more ad hoc “one more guardrail” iterations.

**Approach B: Expand-only ranking tweak**
- Only adjust semantic candidate ranking order in `policy_kernel`
- Faster, but likely too weak because recent failures come from repeated semantic allocation, not just bad first-choice ranking.

**Approach C: Live-profile budget gating**
- Add live knobs in profile and treat semantic routes as throttled by config
- Useful later, but premature before policy semantics are correct.

### Planned L5 Package

#### 1. Expand Semantic Budgeting

**Intent**
- In `post_feasible_expand`, semantic routes should compete for a bounded share of the generation.
- A semantic route that recently regressed feasibility without frontier return should lose expand budget.
- A semantic route with recent frontier adds or safe preserve behavior should retain eligibility.

**Policy shape**
- Compute a recent per-route-family controller budget state using the same recent decision window already available in controller state.
- For each semantic route family, track:
  - recent selection count
  - recent feasible preservation count
  - recent feasible regression count
  - recent Pareto / frontier add count
- Derive a simple policy score:
  - frontier credit positive
  - preserve credit mildly positive
  - regression credit strongly negative
- In `post_feasible_expand`:
  - keep stable baseline visibility
  - keep at most a bounded number of semantic families visible
  - prefer semantic families with non-negative budget score
  - temporarily suppress semantic families that are recently regression-dominant and frontier-empty

**Expected effect**
- Preserve the new route diversity gains.
- Reduce repeated cheap-constraint failures late in expand.
- Improve semantic frontier conversion rate.

#### 2. Expand Phase-Specific Soft Suppression

**Intent**
- Avoid globally punishing a semantic operator for all phases.
- Suppression should be phase-local:
  - `expand` penalizes recent regressors
  - `recover` keeps stable floor plus one semantic observation slot
  - `preserve` remains conservative

**Policy shape**
- Add `expand_budget_state` annotation in `policy_kernel` candidate annotations.
- Reuse the same operator summaries instead of inventing a separate store.
- Only apply budget-based suppression inside `post_feasible_expand`.

#### 3. Prompt Projection Upgrade

**Intent**
- Make the LLM see why a semantic route is visible or throttled.
- Avoid hidden local policy effects that the model cannot explain.

**Additions**
- In `prompt_projection` / prompt metadata, expose compact per-candidate fields such as:
  - `recent_expand_preserve_credit`
  - `recent_expand_regression_credit`
  - `recent_expand_frontier_credit`
  - `expand_budget_status` = `preferred`, `neutral`, `throttled`
- Keep this compact and controller-facing only.

**Expected effect**
- Better alignment between local guardrails and model choice.
- Easier post-run diagnosis.

#### 4. CLI / Summary Diagnostics

**Intent**
- Make future runs self-explaining so we stop reopening the same attribution questions.

**Diagnostics to add**
- `controller_trace_summary.json` should report:
  - expand-family regression counts
  - expand-family preserve counts
  - expand-family frontier counts
  - expand-family throttled counts
  - stable vs semantic frontier ownership by phase
- `llm_summary` should surface whether a route was visible but throttled versus visible and selected.

### Execution Plan

### Task 1: Encode L5 Expand-Budget Regression Tests

**Files:**
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write failing policy-kernel test for expand semantic throttling**

```python
def test_post_feasible_expand_throttles_semantic_route_with_recent_regression_and_no_frontier_credit():
    ...
    assert "spread_hottest_cluster" not in policy.allowed_operator_ids
    assert "smooth_high_gradient_band" in policy.allowed_operator_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_expand_throttles_semantic_route_with_recent_regression_and_no_frontier_credit -v`
Expected: FAIL because current policy does not budget semantic routes by recent expand outcomes.

- [ ] **Step 3: Write failing controller-level request test**

```python
def test_llm_controller_expand_request_marks_regression_dominant_semantic_route_as_throttled():
    ...
    assert "spread_hottest_cluster" not in client.last_kwargs["candidate_operator_ids"]
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/optimizers/test_llm_controller.py::test_llm_controller_expand_request_marks_regression_dominant_semantic_route_as_throttled -v`
Expected: FAIL.

- [ ] **Step 5: Write failing state/metadata test for budget diagnostics**

```python
def test_build_controller_state_emits_expand_budget_credit_fields():
    ...
    assert operator_panel["spread_hottest_cluster"]["expand_budget_status"] == "throttled"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/optimizers/test_llm_controller_state.py::test_build_controller_state_emits_expand_budget_credit_fields -v`
Expected: FAIL.

### Task 2: Implement Expand Budget State

**Files:**
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/domain_state.py`

- [ ] **Step 1: Add minimal helper that computes recent per-family expand credits**

```python
def _post_feasible_expand_budget_annotations(...):
    ...
```

- [ ] **Step 2: Annotate candidate rows with expand budget state**

```python
annotation["expand_budget_state"] = {
    "recent_expand_selection_count": ...,
    "recent_expand_preserve_count": ...,
    "recent_expand_regression_count": ...,
    "recent_expand_frontier_count": ...,
    "budget_status": ...,
}
```

- [ ] **Step 3: Apply the smallest suppression rule**

```python
if phase == "post_feasible_expand":
    suppress semantic families with:
    - recent regression count > preserve count
    - recent frontier count == 0
    - at least one alternative semantic family remains
```

- [ ] **Step 4: Run the new policy test**

Run: `pytest tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_expand_throttles_semantic_route_with_recent_regression_and_no_frontier_credit -v`
Expected: PASS.

### Task 3: Expose Budget Status To LLM Prompts

**Files:**
- Modify: `optimizers/operator_pool/prompt_projection.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Add prompt projection fields for expand budget diagnostics**
- [ ] **Step 2: Keep them compact and phase-local**
- [ ] **Step 3: Update system prompt wording to mention throttled expand routes as low-priority**
- [ ] **Step 4: Run the new state/controller tests**

Run: `pytest tests/optimizers/test_llm_controller_state.py::test_build_controller_state_emits_expand_budget_credit_fields tests/optimizers/test_llm_controller.py::test_llm_controller_expand_request_marks_regression_dominant_semantic_route_as_throttled -v`
Expected: PASS.

### Task 4: Extend Trace Summaries

**Files:**
- Modify: `optimizers/llm_summary.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Add per-family expand preserve/regression/frontier/throttle counters to summaries**
- [ ] **Step 2: Add CLI regression tests for the new summary fields**
- [ ] **Step 3: Run focused CLI tests**

Run: `pytest tests/optimizers/test_optimizer_cli.py -k "analyze_controller_trace or controller_trace_summary" -v`
Expected: PASS.

### Task 5: Run Verification Ladder

**Files:**
- No source edits expected

- [ ] **Step 1: Run focused controller tests**

Run:
`/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_prompt_projection.py tests/optimizers/test_optimizer_cli.py -k "analyze_controller_trace or controller_trace_summary or llm_decision_summary" -v`

- [ ] **Step 2: Run one 12x6 live mid smoke**

Run:
`/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec /tmp/s1_typical_llm_l4_mid_smoke.yaml --evaluation-workers 2 --output-root /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/<timestamp>__llm_l5_mid_smoke`

- [ ] **Step 3: Analyze controller trace**

Run:
`/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace --controller-trace <run>/controller_trace.json --optimization-result <run>/optimization_result.json --operator-trace <run>/operator_trace.json --llm-request-trace <run>/llm_request_trace.jsonl --llm-response-trace <run>/llm_response_trace.jsonl --output <run>/controller_trace_summary.json`

- [ ] **Step 4: Compare against current reference runs**

Compare with:
- `0415_1325__llm_l3_mid_smoke`
- `0415_1622__llm_l4_mid_smoke_v4`
- `0415_0015__llm`
- `0413_1715__raw_union/raw`
- `0413_1715__raw_union/union`

- [ ] **Step 5: Promotion gate**

Promote to full `llm` only if all are true:
- fallback count `== 0`
- invalid response count `== 0`
- feasible rate `>= 0.78`
- best peak improves over `307.3377`
- best grad is not worse than `11.89` by more than a small tolerance
- semantic frontier adds become positive again

- [ ] **Step 6: If gate passes, run one full matched llm**

Run:
`/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_llm.yaml --evaluation-workers 2 --output-root /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/<timestamp>__llm_full_l5`

### Stop Conditions

Pause only if one of these happens:
- New code wants to change problem/operator/solver/evaluation classes
- Mid smoke shows transport instability again
- Semantic frontier adds remain `0` after L5 throttling
- Live run gets clearly worse than `v4` on both feasible rate and peak/gradient

Otherwise continue automatically through:
- tests
- mid smoke
- controller analysis
- full run promotion decision

### Expected Outcome

Best-case:
- keep current route diversity gains
- recover semantic frontier contribution
- move feasible rate back toward `L3 mid`
- close the remaining objective gap to old full `llm`

If this package still fails, the next change should not be another guardrail. It should be a stronger controller architecture change:
- generation-level semantic quota scheduling
- or two-stage candidate selection with stable/semantic split before LLM choice
