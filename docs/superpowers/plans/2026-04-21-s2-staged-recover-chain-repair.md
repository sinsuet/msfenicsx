# S2 Staged Recover-Chain Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the `s2_staged` post-feasible controller chain so `llm` can use coherent recover/preserve/expand semantics, restore visibility for credited route families, and be re-evaluated fairly against `raw` and `union`.

**Architecture:** The source of truth is `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-21-s2-staged-recover-chain-repair-design.md`. The repair keeps the shared operator registry fixed and changes only the controller-side state contract, credit surfaces, candidate-family restoration, and audit coverage. The implementation is intentionally TDD-first and runs directly on `main` in this repository, not in a separate worktree.

**Tech Stack:** Python 3.11+, pytest, pymoo, JSONL traces, conda env `msfenicsx`.

---

## File Structure

### Primary implementation files

- modify `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- modify `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- modify `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- modify `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- modify `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- modify `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- modify `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

### Primary focused tests

- modify `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- modify `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- modify `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- modify `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- keep verification coverage on:
  - `/home/hymn/msfenicsx/tests/generator/test_s2_staged_template.py`
  - `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_baseline.py`

### Run and audit targets

- reuse old official suite:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm`
- rerun new official `llm` mode under the timestamped canonical run root created
  by `optimize-benchmark` inside:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/`
- compare via a new timestamped bundle created inside:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/`

---

### Task 1: Lock The Phase-Contract Audit In Tests

**Files:**

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- Modify: `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

- [ ] **Step 1: Write failing audit tests for the current contract mismatches**

```python
def test_prompt_surface_flags_recover_retrieval_phase_mismatch() -> None:
    summary = summarize_prompt_contract_mismatches(request_rows)
    assert summary["phase_mismatch_count"] == 0


def test_prompt_surface_flags_hidden_positive_route_credit() -> None:
    summary = summarize_prompt_contract_mismatches(request_rows)
    assert summary["hidden_positive_credit_requests"] == 0
```

- [ ] **Step 2: Run the failing audit tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s2_staged_controller_audit.py -v
```

Expected:

- FAIL on missing helper or non-zero mismatch counts against the fixed fixture
  traces used in the audit test

- [ ] **Step 3: Add audit helpers that expose the broken contract directly**

Implement in `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`:

```python
def summarize_prompt_contract_mismatches(
    request_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "phase_mismatch_count": phase_mismatch_count,
        "phase_mismatch_examples": phase_mismatch_examples,
        "hidden_positive_credit_requests": hidden_positive_credit_requests,
        "hidden_positive_credit_family_counts": dict(hidden_positive_credit_family_counts),
        "recover_pool_size_summary": recover_pool_size_summary,
    }
```

The helper must report:

- `phase_mismatch_count`
- `phase_mismatch_examples`
- `hidden_positive_credit_requests`
- `hidden_positive_credit_family_counts`
- `recover_pool_size_summary`

- [ ] **Step 4: Re-run the audit tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_s2_staged_controller_audit.py -v
```

Expected:

- PASS with stable audit summaries for the checked fixtures

### Task 2: Repair The Phase Contract Between Domain State, Retrieval, And Prompt Projection

**Files:**

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write failing state tests for recover-phase retrieval alignment**

```python
def test_retrieval_query_phase_uses_recover_when_policy_phase_is_recover() -> None:
    state = _build_phase_alignment_state(policy_phase="post_feasible_recover")
    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    assert retrieval_panel["query_regime"]["phase"] == "post_feasible_recover"


def test_prompt_projection_does_not_silently_disagree_with_retrieval_phase() -> None:
    state = _build_phase_alignment_state(policy_phase="post_feasible_recover")
    metadata = build_prompt_projection(
        state,
        candidate_operator_ids=state.metadata["candidate_operator_ids"],
        original_candidate_operator_ids=state.metadata["candidate_operator_ids"],
        policy_snapshot=_build_phase_alignment_snapshot("post_feasible_recover"),
        guardrail=None,
    )
    assert (
        metadata["prompt_panels"]["regime_panel"]["phase"]
        == metadata["prompt_panels"]["retrieval_panel"]["query_regime"]["phase"]
    )
