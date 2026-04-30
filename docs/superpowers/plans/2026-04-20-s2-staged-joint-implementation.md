# S2 Staged Joint Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Status: historical S2 implementation plan; current active paper-facing debugging has moved to `s5_aggressive15` in the S5-S7 family.

**Goal:** Advance `s2_staged` as the paper-facing S2 candidate, with benchmark structure and portable controller redesign that let `llm` beat `raw` and `union` for the right reasons.

**Architecture:** The source of truth is `docs/superpowers/specs/2026-04-20-s2-staged-joint-design.md`. This is a joint redesign. The benchmark is recalibrated on the repaired optimizer baseline, and the controller is redesigned through portable state-conditioned route-family policy rather than benchmark-specific hacks.

**Tech Stack:** Python 3.11+, FEniCSx, pymoo, pytest, PyYAML, conda env `msfenicsx`.

---

## File Structure

### New benchmark inputs

- create `scenarios/templates/s2_staged.yaml`
- create `scenarios/evaluation/s2_staged_eval.yaml`
- create `scenarios/optimization/s2_staged_raw.yaml`
- create `scenarios/optimization/s2_staged_union.yaml`
- create `scenarios/optimization/s2_staged_llm.yaml`
- create `scenarios/optimization/profiles/s2_staged_raw.yaml`
- create `scenarios/optimization/profiles/s2_staged_union.yaml`

### Controller and state files expected to change

- modify `optimizers/operator_pool/domain_state.py`
- modify `optimizers/operator_pool/state_builder.py`
- modify `optimizers/operator_pool/policy_kernel.py`
- modify `optimizers/operator_pool/llm_controller.py`
- modify `optimizers/operator_pool/reflection.py`
- modify `optimizers/operator_pool/prompt_projection.py`
- modify `optimizers/operator_pool/route_families.py`
- modify `optimizers/operator_pool/diagnostics.py`

### Trace and artifact files expected to change

- modify `optimizers/artifacts.py`
- modify `optimizers/traces/llm_trace_io.py`
- add any new optimizer analytics helper under `optimizers/analytics/` only if
  needed for promotion-gate reporting

### Focused tests expected to change or be added

- create `tests/generator/test_s2_staged_template.py`
- create `tests/optimizers/test_s2_staged_baseline.py`
- create `tests/optimizers/test_s2_staged_controller_audit.py`
- update focused controller tests under `tests/optimizers/`

### Docs to update only after promotion

- `README.md`
- `AGENTS.md`
- relevant docs under `docs/`

---

## Task 1: Consolidate Active S2 Docs Around `s2_staged`

**Files:**

- modify `README.md`
- modify `AGENTS.md`
- modify active docs under `docs/`

- [ ] Remove retired S2 scenario names and paths from active guidance
- [ ] Point future workers at the `s2_staged` design and execution docs
- [ ] Keep active repository guidance self-consistent after the retirement

## Task 2: Build A Reproducible Audit Harness Before Retuning

**Files:**

- create `tests/optimizers/test_s2_staged_controller_audit.py`
- create a small analytics helper under `optimizers/analytics/` only if a test
  helper is not enough

- [ ] Add a focused audit that compares matched `raw`, `union`, and `llm` run
      `traces/evaluation_events.jsonl` prefixes and confirms exactly where the
      shared prefix ends
- [ ] Add a focused audit that counts unique LLM `decision_id` values instead of
      raw duplicated controller rows
- [ ] Add a focused audit that reports both:
  - raw trace `eval_index`
  - normalized run-summary `first_feasible_eval`
- [ ] Add a focused audit that measures effective candidate pool size, visible
      route families, `semantic_trial_mode`, and `route_family_mode`
- [ ] Add a focused audit that attributes the first feasible offspring to the
      operator that generated it
- [ ] Add a focused audit that reports whether `gradient_improve` prompts expose
      any `congestion_relief` family

**Checkpoint:** We should be able to prove future controller-sensitive claims
from tests and batch analytics, not only by manually reading prompt markdown.

## Task 3: Create The New Benchmark Identity

**Files:**

- create `scenarios/templates/s2_staged.yaml`
- create `scenarios/evaluation/s2_staged_eval.yaml`
- create `scenarios/optimization/s2_staged_raw.yaml`
- create `scenarios/optimization/s2_staged_union.yaml`
- create `scenarios/optimization/s2_staged_llm.yaml`
- create `scenarios/optimization/profiles/s2_staged_raw.yaml`
- create `scenarios/optimization/profiles/s2_staged_union.yaml`

- [ ] Create the `s2_staged` scenario family with its own ids, specs, and
      profiles
