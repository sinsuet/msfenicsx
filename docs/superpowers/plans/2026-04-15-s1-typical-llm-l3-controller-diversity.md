# S1 Typical L3 LLM Controller Diversity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the `s1_typical` `nsga2_llm` route from a repaired-but-collapsed semantic selector into a route-diverse, motif-conditioned controller while keeping the `union` versus `llm` comparison controller-only.

**Architecture:** Keep the fixed mixed operator registry, matched budget, shared repair, shared solve, and shared survival semantics unchanged. Implement the `L3` upgrade entirely inside the controller stack by introducing route-family routing, motif-conditioned reflection credit, negative-evidence retrieval, and explicit recover-exit logic, while preserving the final output contract of one valid operator id per decision.

**Tech Stack:** Python 3.12, pytest, NSGA-II union driver, `optimizers.operator_pool`, OpenAI-compatible client in `llm/openai_compatible/`, YAML/JSON run artifacts

---

## File Map

**Controller logic**

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/llm_controller.py`
  - builds prompt metadata and decision axes
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/policy_kernel.py`
  - phase-aware candidate shaping and guardrails
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/reflection.py`
  - reflective credit summaries over trace history
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/state_builder.py`
  - controller-visible prompt panels
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/domain_state.py`
  - motif buckets and regime panels
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/diagnostics.py`
  - post-run route and operator summaries

**Tests**

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_controller.py`
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_policy_kernel.py`
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_controller_state.py`
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_prompt_projection.py`
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_decision_summary.py`

**Docs / specs**

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/docs/superpowers/specs/2026-04-15-s1-typical-llm-l3-controller-diversity-design.md`
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenarios/optimization/s1_typical_llm.yaml`

### Task 1: Add Failing Tests For Route-Family Control

**Files:**
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write a failing controller test that `post_feasible_expand` does not serialize to a singleton semantic route**

```python
def test_expand_axes_expose_multiple_semantic_route_candidates() -> None:
    metadata = _build_prompt_metadata_for_sink_aligned_expand()
    axes = metadata["decision_axes"]

    assert axes["route_stage"] == "family_then_operator"
    assert axes["route_family_mode"] == "bounded_expand_mix"
    assert set(axes["route_family_candidates"]) >= {
        "hotspot_spread",
        "congestion_relief",
    }
```

- [ ] **Step 2: Write a failing controller test that similar negative evidence is included**

```python
def test_retrieval_panel_exposes_positive_and_negative_route_evidence() -> None:
    metadata = _build_prompt_metadata_with_reflection_history()
    retrieval_panel = metadata["prompt_panels"]["retrieval_panel"]

    assert retrieval_panel["positive_matches"]
    assert retrieval_panel["negative_matches"]
```

- [ ] **Step 3: Write a failing policy-kernel test for route-family quotas in expand**

```python
def test_post_feasible_expand_quota_cools_overused_route_family() -> None:
    snapshot = build_policy_snapshot(_expand_state_with_spread_overuse(), _full_union_registry())

    route_budget = snapshot.candidate_annotations["spread_hottest_cluster"]["route_budget_state"]
    assert route_budget["cooldown_active"] is True
```

- [ ] **Step 4: Write a failing state test for recover exit conditions**

```python
def test_regime_panel_marks_recover_exit_ready_after_stable_preservation() -> None:
    regime_panel = build_prompt_regime_panel(...)
    assert regime_panel["recover_exit_ready"] is True
```

- [ ] **Step 5: Run the targeted tests and confirm red**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py \
  -k "route or retrieval or recover" -v
```

Expected: failures because `L3` route budgeting does not exist yet

- [ ] **Step 6: Commit the failing tests**

```bash
git add \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py
git commit -m "test: cover llm l3 route diversity behavior"
```

### Task 2: Implement Route-Family Decision Axes In The LLM Controller

**Files:**
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/llm_controller.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Add route-family metadata tables and helper mapping**

```python
_ROUTE_FAMILY_BY_OPERATOR = {
    "native_sbx_pm": "stable_local",
    "global_explore": "stable_global",
    "local_refine": "stable_local",
    "move_hottest_cluster_toward_sink": "sink_retarget",
    "spread_hottest_cluster": "hotspot_spread",
    "smooth_high_gradient_band": "congestion_relief",
    "reduce_local_congestion": "congestion_relief",
    "repair_sink_budget": "budget_guard",
    "slide_sink": "sink_retarget",
    "rebalance_layout": "layout_rebalance",
}
```

- [ ] **Step 2: Build route-family candidates instead of singleton semantic trial candidates**

```python
decision_axes["route_family_candidates"] = _rank_route_families(...)
decision_axes["route_family_mode"] = "bounded_expand_mix"
decision_axes["route_stage"] = "family_then_operator"
```

- [ ] **Step 3: Replace `encourage_bounded_trial` prompt language with bounded route-allocation language**

```python
"When route_family_mode is bounded_expand_mix, choose one route family first, "
"prefer underused families with positive local evidence, and avoid repeating a cooled-down family "
"unless its current spatial fit is uniquely strongest."
```

- [ ] **Step 4: Preserve the final output contract**

Implementation notes:

- final response must still be a concrete `selected_operator_id`
- do not change the transport schema
- do not expose route family as a required output field

- [ ] **Step 5: Run focused controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py -v
```

Expected: controller route-axis tests pass

- [ ] **Step 6: Commit the route-family controller change**

```bash
git add \
  optimizers/operator_pool/llm_controller.py \
  tests/optimizers/test_llm_controller.py
git commit -m "feat: add llm route-family decision axes"
```

### Task 3: Implement Motif-Conditioned Credit And Negative Retrieval

**Files:**
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_prompt_projection.py`

- [ ] **Step 1: Add motif-bucket helpers in `domain_state.py`**

