# L1 Post-Feasible Attribution And Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make late-run controller phases locally attributable and add a generic post-feasible kernel that improves Pareto expansion through offline-first and bounded validation rather than unnecessary full reruns.

**Architecture:** Keep the validated reusable pre-feasible kernel, fixed action registry, repair, evaluation, and survival contracts unchanged. Add deterministic local phase attribution, frontier-aware state and diagnostics, then a generic post-feasible shortlist kernel with preserve/expand/recover modes. Validate first with deterministic tests and offline artifact reanalysis, then with bounded `seed11` and `seed17` live gates before considering any new full matched ladder.

**Tech Stack:** Python 3.12, pytest, JSON/JSONL artifact analysis, existing OpenAI-compatible client boundary, `pymoo`, FEniCSx runtime artifacts

---

## File Structure

### Phase Attribution And Client Contract

- Modify: `optimizers/operator_pool/llm_controller.py`
  Make local policy phase authoritative on all controller decisions and preserve provider-returned phase only as sidecar metadata.
- Modify: `llm/openai_compatible/client.py`
  Strengthen the `chat_compatible_json` output contract so the prompt explicitly asks for `selected_operator_id`, `phase`, and `rationale`, while still tolerating missing `phase` from live providers.
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_llm_client.py`

### Diagnostics And Artifact Reanalysis

- Modify: `optimizers/operator_pool/diagnostics.py`
  Support richer artifact inputs, phase backfill, post-feasible family summaries, and frontier-aware counters.
- Modify: `optimizers/cli.py`
  Extend `analyze-controller-trace` with optional artifact arguments for richer offline summaries while preserving backward compatibility.
- Modify: `tests/optimizers/test_optimizer_cli.py`

### Frontier-Aware State And Evidence

- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/reflection.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`

### Post-Feasible Kernel

- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`

### Reporting

- Modify: `docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md`
- Create: `docs/reports/R71_msfenicsx_l1_post_feasible_attribution_and_bounded_validation_20260401.md`

## Task 1: Freeze The Phase-Attribution Gap Into Deterministic Tests

**Files:**
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_llm_client.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing attribution tests**

Add tests that require:

```python
def test_llm_controller_records_local_policy_phase_even_without_active_guardrail():
    decision = controller.select_decision(_post_feasible_state_without_guardrail(), ...)
    assert decision.phase == "post_feasible_progress"
    assert decision.metadata["policy_phase"] == "post_feasible_progress"
```

```python
def test_chat_compatible_json_prompt_demands_phase_and_rationale_fields():
    client.request_operator_decision(...)
    system_prompt = fake_chat_api.last_kwargs["messages"][0]["content"].lower()
    assert "selected_operator_id" in system_prompt
    assert "phase" in system_prompt
    assert "rationale" in system_prompt
```

```python
def test_analyze_controller_trace_prefers_local_policy_phase_over_empty_provider_phase(tmp_path):
    summary = analyze_controller_trace(...)
    assert summary["post_feasible"]["decision_count"] == 3
    assert summary["unknown"]["decision_count"] == 0
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because late rows still lose local phase attribution and `chat_compatible_json` still only hard-requires `selected_operator_id`

- [ ] **Step 3: Commit the red tests**

```bash
git add \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "test: pin llm phase attribution contract"
```

## Task 2: Make Local Policy Phase Authoritative

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `llm/openai_compatible/client.py`
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_llm_client.py`

- [ ] **Step 1: Implement the minimal authoritative phase contract**

Implementation rules:

- set the returned `ControllerDecision.phase` from local kernel phase, not from provider payload
- persist local phase metadata on every decision, not only when guardrail metadata exists
- preserve provider-returned phase only as sidecar metadata such as `model_phase`
- keep operator selection, fallback behavior, repair, evaluation, and survival semantics unchanged
- strengthen `chat_compatible_json` system instructions so they explicitly ask for `phase` and `rationale`, but do not fail live runs when providers omit them

- [ ] **Step 2: Re-run the focused attribution tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py -v
```

Expected:

- PASS

- [ ] **Step 3: Commit**

```bash
git add \
  optimizers/operator_pool/llm_controller.py \
  llm/openai_compatible/client.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py
git commit -m "feat: make llm policy phase locally authoritative"
```

## Task 3: Extend Offline Diagnostics Before Any New Live Run

**Files:**
- Modify: `optimizers/operator_pool/diagnostics.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing diagnostics tests**

Add tests that require:

```python
def test_analyze_controller_trace_can_use_optimization_result_to_split_pre_and_post_feasible(tmp_path):
    summary = analyze_controller_trace(...)
    assert summary["post_feasible"]["decision_count"] > 0