- [ ] Update all ids, descriptions, and profile metadata consistently
- [ ] Preserve the same decision-variable structure and paper ladder
- [ ] Keep `union` and `llm` on the same operator pool and the same union
      profile path unless a profile split is required for apples-to-apples
      controller diagnostics

## Task 4: Add A Baseline Acceptance Harness For `s2_staged`

**Files:**

- create `tests/generator/test_s2_staged_template.py`
- create `tests/optimizers/test_s2_staged_baseline.py`

- [ ] Generate the benchmark seed-11 case
- [ ] Evaluate the generated baseline directly
- [ ] Evaluate the repaired optimizer baseline through
      `ThermalOptimizationProblem.evaluate_baseline()`
- [ ] Assert the repaired baseline has:
  - exactly one dominant positive constraint
  - `c02_peak_temperature_limit` as the dominant id
  - total positive violation in the `2.5-4.0` target band
  - `hotspot_inside_sink_window = false`
  - `nearest_neighbor_gap_min <= 0.06`
  - `hottest_cluster_compactness <= 0.13`
  - `sink_budget_bucket in {tight, full_sink}`

**Checkpoint:** No controller work should be calibrated against a benchmark that
has not yet passed the repaired-baseline gate.

## Task 5: Calibrate The Shared Prefix To Stay Infeasible

**Files:**

- modify `scenarios/templates/s2_staged.yaml`
- modify `scenarios/evaluation/s2_staged_eval.yaml`
- update the new baseline tests if target numbers are tuned

- [ ] Tune physics and layout so the repaired baseline stays meaningfully
      harder than the earlier scenario-first calibration without recreating an
      over-hard stress case
- [ ] Run matched `raw`, `union`, and `llm` `20 x 10` dry comparisons with the
      official seeds
- [ ] Assert from `traces/evaluation_events.jsonl` that optimizer eval rows
      `1-20` are identical and infeasible for all three modes
- [ ] Assert no mode reaches feasibility before the first controller-side
      divergence
- [ ] If any feasible point appears in the shared prefix, return to scenario
      calibration instead of softening controller gates

**Checkpoint:** The staged benchmark stays infeasible through the entire shared
pre-controller optimizer prefix at official `20 x 10`.

## Task 6: Redesign `prefeasible_convert` As A Route-Family Entry Window

**Files:**

- modify `optimizers/operator_pool/policy_kernel.py`
- modify `optimizers/operator_pool/llm_controller.py`
- modify `optimizers/operator_pool/domain_state.py`
- modify `optimizers/operator_pool/state_builder.py`
- update focused tests under `tests/optimizers/`

- [ ] Stop `prefeasible_convert` from collapsing to stable-only candidates when
      non-stable entry families remain state-applicable
- [ ] Guarantee a bounded entry floor that can expose:
  - one stable route
  - one sink or budget entry family
  - one spread or congestion entry family
- [ ] Use prompt-visible state to activate these entry floors:
  - objective balance
  - crowding
  - compact cluster state
  - sink alignment
- [ ] Enable route-family reasoning and bounded semantic-entry trials during
      `prefeasible_convert`, not only after first feasible

**Checkpoint:** In the official failure window class, `llm` no longer reaches
`prefeasible_convert` with an all-stable effective pool.

## Task 7: Redesign Recover And Preserve Around Route-Family Floors

**Files:**

- modify `optimizers/operator_pool/policy_kernel.py`
- modify `optimizers/operator_pool/domain_state.py`
- modify `optimizers/operator_pool/state_builder.py`

- [ ] Replace the single-semantic recover floor with state-conditioned
      route-family floors
- [ ] Add a symmetric gradient-congestion escape family to match the existing
      peak-sink escape family
- [ ] Keep a stable floor, but do not allow recover to suppress all congestion
      routes when the state says gradient pressure is dominant

**Checkpoint:** Under `gradient_improve`, effective LLM pools should expose at
least one `congestion_relief` family candidate most of the time.

## Task 8: Activate Route-Family Reasoning Outside Expand

**Files:**

- modify `optimizers/operator_pool/llm_controller.py`
- modify `optimizers/operator_pool/prompt_projection.py`
- modify `optimizers/operator_pool/state_builder.py`

- [ ] Allow `route_family_mode` and bounded semantic-trial logic in
      `prefeasible_convert`, recover, and preserve, not only in expand
- [ ] Keep the route comparison bounded and state-triggered
- [ ] Expose route-family candidates and reasons directly in request-side trace
      rows, not only in markdown prompt bodies
- [ ] Preserve fairness: the final action is still one operator chosen from the
      same shared registry used by `union`

**Checkpoint:** A controller audit should show non-`none` route-family mode
appearing before first feasible, not only after the first post-feasible expand
window.

