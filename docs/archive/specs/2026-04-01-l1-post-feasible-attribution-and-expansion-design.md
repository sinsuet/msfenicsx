# L1 Post-Feasible Attribution And Expansion Design

Date: 2026-04-01

## Status

Proposed follow-up design after the reusable `L1` controller-kernel validation reported in:

- `docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md`

This design does not replace the validated reusable controller kernel.
It targets the next two open problems on the paper-facing `NSGA-II hybrid-union` `L1` line:

1. late-run `unknown` phase attribution
2. post-feasible Pareto expansion quality

## Goal

Extend the reusable optimizer-layer controller kernel so that:

- controller traces record deterministic local search phases even when the provider does not return a phase label
- cheap local diagnostics can separate true `post_feasible` behavior from missing-metadata `unknown` rows
- post-feasible controller logic uses generic frontier-aware evidence rather than prompt-only heuristics
- new work is validated through offline and bounded gates before any new full matched rerun

## Hard Constraints

The following remain non-negotiable:

- keep the paper-facing line on `NSGA-II` only
- keep the fixed union action registry unchanged
- keep repair unchanged
- keep the expensive thermal evaluation loop unchanged
- keep survival semantics unchanged
- do not add benchmark-specific, seed-specific, backbone-specific, or operator-name-specific permanent patches
- prefer provider-free and replay-style gates before any new live optimization runs

## Current Evidence Summary

The current reusable kernel has already validated the pre-feasible half of the problem:

- bounded fresh `seed17` gate passed with `prefeasible.max_speculative_family_streak=0`
- matched full `11/17/23` reruns improved average feasible rate and time-to-first-feasible relative to raw and the older compact `L1`

But the same validation exposed two remaining gaps.

### Gap 1: Late-Run `Unknown` Phase Attribution

The current runtime can compute local policy phases, but many late-run controller rows still fall into the diagnostics `unknown` bucket.

Observed evidence from the current matched full runs:

- `seed11`: many rows after `first_feasible_eval=57` still land in `unknown`
- `seed17`: `unknown_after_first_feasible=82`
- `seed23`: `unknown_after_first_feasible=64`

The root cause is architectural rather than numerical:

1. `state_builder` and `domain_state` already produce `progress_state.phase`
2. `policy_kernel.build_policy_snapshot(...)` already resolves a local phase
3. the final trace row still depends on `ControllerDecision.phase`
4. on the active `chat_compatible_json` path, provider payloads routinely omit `phase`
5. `guardrail_policy_phase` is written only when guardrail metadata exists, so non-guarded rows lose local phase attribution

This means most late-run `unknown` rows are not "truly unknown".
They are deterministic controller states whose phase was not serialized as a local authoritative field.

### Gap 2: Post-Feasible Pareto Expansion Is Still Weakly Kernelized

The current kernel uses hard local logic for:

- cold start
- pre-feasible family collapse prevention
- pre-feasible no-progress reset

But it uses only prompt guidance for post-feasible behavior.

Current state limitations:

- `build_progress_state(...)` still measures feasible progress through a scalarized `objective_score(...)`
- `archive_state` keeps only `best_feasible` and `best_near_feasible`, not frontier dynamics
- `operator_summary` is rich for feasibility entry and preservation, but thin for frontier contribution and feasible-regression behavior
- `post_feasible` has no local shortlist or diversification guardrail parallel to the pre-feasible kernel

So the current system is strongest at getting into the feasible region and weaker at controlling how the feasible frontier is expanded afterward.

## Root-Cause Chain

### A. Attribution Root Cause

The current `unknown` bucket is mostly caused by a contract mismatch:

- local kernel phase exists
- provider phase is optional in practice
- diagnostics trust either provider phase or guardrail-attached local phase
- late rows with no provider phase and no active guardrail become `unknown`

This is a serialization-contract issue, not a missing-search-state issue.

### B. Expansion Root Cause