```python
def compactness_bucket(value: float) -> str: ...
def nearest_gap_bucket(value: float) -> str: ...
def hotspot_alignment_bucket(inside_sink_window: bool) -> str: ...
```

- [ ] **Step 2: Extend reflection credit to record route-family and motif keys**

```python
credit_key = {
    "phase": regime,
    "sink_budget_bucket": sink_bucket,
    "hotspot_alignment_bucket": alignment_bucket,
    "compactness_bucket": compactness_bucket,
    "gap_bucket": gap_bucket,
    "tradeoff_direction": tradeoff_direction,
}
```

- [ ] **Step 3: Add positive and negative retrieval panels in `state_builder.py`**

```python
retrieval_panel = {
    "positive_matches": positive_matches[:2],
    "negative_matches": negative_matches[:1],
    "query_regime": query_regime,
}
```

- [ ] **Step 4: Add failing-to-green tests for motif credit and negative retrieval**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_prompt_projection.py -v
```

Expected: tests pass and retrieval now exposes positive and negative evidence

- [ ] **Step 5: Commit motif-conditioned reflection**

```bash
git add \
  optimizers/operator_pool/reflection.py \
  optimizers/operator_pool/state_builder.py \
  optimizers/operator_pool/domain_state.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_prompt_projection.py
git commit -m "feat: add motif-conditioned llm route credit"
```

### Task 4: Add Recover-Exit Logic And Route-Family Cooldown In Policy Kernel

**Files:**
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Add regime-panel booleans for recover exit**

```python
regime_panel["recover_exit_ready"] = (
    recent_feasible_regression_count <= 0
    and stable_preservation_streak >= 3
    and not new_dominant_violation_family
)
```

- [ ] **Step 2: Add route-family overuse cooldown in `policy_kernel.py`**

```python
if route_family_recent_share > route_family_share_cap and route_family_recent_frontier_adds <= 0:
    annotation["route_budget_state"]["cooldown_active"] = True
```

- [ ] **Step 3: Bias candidate restoration toward underused high-yield route families**

Implementation notes:

- keep stable backbone visible
- keep at least one semantic family visible in recover
- keep at least two semantic route families visible in expand when available
- do not remove valid operators from the registry

- [ ] **Step 4: Run focused policy-kernel tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected: route cooldown and recover-exit tests pass

- [ ] **Step 5: Commit policy-kernel route budgeting**

```bash
git add \
  optimizers/operator_pool/policy_kernel.py \
  optimizers/operator_pool/domain_state.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add llm recover exit and route cooldown"
```

### Task 5: Extend Diagnostics And Validate With Low-Budget Smoke

**Files:**
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/optimizers/operator_pool/diagnostics.py`
- Modify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/tests/optimizers/test_llm_decision_summary.py`
- Verify only: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenarios/optimization/s1_typical_llm.yaml`

- [ ] **Step 1: Add route-family usage and entropy summaries to diagnostics**

```python
summary["route_family_counts"] = ...
summary["route_family_entropy"] = ...
summary["expand_route_family_counts"] = ...
```

- [ ] **Step 2: Add a low-budget smoke config patch without changing official full-budget defaults**

Implementation notes:

- keep the checked-in official spec matched to the paper budget
- pass low-budget overrides via CLI or temporary local patch that is reverted before final full run
- never change the official final budget just to speed up validation

- [ ] **Step 3: Run diagnostics tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_decision_summary.py -v
```

Expected: route metrics appear in the decision summary outputs

- [ ] **Step 4: Run a low-budget inline smoke**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-l3-smoke
```

Expected:

- live transport remains stable
- `expand` no longer collapses to one semantic family
- operator and route entropy increase
- no obvious feasible-rate collapse

- [ ] **Step 5: Inspect smoke artifacts before any full rerun**

Inspect:

- `controller_trace.json`
- `operator_trace.json`
- `llm_request_trace.jsonl`
- `llm_metrics.json`
- route diagnostics summary

- [ ] **Step 6: Commit diagnostics updates**

```bash
git add \
  optimizers/operator_pool/diagnostics.py \
  tests/optimizers/test_llm_decision_summary.py
git commit -m "feat: add llm route diversity diagnostics"
```

### Task 6: Run Final Verification And Prepare Full-Budget Execution

**Files:**
- No new code files if earlier tasks pass cleanly
- Verify: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/docs/superpowers/specs/2026-04-15-s1-typical-llm-l3-controller-diversity-design.md`

- [ ] **Step 1: Run the full touched optimizer test set**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_prompt_projection.py \
  tests/optimizers/test_llm_decision_summary.py -v
```

Expected: all touched tests pass

- [ ] **Step 2: Re-read the official `llm` spec and confirm the comparison boundary remains controller-only**

Checklist:

- same operator pool as `union`
- same problem definition
- same full-budget defaults
- no new `llm`-only operators
- no repair/solver/evaluation drift

- [ ] **Step 3: Record smoke conclusions**

Capture:

- operator entropy before / after
- route-family entropy before / after
- Pareto size in smoke
- feasible rate in smoke
- dominant expand routes

- [ ] **Step 4: If smoke is positive, run the full official `llm` rerun**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/0415_l3__llm
```

- [ ] **Step 5: Compare the final full run against matched baselines**

Compare against:

- `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/raw`
- `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/union`
- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_0015__llm`

- [ ] **Step 6: Commit the verified `L3` controller upgrade**

```bash
git add \
  optimizers/operator_pool \
  tests/optimizers \
  docs/superpowers/specs/2026-04-15-s1-typical-llm-l3-controller-diversity-design.md \
  docs/superpowers/plans/2026-04-15-s1-typical-llm-l3-controller-diversity.md
git commit -m "feat: add llm l3 route-diversity controller"
```