## Task 9: Extend Reflection And Credit Beyond Expand

**Files:**

- modify `optimizers/operator_pool/reflection.py`
- modify `optimizers/operator_pool/route_families.py`
- modify `optimizers/operator_pool/state_builder.py`
- update any focused controller tests affected by the new credit model

- [ ] Record route-family credit in `prefeasible_convert`, recover, preserve,
      and expand
- [ ] Separate penalty-coded failure deltas from normal violation deltas so
      prefeasible retrieval evidence is not dominated by `1e12` artifacts
- [ ] Keep separate counts for:
  - feasible preservation
  - feasible regression
  - frontier add
  - objective-direction improvement
- [ ] Index route-family credit by compact regime keys rather than benchmark id
- [ ] Make the prompt surface aware of both positive and negative recent route
      evidence

**Checkpoint:** A route family filtered in one phase should still be able to
accumulate useful credit from recover and preserve, not only from expand.

## Task 10: Add Macro-To-Micro Handoff Logic

**Files:**

- modify `optimizers/operator_pool/policy_kernel.py`
- modify `optimizers/operator_pool/llm_controller.py`
- update focused tests under `tests/optimizers/`

- [ ] Detect semantic milestone events such as:
  - first feasible entry
  - frontier add
  - objective milestone
- [ ] After a semantic milestone, open a bounded handoff window that restores
      `local_refine` and `native_sbx_pm`
- [ ] Prevent endless semantic macro moves after the controller has already
      recovered a good feasible basin

**Checkpoint:** The next official run should show semantic recovery followed by
native or local finishing, not semantic saturation or recover-only looping.

## Task 11: Upgrade Trace And Artifact Surfaces For Promotion-Gate Analytics

**Files:**

- modify `optimizers/artifacts.py`
- modify `optimizers/traces/llm_trace_io.py`
- modify `optimizers/operator_pool/diagnostics.py`
- add any needed analytics rollup under `optimizers/analytics/`

- [ ] Materialize unique-decision analytics alongside raw controller rows
- [ ] Persist effective pool size, visible route families, and filtered route
      families per decision
- [ ] Persist enough linkage to identify which operator produced the first
      feasible offspring without manual prompt joins
- [ ] Add route-family visibility summaries to controller diagnostics
- [ ] Keep prompt markdown dumps, but make the JSONL sidecars sufficient for
      audit scripts

**Checkpoint:** Promotion-gate analytics should no longer require reparsing all
`prompts/*.md` files.

## Task 12: Validation Ladder

### Stage A: Focused tests

- [ ] Run:
  - `conda run -n msfenicsx pytest tests/generator/test_s2_staged_template.py tests/optimizers/test_s2_staged_baseline.py tests/optimizers/test_s2_staged_controller_audit.py -v`
- [ ] Run the focused controller test files touched by Tasks 6-11

### Stage B: `10 x 5` smoke

- [ ] Run matched `raw`, `union`, and `llm` smoke comparisons with
      `--evaluation-workers 2`
- [ ] Confirm trace sidecars, prompt refs, and materialized decision analytics
      are present
- [ ] Confirm LLM runtime still has:
  - `fallback_count = 0`
  - `schema_invalid_count = 0`
  - `semantic_invalid_count = 0`

### Stage C: official `20 x 10`

- [ ] Run the official matched comparison
- [ ] Require:
  - from `traces/evaluation_events.jsonl`, optimizer eval rows `1-20` are
    identical and infeasible across all modes
  - no mode reaches feasibility before the first controller-side divergence
  - non-stable route visibility during `prefeasible_convert`
  - first-feasible attribution is materialized and points to a traceable
    operator event
  - LLM first feasible earlier than both baselines
  - visible recover, preserve, and expand phases in unique LLM decisions
  - non-trivial congestion-family visibility under `gradient_improve`
  - LLM final best peak and gradient both better than `union`

### Stage D: paper-facing `32 x 16`

- [ ] Run the extended matched comparison
- [ ] Compute feasible-only PDE milestone curves for both objectives
- [ ] Require:
  - LLM best peak better than `raw` and `union`
  - LLM best gradient better than `raw` and `union`
  - LLM feasible rate within `0.10` of the best baseline
  - the milestone gate from the spec passes for both objectives

## Task 13: Promote Only After Gates Pass

**Files:**

- modify `README.md`
- modify `AGENTS.md`
- update any active docs that reference the paper-facing S2 identity

- [ ] Historical step: after Tasks 1-12 passed, promote `s2_staged` as the
      paper-facing S2 candidate for that phase
- [ ] Historical step: promote `s2_staged` as the only paper-facing S2 candidate
      in then-active guidance
- [ ] Remove retired S2 docs and artifact roots from active references
