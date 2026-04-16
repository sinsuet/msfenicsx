# LLM Controller End-to-End Stability Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a trustworthy `20x10 / 201 eval` `nsga2_llm` pipeline that can compare fairly against `raw` and `union`, while keeping objective-balance online and preventing duplicate-driven controller churn.

**Architecture:** Treat the current failure as an end-to-end control-loop problem, not an isolated prompt bug. Separate proposal attempts from accepted/evaluated offspring, move controller/policy/reflection accounting onto accepted events only, and add duplicate-aware diversification for deterministic semantic peak operators so escape-hatch visibility no longer explodes into duplicate-elimination churn.

**Tech Stack:** Python, pytest, pymoo, numpy, current `optimizers/` union adapter stack.

---

## Evidence Summary

- `0416_0224__llm` is the last valid matched-budget double-win run:
  - `best T_max = 305.1774`
  - `best grad_rms = 11.2548`
  - beats both `raw` and `union`
- `0416_1527__llm` is valid but regressed:
  - `best T_max = 306.3662`
  - `best grad_rms = 10.8682`
  - loses `T_max` to both baselines
- `0416_1548__llm` is **not** a valid comparison run:
  - `history_len = 184` instead of `201`
  - `controller_trace_len = 2426`
  - same `evaluation_index` repeated ~100 times
  - repaired-vector duplicate ratio reached `93.9%`

### Root Cause Clusters

1. **Accounting contamination**
   - `GeneticFamilyUnionMating` records `controller_trace` / `operator_trace` before pymoo repair + duplicate elimination.
   - `InfillCriterion.do()` may call `_do()` repeatedly until enough unique offspring survive.
   - Same `evaluation_index` is therefore reused across many proposal attempts.
   - `reflection.py`, `policy_kernel.py`, and `llm_controller.py` currently consume those attempt traces as if they were accepted/evaluated events.

2. **False evidence amplification**
   - `reflection._summarize_operator_outcomes()` joins `operator_trace` to history by `evaluation_index`.
   - When 100 proposal attempts share one `evaluation_index`, the same accepted child record is credited to many attempts.
   - This inflates:
     - `feasible_preservation_count`
     - `pareto_contribution_count`
     - `frontier_novelty_count`
     - `post_feasible` evidence
   - Those inflated counts then drive `preserve_fit`, `expand_fit`, `post_feasible_role`, and balance guidance.

3. **Duplicate-churn in deterministic peak operators**
   - `slide_sink` and `repair_sink_budget` are deterministic after parent/state selection.
   - In normal runs they already show high repaired-vector duplication.
   - Once both become visible escape-hatch candidates, pymoo duplicate elimination starts rejecting large fractions of offspring and repeatedly re-enters mating.
   - Eventually `n_max_iterations=100` short-circuits some generations, producing underfilled budgets like `184` instead of `201`.

4. **Guardrail feedback loop**
   - `recent_operator_dominance` uses recent controller trace windows.
   - Because those windows currently count rejected attempts, duplicate churn is misread as genuine recent preference.
   - The guardrail then narrows candidates further toward the same peak operators, increasing churn again.

---

### Task 1: Split Attempt Traces From Accepted Offspring Traces

**Files:**
- Modify: `optimizers/adapters/genetic_family.py`
- Modify: `optimizers/operator_pool/trace.py`
- Modify: `optimizers/drivers/union_driver.py`
- Test: `tests/optimizers/test_genetic_union_adapter.py` or new targeted adapter tests

- [ ] Introduce explicit attempt-vs-accepted trace semantics in the union genetic adapter.
- [ ] Keep proposal-attempt diagnostics, but do not let them masquerade as evaluated offspring.
- [ ] Override or wrap the current `InfillCriterion.do()` flow so repair + duplicate elimination can preserve source metadata for accepted offspring.
- [ ] Attach a stable per-attempt id / per-accepted-offspring id so later layers can join outcomes without relying on reused `evaluation_index`.
- [ ] Add trace fields for:
  - `accepted_for_evaluation`
  - `rejection_reason`
  - `duplicate_with_population`
  - `duplicate_within_batch`
  - `repair_collapsed_duplicate`
