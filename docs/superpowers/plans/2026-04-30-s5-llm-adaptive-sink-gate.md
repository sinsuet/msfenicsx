# S5 LLM Adaptive Sink Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hard post-feasible `sink_budget_shape` demotion with an adaptive gate that keeps sink stabilization early and demotes no-credit `sink_resize` only after feasible-rate and frontier-stagnation thresholds are met.

**Architecture:** The policy decision belongs in `optimizers/operator_pool/policy_kernel.py`, where operator annotations already compute semantic debt and saturation. The prompt-facing semantic ordering belongs in `optimizers/operator_pool/state_builder.py`, where `semantic_task_panel` orders semantic tasks. Tests must prove both early stabilization and late exploitation switching before code changes.

**Tech Stack:** Python 3, pytest, existing `ControllerState`, `build_policy_snapshot`, and `_build_prompt_semantic_task_panel` helpers.

---

## File Map

- Modify: `optimizers/operator_pool/policy_kernel.py`
  - Add threshold constants for adaptive sink gate.
  - Change `_post_feasible_sink_budget_shape_deprioritized(...)` so it only returns true when feasible-rate and frontier-stagnation thresholds are met and no sink-budget pressure is active.
- Modify: `optimizers/operator_pool/state_builder.py`
  - Add prompt-panel helper logic mirroring the adaptive gate.
  - Use the gate in `task_rank(...)` so `sink_budget_shape` remains available early but moves behind exploitation tasks late.
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
  - Update current hard-demotion test into the late-gate positive case.
  - Add early-gate negative case where feasible rate is below threshold and `sink_resize` remains neutral/stabilizing.
- Modify: `tests/optimizers/test_llm_controller_state.py`
  - Split current semantic panel test into early and late cases.
  - Early case: legal full sink does not equal budget pressure and does not force exploitation ahead of all sink stabilization.
  - Late case: gate-triggered stagnation puts exploitation tasks before `sink_budget_shape`.

---

### Task 1: Add policy-kernel adaptive gate tests

**Files:**
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Test: `tests/optimizers/test_llm_policy_kernel.py`

- [ ] **Step 1: Add early negative test before existing late sink-debt test**

Insert this test immediately before `test_post_feasible_expand_does_not_repay_sink_budget_debt_without_budget_pressure`:

```python
def test_post_feasible_expand_keeps_sink_budget_stabilizer_before_feasible_rate_gate() -> None:
    policy_kernel = _policy_kernel_module()
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=126,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 92,
                "evaluations_used": 125,
                "evaluations_remaining": 75,
                "feasible_rate": 0.42,
                "first_feasible_eval": 14,
                "sink_budget_utilization": 1.0,
            },
            "archive_state": {
                "pareto_size": 2,
                "recent_frontier_add_count": 0,
                "evaluations_since_frontier_add": 10,
                "recent_feasible_regression_count": 0,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 7,
                "recent_frontier_stagnation_count": 7,
                "diversity_deficit_level": "medium",
            },
            "prompt_panels": {
                "regime_panel": {
                    "phase": "post_feasible_expand",
                    "dominant_violation_family": "thermal_limit",
                    "frontier_pressure": "high",
                    "preservation_pressure": "medium",
                },
                "spatial_panel": {
                    "sink_budget_bucket": "full_sink",
                    "hotspot_inside_sink_window": True,
                    "nearest_neighbor_gap_min": 0.08,
                },
            },
            "recent_decisions": [
                {
                    "evaluation_index": 118 + index,
                    "selected_operator_id": operator_id,
                    "fallback_used": False,
                    "llm_valid": True,
                }
                for index, operator_id in enumerate(
                    (
                        "component_jitter_1",
                        "component_subspace_sbx",
                        "component_relocate_1",
                        "component_jitter_1",
                        "vector_sbx_pm",
                        "component_subspace_sbx",
                        "component_relocate_1",
                        "component_jitter_1",
                    )
                )
            ],
            "operator_summary": {
                "sink_resize": {
                    "selection_count": 44,
                    "recent_selection_count": 0,
                    "proposal_count": 44,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                    "post_feasible_success_count": 18,
                    "post_feasible_selection_count": 44,
                },
                "component_block_translate_2_4": {
                    "selection_count": 12,
                    "recent_selection_count": 1,
                    "proposal_count": 12,
                    "pareto_contribution_count": 0,
                    "recent_expand_frontier_add_count": 0,
                },
                "component_subspace_sbx": {
                    "selection_count": 18,
                    "recent_selection_count": 1,
                    "proposal_count": 18,
                    "pareto_contribution_count": 1,
                    "recent_expand_frontier_add_count": 1,
                },
                "component_jitter_1": {
                    "selection_count": 20,
                    "recent_selection_count": 2,
                    "proposal_count": 20,
                    "pareto_contribution_count": 1,
                    "recent_expand_frontier_add_count": 1,
                },
            },
        },
    )

    policy = policy_kernel.build_policy_snapshot(
        state,
        (
            "sink_resize",
            "component_block_translate_2_4",
            "component_subspace_sbx",
            "component_jitter_1",
        ),
    )

    assert policy.phase == "post_feasible_expand"
    assert policy.candidate_annotations["sink_resize"]["semantic_task"] == "sink_budget_shape"
    assert policy.candidate_annotations["sink_resize"]["semantic_task_status"] == "under_target"
    assert policy.candidate_annotations["sink_resize"]["portfolio_priority"] == "repay_task_debt"
```