```

```python
def test_analyze_controller_trace_reports_frontier_and_regression_metrics(tmp_path):
    summary = analyze_controller_trace(...)
    assert "recent_frontier_add_count" in summary["post_feasible"]
    assert "feasible_regression_count" in summary["post_feasible"]
```

```python
def test_optimizer_cli_analyze_controller_trace_accepts_optional_operator_and_request_sidecars(tmp_path):
    exit_code = main([...])
    assert exit_code == 0
    assert output_path.exists()
```

- [ ] **Step 2: Run the diagnostics tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because the analyzer currently only reads `controller_trace.json` and cannot reconstruct frontier-aware post-feasible summaries

- [ ] **Step 3: Implement richer offline artifact analysis**

Add optional inputs such as:

- `optimization_result`
- `operator_trace`
- `llm_request_trace`
- `llm_response_trace`

Required outputs:

- pre-feasible and post-feasible row counts
- rows before and after `first_feasible_eval`
- family mix after first feasible
- feasible regression count
- feasible preservation count
- frontier add count
- evaluations since frontier add
- post-feasible same-family streaks
- post-feasible speculative-family streaks

Keep the existing simple `--controller-trace` path working for backwards compatibility.

- [ ] **Step 4: Re-run the diagnostics tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/diagnostics.py \
  optimizers/cli.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "feat: extend offline llm trace diagnostics"
```

## Task 4: Add Frontier-Aware Generic State And Evidence Summaries

**Files:**
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/reflection.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write the failing state-summary tests**

Add tests that require:

```python
def test_build_controller_state_includes_frontier_aware_archive_state():
    state = build_controller_state(...)
    assert state.metadata["archive_state"]["pareto_size"] >= 1
    assert "evaluations_since_frontier_add" in state.metadata["archive_state"]
```

```python
def test_build_progress_state_distinguishes_post_feasible_expand_preserve_recover_modes():
    progress = build_progress_state(history=...)
    assert progress["post_feasible_mode"] in {"expand", "preserve", "recover"}
```

```python
def test_summarize_operator_history_reports_pareto_and_regression_evidence():
    summary = summarize_operator_history(...)
    assert "pareto_contribution_count" in summary["radiator_expand"]
    assert "feasible_regression_count" in summary["radiator_expand"]
```

- [ ] **Step 2: Run the focused state tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because current state summaries still center on single-best feasible progress and do not expose frontier-aware post-feasible evidence

- [ ] **Step 3: Implement the minimal generic frontier-aware summaries**

Add compact state blocks such as:

- `archive_state.pareto_size`
- `archive_state.recent_frontier_add_count`
- `archive_state.evaluations_since_frontier_add`
- `archive_state.recent_feasible_regression_count`
- `archive_state.recent_feasible_preservation_count`
- `progress_state.post_feasible_mode`
- `progress_state.recent_frontier_stagnation_count`
- `operator_summary[*].pareto_contribution_count`
- `operator_summary[*].feasible_regression_count`
- `operator_summary[*].post_feasible_avg_objective_delta`

Keep the summaries prompt-safe and fixed-size.

- [ ] **Step 4: Re-run the focused state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/domain_state.py \
  optimizers/operator_pool/reflection.py \
  optimizers/operator_pool/state_builder.py \
  tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add frontier-aware llm controller state summaries"
```

## Task 5: Add A Generic Post-Feasible Kernel

**Files:**
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing post-feasible kernel tests**

Add tests that require:

```python
def test_policy_kernel_enters_post_feasible_recover_when_frontier_regresses():
    policy = build_policy_snapshot(_post_feasible_regression_state(), ...)
    assert policy.phase == "post_feasible_recover"
```

```python
def test_policy_kernel_limits_unproven_expansion_families_during_post_feasible_recover():
    policy = build_policy_snapshot(_post_feasible_regression_state(), ...)
    assert "trusted_preserve" in {annotation["post_feasible_role"] for annotation in policy.candidate_annotations.values()}
```

```python
def test_llm_controller_prompt_includes_post_feasible_mode_guidance_without_operator_name_patch():
    controller.select_decision(_post_feasible_expand_state(), ...)
    assert "pareto" in fake_client.last_kwargs["system_prompt"].lower()
    assert "battery_to_warm_zone" not in fake_client.last_kwargs["system_prompt"]