```

- [ ] **Step 2: Run the focused state tests and confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because current retrieval still collapses recover into preserve

- [ ] **Step 3: Implement the phase-contract repair**

Apply these changes:

- in `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
  - keep `build_prompt_phase()` phase-specific for:
    - `prefeasible_convert`
    - `post_feasible_recover`
    - `post_feasible_preserve`
    - `post_feasible_expand`
- in `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
  - build retrieval query from the actual prompt phase
  - if fallback phases are needed, make them explicit via
    `query_regime["phase_fallbacks"]`
- in `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
  - preserve the aligned phase contract rather than rewriting only one panel

- [ ] **Step 4: Re-run the state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS

### Task 3: Replace Sticky Recover With Windowed Recover Pressure

**Files:**

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write failing tests for recover exit readiness and preserve activation**

```python
def test_recover_exit_ready_uses_recent_pressure_not_any_historical_family_switch() -> None:
    progress_state = build_progress_state(history=history_with_old_switch_but_recent_stability)
    assert progress_state["post_feasible_mode"] == "preserve"


def test_detect_search_phase_promotes_to_preserve_after_recover_pressure_cools() -> None:
    snapshot = build_policy_snapshot(state, OPERATOR_IDS)
    assert snapshot.phase == "post_feasible_preserve"
```

- [ ] **Step 2: Run the focused policy/state tests and confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because current logic still keys off the old tail-sensitive boolean and
  perfect-exit conditions

- [ ] **Step 3: Implement recent-pressure recover semantics**

Implement in `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`:

```python
progress_state["recent_violation_family_switch_count"] = int(recent_switch_count)
progress_state["recover_pressure_level"] = recover_pressure_level
progress_state["recover_exit_ready"] = recover_pressure_level == "low"
```

Then update `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py` to
use:

- `recover_pressure_level`
- `recover_exit_ready`

instead of:

- the old all-or-nothing `new_dominant_violation_family` gate

- [ ] **Step 4: Re-run the focused policy/state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS

### Task 4: Make Recover Visibility Credit-Aware And Family-Aware

**Files:**

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write failing tests for hidden positive-credit families**

```python
def test_recover_restores_positive_budget_guard_family_visibility() -> None:
    snapshot = build_policy_snapshot(state_with_positive_budget_guard_credit, OPERATOR_IDS)
    assert "repair_sink_budget" in snapshot.allowed_operator_ids


def test_recover_restores_positive_stable_local_family_visibility() -> None:
    snapshot = build_policy_snapshot(state_with_positive_stable_local_credit, OPERATOR_IDS)
    assert any(op in snapshot.allowed_operator_ids for op in ("native_sbx_pm", "local_refine"))
```

- [ ] **Step 2: Run the focused policy/controller tests and confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because current recover visibility restores only a narrow semantic floor
  without credit-aware family guarantees

- [ ] **Step 3: Add family-level credit surfaces and visibility restoration**

Implement these pieces:

- in `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
  - aggregate `credit_by_route_family`
  - keep positive and negative support by compact regime key
- in `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
  - expose a route-family retrieval panel such as:

```python
"route_family_credit": {
    "positive_families": ["budget_guard", "stable_local"],
    "negative_families": ["sink_retarget"],
}
```

- in `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
  - restore at least one operator per positive family during recover/preserve
  - unless explicit stronger-negative suppression is trace-visible

- [ ] **Step 4: Re-run the focused policy/controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

### Task 5: Differentiate Recover, Preserve, And Expand Candidate Floors

**Files:**

- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Test: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write failing tests for preserve/expand route-family behavior**

```python
def test_preserve_keeps_multiple_low_regression_families_visible() -> None:
    snapshot = build_policy_snapshot(state_in_preserve, OPERATOR_IDS)
    assert len(snapshot.allowed_operator_ids) >= 3


def test_expand_prefers_family_diversity_without_hiding_all_nonstable_routes() -> None:
    snapshot = build_policy_snapshot(state_in_expand, OPERATOR_IDS)
    assert any(op in snapshot.allowed_operator_ids for op in GRADIENT_ROUTE_OPERATORS)