- [ ] **Step 2: Verify early negative test fails against current hard-demotion code**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_expand_keeps_sink_budget_stabilizer_before_feasible_rate_gate
```

Expected before implementation: FAIL because current code marks `sink_resize` as `saturated_no_frontier` / `avoid_saturated_repeat` even at feasible rate 0.42.

- [ ] **Step 3: Keep existing late positive test expectation**

Do not weaken `test_post_feasible_expand_does_not_repay_sink_budget_debt_without_budget_pressure`. It should remain the late positive case and continue asserting:

```python
assert policy.candidate_annotations["sink_resize"]["semantic_task_status"] == "saturated_no_frontier"
assert policy.candidate_annotations["sink_resize"]["portfolio_priority"] == "avoid_saturated_repeat"
```

---

### Task 2: Implement policy-kernel adaptive gate

**Files:**
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Test: `tests/optimizers/test_llm_policy_kernel.py`

- [ ] **Step 1: Add threshold constants near the other post-feasible constants**

Add these constants near `_POST_FEASIBLE_EXPOSURE_WINDOW` or the adjacent post-feasible constants:

```python
_ADAPTIVE_SINK_GATE_FEASIBLE_RATE_THRESHOLD = 0.50
_ADAPTIVE_SINK_GATE_FRONTIER_STAGNATION_THRESHOLD = 6
```

- [ ] **Step 2: Replace `_post_feasible_sink_budget_shape_deprioritized` with thresholded gate**

Replace the function body with:

```python
def _post_feasible_sink_budget_shape_deprioritized(state: ControllerState, phase: str) -> bool:
    if phase not in {"post_feasible_expand", "post_feasible_preserve"}:
        return False
    if _sink_budget_pressure_active(state):
        return False
    run_state = state.metadata.get("run_state")
    run_state = run_state if isinstance(run_state, dict) else {}
    feasible_rate = float(run_state.get("feasible_rate", 0.0) or 0.0)
    if feasible_rate < _ADAPTIVE_SINK_GATE_FEASIBLE_RATE_THRESHOLD:
        return False
    progress_state = state.metadata.get("progress_state")
    progress_state = progress_state if isinstance(progress_state, dict) else {}
    frontier_stagnation = int(progress_state.get("recent_frontier_stagnation_count", 0) or 0)
    if frontier_stagnation < _ADAPTIVE_SINK_GATE_FRONTIER_STAGNATION_THRESHOLD:
        return False
    return True
```

- [ ] **Step 3: Run policy kernel focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_policy_kernel.py
```

Expected: all tests in `test_llm_policy_kernel.py` pass.

---

### Task 3: Add semantic panel adaptive ordering tests

**Files:**
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Test: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Rename existing semantic panel test to early case**

Rename:

```python
def test_post_feasible_expand_semantic_panel_prioritizes_exploitation_when_sink_is_legal() -> None:
```

to:

```python
def test_post_feasible_expand_semantic_panel_keeps_sink_stabilizer_before_gate() -> None:
```