The current post-feasible behavior is under-specified because the controller lacks a generic frontier-aware local abstraction.

The reusable kernel now answers:

- are we still before first feasible?
- are speculative families collapsing the search?
- has no-progress streak become large enough to force a stable-family reset?

It does not yet answer:

- are we preserving feasibility but not adding new frontier members?
- are we overusing one expansion family after first feasible?
- are recent custom-family actions improving feasible objective tradeoffs or only increasing regression risk?
- should the next post-feasible action prioritize preserve, expand, or recover?

Without those answers, post-feasible control stays mostly inside the `LLM` prompt and model behavior.

## Design Principles

### 1. Local Phase Must Be Authoritative

`policy_snapshot.phase` is optimizer-layer logic, not model creativity.
The local controller should always serialize its own resolved phase to the final trace contract.

Provider-returned `phase` can still be preserved as a sidecar for diagnostics, but it must not be the only source of truth.

### 2. Post-Feasible Progress Must Be Pareto-Aware

After first feasible, "progress" should not mean only "best scalar objective improved".
It should include frontier-aware signals such as:

- frontier additions
- feasible-preservation streaks
- feasible regression rate
- evaluations since last frontier addition
- family-conditioned contribution to frontier growth

### 3. Post-Feasible Policy Must Stay Generic

The next kernel must remain:

- scenario-agnostic
- portable across future backbones using the same action registry contracts
- framed in terms of stable family roles and evidence tiers

It must not become:

- "prefer `battery_to_warm_zone` on seed 11"
- "ban `radiator_expand` after eval 60"
- "special-case the current thermal benchmark"

### 4. Full Live Reruns Are The Last Gate

New work should pass three cheaper gates first:

1. deterministic tests
2. offline artifact diagnostics on existing full runs
3. bounded live validation on selected seeds

Only then should a new matched full rerun be considered.

## Proposed Architecture

### Layer 1: Deterministic Phase-Attribution Contract

Add a local authoritative phase contract for every controller decision.

Required behavior:

- every `ControllerDecision` emitted by the `LLM` controller carries a local `policy_phase`
- every controller trace row carries local phase metadata even when no guardrail is active
- provider phase becomes optional observational metadata such as `model_phase`
- diagnostics prefer local phase attribution first, then legacy fallbacks for older artifacts

Recommended serialized fields:

- `policy_phase`
- `policy_reason_codes`
- `policy_reset_active`
- `phase_source`
- `model_phase`
- `model_rationale_present`

The important change is not just a new field name.
The important change is that phase attribution becomes deterministic optimizer-layer state rather than a provider-dependent best effort.

### Layer 2: Offline-Enriched Diagnostics

Extend local diagnostics so that they can explain the post-feasible regime without any provider call.

Instead of reading only `controller_trace.json`, the enriched analyzer should be able to combine:

- `optimization_result.json`
- `controller_trace.json`
- `operator_trace.json`
- optional `llm_request_trace.jsonl`
- optional `llm_response_trace.jsonl`

Required derived diagnostics:

- pre-feasible versus post-feasible phase counts
- decisions before and after `first_feasible_eval`
- family mix after first feasible
- feasible-regression counts
- feasible-preservation counts
- frontier-add counts
- evaluations since last frontier addition
- post-feasible same-family streaks
- post-feasible speculative-family streaks
- operator-family contribution to final Pareto members

This layer is the primary cheap gate for design iterations.

### Layer 3: Frontier-Aware Generic State Summaries

Add compact controller-visible summaries that describe the feasible frontier rather than only the single best feasible record.

Recommended state additions:

#### `archive_state`

- `pareto_size`
- `recent_frontier_add_count`
- `evaluations_since_frontier_add`
- `recent_feasible_regression_count`
- `recent_feasible_preservation_count`
- `best_feasible`
- `best_near_feasible`

#### `progress_state`