- [ ] Add regression tests showing that repeated `_do()` calls do not create multiple accepted trace rows for one evaluated child.

### Task 2: Re-base State, Reflection, And Guardrails On Accepted History

**Files:**
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `optimizers/operator_pool/reflection.py`
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Test: `tests/optimizers/test_llm_controller_state.py`
- Test: `tests/optimizers/test_llm_policy_kernel.py`
- Test: `tests/optimizers/test_llm_controller.py`

- [ ] Build `recent_decisions`, `recent_operator_counts`, and `operator_summary` from accepted/evaluated controller events only.
- [ ] Keep attempt-trace analytics separate and diagnostic-only.
- [ ] Change `reflection._summarize_operator_outcomes()` to score one accepted offspring against one evaluation outcome.
- [ ] Remove the possibility that repeated rejected attempts can inflate:
  - `evidence_level`
  - `preserve_fit`
  - `expand_fit`
  - `post_feasible_role`
- [ ] Change `recent_operator_dominance` to use accepted recent selections rather than raw attempt volume.
- [ ] Add tests proving that repeated rejected attempts do not produce fake preservation/frontier credit.

### Task 3: Add Duplicate-Aware Diversification For Deterministic Peak Operators

**Files:**
- Modify: `optimizers/operator_pool/operators.py`
- Modify: `optimizers/adapters/genetic_family.py`
- Possibly modify: `optimizers/operator_pool/state_builder.py`
- Test: `tests/optimizers/test_operator_pool_operators.py` or new focused optimizer tests

- [ ] Add bounded stochastic variants for deterministic sink operators:
  - `slide_sink`
  - `repair_sink_budget`
- [ ] Preserve operator semantics, but introduce small controlled variation so repeated parent/state pairs do not collapse to the same repaired vector.
- [ ] Add infill-local novelty gating inside the adapter:
  - compare repaired proposals against current generation accepted offspring and current population
  - if a candidate collapses to a duplicate, resample or route to a diversification fallback before asking pymoo to retry the entire infill loop
- [ ] Add duplicate-rate telemetry by operator/family.
- [ ] Optionally feed recent duplicate-rate back into applicability or candidate shaping, but only after accepted-trace accounting is fixed.

### Task 4: Restore Valid Comparison Criteria And Re-run Budget-Matched Evidence

**Files:**
- Modify: `optimizers/drivers/union_driver.py`
- Modify: `optimizers/llm_summary.py` or trace-summary utilities if needed
- Add/Modify docs under `docs/superpowers/`

- [ ] Define validity criteria for live `20x10` evidence:
  - `history_len == 201`
  - no generation shortfall
  - attempt/accepted ratio below a sanity threshold
  - no mass duplicate churn on one operator family
- [ ] Add summary diagnostics that surface:
  - attempts per generation
  - accepted offspring per generation
  - duplicate rejection counts by operator
  - accepted operator counts by generation
- [ ] Re-run `20x10` only after Tasks 1-3 land.
- [ ] Compare against:
  - `raw`
  - `union`
  - `0416_0224__llm`
- [ ] Only treat the rerun as valid if the budget is complete and trace accounting is clean.

---

## Implementation Order

1. **Fix accounting first**
   - Without accepted-trace semantics, every later live result can be contaminated.
2. **Then fix duplicate churn**
   - Otherwise deterministic peak operators can still collapse generations even if accounting is clean.
3. **Then re-tune balance behavior if necessary**
   - Only after the pipeline is trustworthy should we revisit policy weights or prompt phrasing.

## Non-Goals

- Do not change benchmark seed, objective definitions, evaluation spec, or paper-facing comparison class.
- Do not hardcode one-off rules for `slide_sink` or any specific run id.
- Do not use invalid runs like `0416_1548__llm` as performance evidence.

## Success Criteria

- `nsga2_llm` completes full `20x10 / 201 eval` live runs reliably.
- Accepted-trace and history accounting are one-to-one and auditable.
- Duplicate-driven infill churn is bounded and visible.
- `recent_operator_dominance` no longer reacts to rejected-attempt noise.
- A fresh valid rerun can be compared fairly to `raw`, `union`, and `0416_0224__llm`.