Update its `regime_panel` input to include early gate fields:

```python
"run_feasible_rate": 0.42,
"recent_frontier_stagnation_count": 4,
```

Update the final order assertion to preserve sink stabilizer in the active mix rather than forcing it behind exploitation:

```python
assert semantic_task_panel["stage_focus"] == "post_feasible_expand"
assert semantic_task_panel["active_bottleneck"] != "sink_budget_pressure"
assert semantic_task_panel["recommended_task_order"][:4] == [
    "semantic_block_move",
    "local_polish",
    "sink_budget_shape",
    "baseline_reset",
]
```

- [ ] **Step 2: Add late gate semantic panel test**

Add this test immediately after the early case:

```python
def test_post_feasible_expand_semantic_panel_prioritizes_exploitation_after_sink_gate() -> None:
    semantic_task_panel = _build_prompt_semantic_task_panel(
        candidate_operator_ids=(
            "vector_sbx_pm",
            "sink_resize",
            "component_block_translate_2_4",
            "component_jitter_1",
        ),
        regime_panel={
            "phase": "post_feasible_expand",
            "dominant_violation_family": "thermal_limit",
            "frontier_pressure": "high",
            "preservation_pressure": "medium",
            "run_feasible_rate": 0.56,
            "recent_frontier_stagnation_count": 8,
        },
        spatial_panel={
            "sink_budget_bucket": "full_sink",
            "hotspot_inside_sink_window": True,
            "nearest_neighbor_gap_min": 0.08,
        },
        recent_decisions=(
            {"selected_operator_id": "sink_resize"},
            {"selected_operator_id": "component_jitter_1"},
            {"selected_operator_id": "component_block_translate_2_4"},
            {"selected_operator_id": "sink_resize"},
        ),
    )

    assert semantic_task_panel["stage_focus"] == "post_feasible_expand"
    assert semantic_task_panel["active_bottleneck"] != "sink_budget_pressure"
    assert semantic_task_panel["recommended_task_order"][:2] == ["semantic_block_move", "local_polish"]
    assert semantic_task_panel["recommended_task_order"].index("sink_budget_shape") > semantic_task_panel[
        "recommended_task_order"
    ].index("local_polish")
```

- [ ] **Step 3: Run semantic panel tests and verify early case fails before implementation**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller_state.py::test_post_feasible_expand_semantic_panel_keeps_sink_stabilizer_before_gate tests/optimizers/test_llm_controller_state.py::test_post_feasible_expand_semantic_panel_prioritizes_exploitation_after_sink_gate
```

Expected before implementation: the early case fails because current code always demotes sink after removing sink-budget pressure.

---

### Task 4: Implement semantic panel adaptive ordering

**Files:**
- Modify: `optimizers/operator_pool/state_builder.py`
- Test: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Add helper below `_semantic_stage_focus`**

Add:

```python
def _semantic_sink_budget_gate_active(regime_panel: Mapping[str, Any]) -> bool:
    phase = str(regime_panel.get("phase") or "")
    if phase not in {"post_feasible_expand", "post_feasible_preserve"}:
        return False
    if str(regime_panel.get("dominant_violation_family") or "") == "sink_budget":
        return False
    feasible_rate = float(regime_panel.get("run_feasible_rate", 0.0) or 0.0)
    if feasible_rate < 0.50:
        return False
    frontier_stagnation = int(regime_panel.get("recent_frontier_stagnation_count", 0) or 0)
    return frontier_stagnation >= 6
```

- [ ] **Step 2: Update `task_rank` in `_build_prompt_semantic_task_panel`**

Inside `_build_prompt_semantic_task_panel`, compute the gate before `task_rank`:

```python
sink_budget_gate_active = _semantic_sink_budget_gate_active(regime_panel)
```

Then replace the current `task_rank` conditional with:

```python
if task_id == "baseline_reset" and stage_focus == "post_feasible_expand" and active_bottleneck in {
    "frontier_stagnation",
    "local_congestion",
}:
    debt_rank = 2
elif task_id == "sink_budget_shape" and stage_focus == "post_feasible_expand" and not sink_budget_gate_active:
    debt_rank = 0 if share < 0.50 else 1