```

- [ ] **Step 2: Run the focused policy/controller tests and confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because current preserve/expand logic still inherits too much recover
  narrowness

- [ ] **Step 3: Implement phase-specific floors**

Apply these rules:

- recover:
  - stable anchor
  - positive-family restoration
  - active objective-pressure escape family
- preserve:
  - low-regression family comparison
  - bounded gradient escape when needed
- expand:
  - frontier and diversity bias
  - budget throttles only after visibility invariants hold

Update `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py` so
trace metadata exposes:

- visible route families
- suppressed route families
- explicit suppress reasons

- [ ] **Step 4: Re-run the focused policy/controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

### Task 6: Run The Full Focused Test Gate

**Files:**

- No code changes expected; this is a verification gate

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

- [ ] **Step 2: If a test fails, fix only the failing contract before rerun**

Allowed next action:

- return to the task owning the failing file

Not allowed:

- start the official rerun with known failing focused tests

### Task 7: Run The New Official `s2_staged` `llm` Rerun

**Files:**

- Output only under `/home/hymn/msfenicsx/scenario_runs/s2_staged/`

- [ ] **Step 1: Launch the new official `llm` rerun**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx \
python -m optimizers.cli optimize-benchmark \
--optimization-spec scenarios/optimization/s2_staged_llm.yaml \
--evaluation-workers 2 \
--output-root ./scenario_runs/s2_staged
```

Expected:

- one new run root under `scenario_runs/s2_staged/` with canonical
  `__llm` naming

- [ ] **Step 2: Render the rerun assets**

Run:

```bash
NEW_LLM_RUN="$(ls -dt scenario_runs/s2_staged/*__llm | head -n1)"
/home/hymn/miniconda3/bin/conda run -n msfenicsx \
python -m optimizers.cli render-assets \
--run "$NEW_LLM_RUN"
```

Expected:

- updated `analytics/` and `figures/` under the new `llm` run

### Task 8: Compare Against The Old Official Suite And Answer The Paper Questions

**Files:**

- Output only under `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/`

- [ ] **Step 1: Create the comparison bundle**

Run:

```bash
NEW_LLM_RUN="$(ls -dt scenario_runs/s2_staged/*__llm | head -n1)"
COMPARE_OUT="./scenario_runs/compare_reports/s2_staged/$(date +%m%d_%H%M)__raw_union_old_vs_llm_recover_repair"
/home/hymn/miniconda3/bin/conda run -n msfenicsx \
python -m optimizers.cli compare-runs \
--run ./scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11 \
--run ./scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11 \
--run "$NEW_LLM_RUN" \
--output "$COMPARE_OUT"
```

Expected:

- a new comparison bundle with tables and figures for `raw`, `union`, and the
  repaired `llm`

- [ ] **Step 2: Run the controller audit against the new request traces**

Run:

```bash
NEW_LLM_RUN="$(ls -dt scenario_runs/s2_staged/*__llm | head -n1)"
export NEW_LLM_RUN
/home/hymn/miniconda3/bin/conda run -n msfenicsx python - <<'PY'
import json
import os
from pathlib import Path
from optimizers.analytics.staged_audit import summarize_prompt_contract_mismatches

run_root = Path(os.environ["NEW_LLM_RUN"])
rows = [json.loads(line) for line in (run_root / "traces" / "llm_request_trace.jsonl").open()]
print(json.dumps(summarize_prompt_contract_mismatches(rows), indent=2))
PY
```

Expected:

- zero silent phase mismatches
- zero hidden positive-credit requests, or only explicit stronger-negative
  suppressions

- [ ] **Step 3: Re-answer the required questions from the new evidence**

Answer exactly:

1. `llm` 是否终于超过 `union` 的 `first_feasible`？
2. `llm` 是否保持 final Pareto / hypervolume 优势？
3. `llm` 是否在 PDE solve 效率上更优？
4. 如果还没赢，具体卡在 recover / preserve / expand 哪段链路？

Use:

- the new comparison bundle
- the new `llm` run summaries
- the new audit summaries

Do not answer from memory or from the old run.