```

- [ ] **Step 2: Run the focused kernel tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because current post-feasible behavior is still prompt-only and does not expose explicit preserve/expand/recover candidate shaping

- [ ] **Step 3: Implement the minimal post-feasible local kernel**

Implementation rules:

- add local post-feasible modes such as `post_feasible_expand`, `post_feasible_preserve`, and `post_feasible_recover`
- derive expansion versus preserve roles from generic outcome evidence, not operator-name exceptions
- add local same-family diversification and recovery guardrails after first feasible
- keep pre-feasible behavior unchanged unless a deterministic regression test requires a compatible update

- [ ] **Step 4: Re-run the focused kernel tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/policy_kernel.py \
  optimizers/operator_pool/llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py
git commit -m "feat: add generic post-feasible llm kernel"
```

## Task 6: Reanalyze Existing Full Artifacts Before Any New Live Run

**Files:**
- No source edits required

- [ ] **Step 1: Run the full deterministic optimizer test slice**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 2: Reanalyze the current `2026-04-01` full artifacts without live reruns**

Run enriched diagnostics on:

- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed11`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed23`

Required outputs:

- late-run rows are mostly attributable as `post_feasible_*` rather than `unknown`
- seed-level differences in post-feasible family mix and frontier contribution are now explainable from the new summaries

- [ ] **Step 3: Save a comparison summary artifact**

Write an aggregated local summary to a path such as:

- `scenario_runs/optimizations/diagnostics/2026-04-01-gpt54-post-feasible-design-gate-summary.json`

This summary becomes the no-provider decision gate for whether bounded live runs are justified.

## Task 7: Run Only Two Bounded Live Gates

**Files:**
- No repository source edits required

- [ ] **Step 1: Create temporary reduced-budget validation specs**

Clone the current live spec to `/tmp` for:

- `seed11`
- `seed17`

Keep matched:

- action registry
- provider/model
- repair
- evaluation spec
- algorithm seed

Reduce only generation count enough to expose a real post-feasible window.

- [ ] **Step 2: Run bounded `seed11`**

Run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec /tmp/<seed11-bounded-spec>.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-post-feasible-check/seed-11
```

Then analyze its controller trace.

Success conditions:

- no regression to pre-feasible collapse
- stronger post-feasible frontier-add and Pareto-contribution prefix metrics than the same-budget prefix of the current kernel

- [ ] **Step 3: Run bounded `seed17` regression guard**

Run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec /tmp/<seed17-bounded-spec>.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-post-feasible-check/seed-17
```

Then analyze its controller trace.

Success conditions:

- `prefeasible.max_speculative_family_streak` stays at `0`
- `first_feasible_eval` does not materially regress from the current validated kernel

- [ ] **Step 4: Stop if either bounded gate fails**

Do not run any new full `11/17/23` ladder if:

- `seed11` does not improve bounded post-feasible metrics
- `seed17` regresses on pre-feasible stability

## Task 8: Only If Both Bounded Gates Pass, Run The Next Full Ladder And Report

**Files:**
- Modify: `docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md`
- Create: `docs/reports/R71_msfenicsx_l1_post_feasible_attribution_and_bounded_validation_20260401.md`

- [ ] **Step 1: Run a new matched full `11/17/23` ladder**

Only after Task 7 passes.

- [ ] **Step 2: Build a comparison table**

Report at minimum:

- feasible rate
- first feasible evaluation
- Pareto size
- request count
- fallback count
- average provider latency
- post-feasible family mix
- frontier-add counts
- feasible-regression counts
- same-family streaks after first feasible

- [ ] **Step 3: Update the reporting docs**

Document:

- the attribution-contract repair
- the new frontier-aware summaries
- the new post-feasible kernel modes
- whether the bounded gains transferred to the full matched ladder
- whether the current kernel now beats `raw`, `union_uniform`, and the prior compact `L1` on the relevant post-feasible metrics

- [ ] **Step 4: Commit**

```bash
git add \
  docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md \
  docs/reports/R71_msfenicsx_l1_post_feasible_attribution_and_bounded_validation_20260401.md
git commit -m "docs: report post-feasible llm kernel validation"
```

## Execution Notes

- Treat `seed11` as the primary bounded post-feasible quality gate and `seed17` as the regression guard for pre-feasible stability.
- Do not spend a new full matched budget just to learn whether phase attribution can be reconstructed locally; that must be proven offline first.
- Prefer generic frontier-aware evidence and family-level role abstractions over operator-name patches.
- If a proposed post-feasible rule cannot be stated without naming one benchmark seed or one operator id, stop and redesign the abstraction before implementing it.