- `phase`
- `first_feasible_found`
- `evaluations_since_first_feasible`
- `recent_no_progress_count`
- `recent_frontier_stagnation_count`
- `post_feasible_mode`
  - `preserve`
  - `expand`
  - `recover`

#### `operator_summary`

- `feasible_entry_count`
- `feasible_preservation_count`
- `feasible_regression_count`
- `pareto_contribution_count`
- `frontier_novelty_count`
- `post_feasible_avg_objective_delta`
- `post_feasible_avg_violation_delta`
- `evidence_level`
- `operator_family`

These additions remain compact and prompt-safe, but they give the controller a real post-feasible state abstraction.

### Layer 4: Post-Feasible Local Policy Kernel

Add local post-feasible candidate shaping parallel to the existing pre-feasible kernel.

Recommended local modes:

- `post_feasible_expand`
- `post_feasible_preserve`
- `post_feasible_recover`

Recommended generic behaviors:

#### `post_feasible_expand`

Used when feasibility is stable but frontier growth is stalled.

Behavior:

- allow stable families plus supported expansion families
- discourage repeated same-family expansion streaks
- prefer families with positive frontier contribution evidence

#### `post_feasible_preserve`

Used when the frontier is still growing and feasibility regressions are low.

Behavior:

- keep preserve-capable and low-regression families visible
- avoid unnecessary family-level forcing
- prevent one operator from monopolizing late-run decisions

#### `post_feasible_recover`

Used when feasible regression increases or frontier growth collapses after first feasible.

Behavior:

- temporarily narrow candidates toward trusted preserve-capable families
- reduce risky expansion actions that have poor preservation evidence
- exit recovery mode once preservation stabilizes

The kernel must still avoid operator-name-specific rules.
Family and evidence categories should be derived from outcome statistics, not hardcoded operator identities.

### Layer 5: Validation Ladder

The validation ladder should explicitly avoid unnecessary full reruns.

#### Gate A: Deterministic Contract Tests

No live run.

Required outcomes:

- phase attribution persists without provider phase
- diagnostics no longer classify most post-feasible rows as `unknown`
- post-feasible state summaries are stable and bounded in size

#### Gate B: Offline Artifact Reanalysis

No live run.

Reanalyze existing:

- `2026-04-01-kernel-validation-seed11`
- `2026-04-01-kernel-validation-seed17`
- `2026-04-01-kernel-validation-seed23`

Required outcomes:

- late-run rows are attributable as true `post_feasible` rather than `unknown`
- seed-level differences in frontier dynamics become explainable
- post-feasible family statistics distinguish stronger and weaker runs without any new solve

#### Gate C: Bounded Live Validation

Only after Gates A and B pass.

Recommended seeds:

- `seed11` for post-feasible expansion quality
- `seed17` as a regression guard for pre-feasible stability

Recommended bounded rule:

- use reduced-generation runs that still expose a real post-feasible window
- compare against the same-budget prefix of the current validated kernel

Required outcomes:

- `seed17` does not regress on pre-feasible stability
- `seed11` improves bounded post-feasible frontier metrics

#### Gate D: Full Matched Rerun

Only after Gate C passes.

Run a new full `11/17/23` ladder only if the bounded gates show real post-feasible benefit.

## Acceptance Criteria

This design should be considered implemented only when all of the following are true:

1. current and future full artifacts no longer depend on provider-returned phase for usable phase attribution
2. most late-run rows that are currently `unknown` can be classified as `post_feasible_*`
3. offline diagnostics can explain post-feasible family mix and frontier contribution without any live rerun
4. bounded `seed11` validation shows improved post-feasible frontier growth versus the current kernel at the same budget prefix
5. bounded `seed17` validation retains the current pre-feasible stabilization gains
6. only then is a new full matched rerun justified

## Non-Goals

This design does not propose:

- expanding to additional backbones
- changing the action registry
- adding benchmark-specific controller exceptions
- claiming immediate full-method superiority before bounded post-feasible validation