elif task_id == "sink_budget_shape" and sink_budget_gate_active:
    debt_rank = 2
elif share < target_low:
    debt_rank = 0
else:
    debt_rank = 1
```

This keeps sink stabilization visible before the gate but moves it behind exploitation once the gate opens.

- [ ] **Step 3: Ensure regime panel provides gate fields when built from full state**

If `build_prompt_regime_panel(...)` already includes feasible rate and frontier stagnation under different names, reuse those names in `_semantic_sink_budget_gate_active`. If not, add these keys in `optimizers/operator_pool/domain_state.py` inside `build_prompt_regime_panel(...)` from existing `run_state` and `progress_state` values:

```python
regime_panel["run_feasible_rate"] = float(run_state.get("feasible_rate", 0.0) or 0.0)
regime_panel["recent_frontier_stagnation_count"] = int(progress_state.get("recent_frontier_stagnation_count", 0) or 0)
```

- [ ] **Step 4: Run semantic panel focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller_state.py::test_post_feasible_expand_semantic_panel_keeps_sink_stabilizer_before_gate tests/optimizers/test_llm_controller_state.py::test_post_feasible_expand_semantic_panel_prioritizes_exploitation_after_sink_gate
```

Expected: both tests pass.

---

### Task 5: Verification and S5 GPT 20×10 run

**Files:**
- Verify: `tests/optimizers/test_llm_policy_kernel.py`
- Verify: selected tests in `tests/optimizers/test_llm_controller_state.py`
- Runtime output: `scenario_runs/s5_aggressive15/<timestamp>__llm_gpt_20x10_adaptive_sink_gate/`

- [ ] **Step 1: Run focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller_state.py::test_build_controller_state_emits_semantic_task_panel tests/optimizers/test_llm_controller_state.py::test_post_feasible_expand_semantic_panel_keeps_sink_stabilizer_before_gate tests/optimizers/test_llm_controller_state.py::test_post_feasible_expand_semantic_panel_prioritizes_exploitation_after_sink_gate
```

Expected: policy kernel file passes; selected controller-state tests pass. Do not run the known failing full `test_llm_controller_state.py` unless specifically fixing `test_build_progress_state_keeps_preserve_dwell_live_across_one_regression`.

- [ ] **Step 2: Run diff whitespace check**

Run:

```bash
git diff --check
```

Expected: no output, exit code 0.

- [ ] **Step 3: Start S5 GPT 20×10 adaptive gate run**

Run:

```bash
RUN_ROOT="scenario_runs/s5_aggressive15/$(date +%m%d_%H%M)__llm_gpt_20x10_adaptive_sink_gate"; /home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm default --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml --output-root "$RUN_ROOT" --evaluation-workers 2 --population-size 20 --num-generations 10
```

Expected: command exits 0 and writes rendered run bundle under the printed `RUN_ROOT`.

- [ ] **Step 4: Analyze result**

Read:

```text
scenario_runs/s5_aggressive15/<run>/summaries/seed_summary.json
scenario_runs/s5_aggressive15/<run>/summaries/llm_decision_summary.json
scenario_runs/s5_aggressive15/<run>/summaries/llm_runtime_summary.json
scenario_runs/s5_aggressive15/<run>/pareto_front.json
```

Report these metrics against `0430_0146__llm_gpt_20x10_stage_policy` and `0430_0902__llm_gpt_20x10_sink_debt_policy`:

```text
PDE evaluations
solver skipped evaluations
first feasible eval
feasible rate
Pareto size
best temperature max
best gradient RMS
sink_resize count
expand sink_budget_shape count
semantic_task_entropy
fallback count
```

---

## Self-Review

Spec coverage: the plan covers adaptive gate thresholds, policy-kernel annotation, semantic panel ordering, focused tests, diff check, and the requested S5 GPT 20×10 validation run.

Placeholder scan: no TBD/TODO placeholders remain. Each code-changing task includes exact snippets and commands.

Type consistency: the plan consistently uses `run_feasible_rate`, `recent_frontier_stagnation_count`, `_post_feasible_sink_budget_shape_deprioritized`, `_sink_budget_pressure_active`, and `_semantic_sink_budget_gate_active`.
