# L1 Domain-Grounded Controller State Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the paper-facing `L1` `NSGA-II` union-`LLM` controller so live decisions are grounded in compact parent, feasibility, violation, objective, archive, and regime summaries rather than only recent action history.

**Architecture:** Keep the already validated OpenAI-compatible client boundary, mixed union action registry, repair, expensive evaluation loop, and native `NSGA-II` survival unchanged. Add a compact domain-state layer that summarizes current parents, optimizer progress, archive status, and operator outcome credit from `problem.history`, the active population, and existing traces, then feed only those fixed-size summaries into the `LLM` prompt so the controller becomes more state-aware without exploding token cost.

**Tech Stack:** Python 3.12, NumPy, `pymoo`, pytest, OpenAI Python SDK, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`)

---

Spec references:

- `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`
- `docs/superpowers/specs/2026-03-28-openai-union-llm-controller-design.md`

Current-state references:

- `docs/superpowers/plans/2026-03-28-openai-compatible-union-llm-controller.md`
- `docs/superpowers/plans/2026-03-31-l1-llm-stability-diagnostics-and-repair.md`
- `scenario_runs/optimizations/diagnostics/2026-03-31-nsga2-multiseed-comparison-summary.json`

Status context:

- the OpenAI-compatible live route is now transport-stable with `GPT-5.4`
- the current implemented prompt/state is intentionally compact and mostly history-driven
- the original March 28 design expected richer domain-grounded state, including parent vectors, feasibility, dominant violations, and archive summaries
- the next step is to close that implementation gap without changing the fairness contract between `P1` and `L1`

## Status Update - 2026-03-31

- The core state-completion scope of this plan is now implemented in the active code path: compact `run_state`, `parent_state`, `archive_state`, `domain_regime`, and operator-outcome credit are present in the live `L1` controller prompt contract.
- Live smoke and full runs confirmed that richer state alone does not guarantee more stable search behavior; multi-seed evidence showed improved best-case feasibility on some seeds but higher variance on others.
- The remaining gap is therefore no longer "add more benchmark-specific state fields" by default. The remaining gap is to extract a reusable controller-policy kernel that interprets compact state through portable search-phase, evidence-tier, family-level anti-collapse, and progress-reset mechanisms.
- Future work derived from this plan should treat domain-grounded summaries as reusable optimizer-layer context blocks, not as justification for one-scenario prompt tuning or one-operator special cases.

## File Structure

### Domain-State And Regime Layer

- Create: `optimizers/operator_pool/domain_state.py`
  Build compact run, parent, archive, and regime summaries from the active population and `problem.history`.
- Modify: `optimizers/operator_pool/state_builder.py`
  Replace the current mostly-trace-only metadata assembly with a richer but fixed-size domain-state payload.
- Modify: `optimizers/operator_pool/reflection.py`
  Extend operator summaries with outcome credit such as feasible-entry, feasible-preservation, and violation deltas.
- Modify: `tests/optimizers/test_llm_controller_state.py`

### Runtime Wiring Layer

- Modify: `optimizers/adapters/genetic_family.py`
  Pass active parent population members, evaluation budget counters, and `problem.history` summaries into the state builder while preserving native mating and survival.
- Modify: `optimizers/operator_pool/trace.py`
  Keep trace rows joinable to later evaluation outcomes if additional parent-summary metadata is needed.
- Modify: `tests/optimizers/test_operator_pool_adapters.py`

### Prompt Contract Layer

- Modify: `optimizers/operator_pool/llm_controller.py`
  Teach the prompt builder to serialize only the approved compact domain-state blocks, not raw large payloads.
- Modify: `tests/optimizers/test_llm_controller.py`

### Documentation

- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`
- Create: `docs/superpowers/plans/2026-03-31-l1-domain-grounded-controller-state-completion.md`

## Task 1: Pin The Missing Domain-Grounded State In Tests

**Files:**
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing state-shape tests**

Add tests that require:

```python
def test_build_controller_state_includes_parent_run_archive_and_regime_blocks():
    state = build_controller_state(...)
    assert state.metadata["run_state"]["evaluations_used"] == 37
    assert state.metadata["parent_state"]["parents"][0]["decision_vector"]["processor_x"] == pytest.approx(0.22)
    assert state.metadata["archive_state"]["best_feasible"]["evaluation_index"] == 28
    assert state.metadata["domain_regime"]["phase"] == "near_feasible"
```

```python
def test_operator_summary_tracks_feasible_entry_preservation_and_violation_delta():
    summary = summarize_operator_history(...)
    assert summary["hot_pair_to_sink"]["feasible_entry_count"] == 2
    assert summary["local_refine"]["avg_total_violation_delta"] < 0.0
```

```python
def test_llm_controller_user_prompt_serializes_compact_domain_grounded_blocks_only():
    decision = controller.select_decision(...)
    payload = json.loads(fake_client.last_kwargs["user_prompt"])
    assert "parent_state" in payload["metadata"]
    assert "archive_state" in payload["metadata"]
    assert "domain_regime" in payload["metadata"]
    assert "case_reports" not in fake_client.last_kwargs["user_prompt"]
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because the current state builder only exposes compact trace/history fields

- [ ] **Step 3: Commit the red tests**

```bash
git add \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py
git commit -m "test: pin missing domain-grounded llm state"
```

## Task 2: Implement Compact Domain-State Summaries

**Files:**
- Create: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `optimizers/operator_pool/reflection.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Add the failing helper tests if Task 1 did not already cover them**

Add focused tests for helpers such as:

```python
def test_build_parent_state_summarizes_feasibility_violation_and_objectives():
    parent_state = build_parent_state(...)
    assert parent_state["parents"][0]["feasible"] is False
    assert parent_state["parents"][0]["dominant_violation"]["constraint_id"] == "battery_temp_upper"
```

```python
def test_build_archive_state_tracks_best_feasible_and_near_feasible_records():
    archive_state = build_archive_state(history, ...)
    assert archive_state["best_near_feasible"]["total_violation"] < 1.0
```

- [ ] **Step 2: Run the focused state tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because `domain_state.py` and richer summaries do not exist yet

- [ ] **Step 3: Implement the minimal helper layer**

Create helpers that build only compact summaries:

- `run_state`
  - `generation_index`
  - `decision_index`
  - `evaluations_used`
  - `evaluations_remaining`
  - `feasible_rate`
  - `first_feasible_eval`
- `parent_state`
  - parent indices
  - parent decision vectors
  - parent feasibility
  - total violation
  - dominant active violation
  - feasible-only objective summary
- `archive_state`
  - best near-feasible record
  - best feasible record
  - compact Pareto/front diversity summary
- `domain_regime`
  - `far_infeasible`
  - `near_feasible`
  - `feasible_refine`
  - dominance tag such as `hot_dominant`, `cold_dominant`, `geometry_dominant`, or `mixed`

Do not forward raw `case_reports`, field data, or unbounded history slices.

- [ ] **Step 4: Extend operator reflection with outcome credit**

Use `controller_trace`, `operator_trace`, and joined evaluation outcomes to compute:

- `feasible_entry_count`
- `feasible_preservation_count`
- `avg_total_violation_delta`
- `avg_feasible_objective_delta`
- `recent_helpful_regimes`
- `recent_harmful_regimes`

- [ ] **Step 5: Re-run the state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/operator_pool/domain_state.py \
  optimizers/operator_pool/state_builder.py \
  optimizers/operator_pool/reflection.py \
  tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add domain-grounded llm state summaries"
```

## Task 3: Wire Parent And History Context Through The NSGA-II Union Adapter

**Files:**
- Modify: `optimizers/adapters/genetic_family.py`
- Modify: `optimizers/operator_pool/trace.py`
- Modify: `tests/optimizers/test_operator_pool_adapters.py`

- [ ] **Step 1: Write the failing integration tests**

Add tests that require:

```python
def test_genetic_union_mating_builds_llm_state_from_population_and_problem_history(monkeypatch):
    ...
```

```python
def test_controller_trace_rows_remain_joinable_to_parent_and_child_outcomes(monkeypatch):
    ...
```

- [ ] **Step 2: Run the adapter tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py -v
```

Expected:

- FAIL because the current adapter only passes parent bundles plus trace buffers into `build_controller_state`

- [ ] **Step 3: Implement the minimal runtime wiring**

In `optimizers/adapters/genetic_family.py`:

- derive parent summaries from the selected population rows
- pass `problem.history`
- pass evaluation budget counters derived from `population_size`, `num_generations`, and `problem._next_evaluation_index`
- preserve the exact native fast path and current union action registry

If necessary, add compact parent-summary metadata to trace rows, but do not duplicate large payloads.

- [ ] **Step 4: Re-run the adapter tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/adapters/genetic_family.py \
  optimizers/operator_pool/trace.py \
  tests/optimizers/test_operator_pool_adapters.py
git commit -m "feat: wire domain-grounded llm state into nsga2 union mating"
```

## Task 4: Update The Prompt Contract Without Re-Inflating It

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing prompt-contract tests**

Add tests that require:

```python
def test_llm_controller_prompt_includes_parent_archive_and_regime_blocks():
    ...
```

```python
def test_llm_controller_prompt_does_not_forward_raw_case_reports_or_full_history():
    ...
```

- [ ] **Step 2: Run the prompt tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because the prompt still serializes the older compact trace-only schema

- [ ] **Step 3: Implement the prompt update**

Keep:

- the same OpenAI-compatible client boundary
- the same action registry and guardrail logic
- the same fallback behavior

Change only the user-prompt schema so it includes compact:

- `run_state`
- `parent_state`
- `archive_state`
- `operator_summary`
- `domain_regime`
- `recent_decisions`

Do not add free-form chain-of-thought requests or raw thermal fields.

- [ ] **Step 4: Re-run the prompt tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/llm_controller.py \
  tests/optimizers/test_llm_controller.py
git commit -m "feat: prompt llm controller with domain-grounded compact state"
```

## Task 5: Calibrate Documentation And Re-Verify The L1 Line

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`
- Create: `docs/superpowers/plans/2026-03-31-l1-domain-grounded-controller-state-completion.md`

- [ ] **Step 1: Update docs to separate current implementation from target architecture**

Document that:

- the live `L1` route is transport-stable today
- the current controller-visible state is compact and history-driven
- fuller parent/objective/violation/archive grounding remains an explicit follow-up plan

- [ ] **Step 2: Run focused verification**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 3: Run one fresh live smoke with the richer state**

Run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx \
  python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_smoke.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-smoke/<date>-domain-grounded
```

Expected:

- successful live structured decisions
- `fallback_count == 0`
- prompt/trace artifacts showing the new compact domain-grounded blocks

- [ ] **Step 4: Commit**

```bash
git add \
  README.md \
  AGENTS.md \
  docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md \
  docs/superpowers/plans/2026-03-31-l1-domain-grounded-controller-state-completion.md
git commit -m "docs: add follow-up plan for domain-grounded l1 state"
```
