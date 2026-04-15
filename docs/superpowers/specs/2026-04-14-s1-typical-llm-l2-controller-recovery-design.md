# S1 Typical L2 LLM Controller Recovery Design

## Context

The active paper-facing ladder for `s1_typical` is:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

The intended paper contract remains fixed:

- all three routes optimize the same `32D` decision encoding
- all three routes use the same case template, repair, cheap constraints, PDE solve, evaluation spec, and survival semantics
- `raw` uses native `NSGA-II` proposal only
- `union` and `llm` share the same fixed mixed operator registry
- `union` and `llm` differ only by controller

The repository now has a completed live `s1_typical` `llm` run under the rebuilt mainline:

- `scenario_runs/s1_typical/0414_1618__llm/`

That live run matters because it separates two questions:

1. is the end-to-end live `LLM` route runnable and physically credible?
2. does the current `LLM` controller actually realize the intended paper story of semantic mixed-action scheduling?

The answer is now split:

- the route is runnable and physically credible
- the current controller does not yet realize the intended semantic-action scheduling story

## Validated Facts From The Current Live Run

### Runtime And Transport Facts

The current `s1_typical` `LLM` route is live-runnable with:

- `provider: openai-compatible`
- `model: gpt-5.4`
- `base_url: https://rust.cat/v1`
- `capability_profile: chat_compatible_json`

The current live path is no longer blocked by the older SDK transport boundary.
The repository already uses a direct HTTP chat-compatible JSON path for live requests.

The completed live run reports:

- `request_count = 436`
- `response_count = 430`
- `fallback_count = 6`
- `retry_count = 1`
- `invalid_response_count = 7`
- `schema_invalid_count = 7`
- `semantic_invalid_count = 0`
- `elapsed_seconds_avg ~= 7.65`
- `elapsed_seconds_max ~= 45.24`

So the current blocker is not provider unavailability and not repeated semantic registry violations.

### Optimization Outcome Facts

Matched seed-11 aggregate outcomes currently show:

- `raw`
  - feasible rate `0.7641`
  - Pareto size `5`
  - `min_peak = 304.4342`
  - `min_grad = 9.6598`
- `union`
  - feasible rate `0.8226`
  - Pareto size `7`
  - `min_peak = 305.8794`
  - `min_grad = 10.9995`
- `llm`
  - feasible rate `0.7641`
  - Pareto size `5`
  - `min_peak = 305.5797`
  - `min_grad = 10.7274`

Current interpretation:

- `raw` is strongest on extreme single-point optima
- `union` is strongest on balanced Pareto expansion and feasible-set width
- current `llm` is live-runnable but does not recover the `union` semantic-action advantage

### Physics And Realism Facts

Representative bundles for `raw`, `union`, and `llm` are numerically self-consistent:

- no `NaN` values in the saved thermal fields
- saved field minima and maxima match evaluation summaries exactly
- hotspot positions and sink placement produce physically plausible trade-offs
- shorter sink spans produce smoother gradients but higher peak temperatures
- larger sink spans reduce peak temperatures as expected

So the current problem is not a physics corruption issue and not an artifact-fraud issue.

### First-Feasible Interpretation Caveat

For `seed-11`, the controller starts making decisions only after the initial population is already evaluated.
In the current run layout:

- first controller decision occurs at `evaluation_index = 34`
- the run already has a feasible point earlier in the baseline-included history
- under the optimizer-progress-only interpretation, first feasible still occurs before controller activation matters

Therefore `seed-11` is valid for matched end metrics and post-feasible behavior, but it is not strong evidence for controller-driven first-feasible conversion.

That caveat must remain explicit in paper writing.

## Problem Statement

The current live `LLM` route is technically functional, but methodologically underpowered for the intended paper story.

The intended story is:

- `raw -> union` isolates proposal-space expansion
- `union -> llm` isolates controller intelligence on the same fixed mixed operator registry

The current live `llm` run does not yet satisfy the second half strongly enough because the controller does not actually schedule the semantic custom operators in live post-feasible search.

## Root-Cause Diagnosis

## 1. The Current LLM Is Not Really Seeing The Full Mixed Registry

The most important diagnosis is structural:

- in the completed `0414_1618__llm` run, the effective candidate set presented to the `LLM` contains no semantic custom operator in any live request
- every live request is reduced to subsets of:
  - `native_sbx_pm`
  - `global_explore`
  - `local_refine`

Observed request-level pattern:

- `318` requests had `3` candidates
- `86` requests had `2` candidates
- `32` requests had `1` candidate
- `0` requests retained any semantic custom operator in the effective candidate set

So the current live route is not failing because the `LLM` sees the semantic actions and chooses poorly.
It is failing earlier:

- pre-`LLM` candidate shaping removes the semantic actions before the model can select them

This means the current route is functionally a stable-family selector, not a semantic mixed-action controller.

## 2. Post-Feasible Hard Filtering Is Too Aggressive

The current `policy_kernel` applies hard post-feasible candidate filtering.
For the live `s1_typical` run, that filter repeatedly suppresses:

- `move_hottest_cluster_toward_sink`
- `spread_hottest_cluster`
- `smooth_high_gradient_band`
- `reduce_local_congestion`
- `repair_sink_budget`
- `slide_sink`
- `rebalance_layout`

That filter is currently driven by:

- `post_feasible_recover_preserve_bias`
- `post_feasible_expand_frontier_bias`
- recent-dominance guardrails on the remaining stable set

This creates a self-locking behavior:

1. semantic operators are filtered out
2. filtered operators receive no new outcome credit
3. unsupported operators remain labeled risky
4. later filters suppress them again

That is a credit-starvation loop.

## 3. Reflection Evidence Is Too Coarse For Action-Conditioned Spatial Decisions

The current controller state already includes useful compact panels, but the operator evidence is still too categorical.
Current prompt-facing evidence mostly uses labels such as:

- `entry_fit`
- `preserve_fit`
- `expand_fit`
- `frontier_evidence`
- `dominant_violation_relief`

Those labels are useful for generic phase control, but not enough for semantic thermal-layout actions that depend on spatial state such as:

- hotspot-to-sink offset
- sink saturation and directionality
- local congestion geometry
- high-gradient band location
- whether the hottest cluster is compact, elongated, or split

So even if the semantic operators were allowed back into the candidate set, the current prompt surface would still under-express why a specific semantic action is locally appropriate.

## 4. The Current Controller Learns Too Little About Regime-Specific Operator Credit

The current reflective summaries are useful as `L1` evidence, but they aggregate too coarsely for the next paper-facing step.

For the active `s1_typical` story, the controller needs regime-conditioned operator credit such as:

- which operators preserve feasibility under full sink utilization
- which operators add frontier points in thermal-limit-dominated feasible regions
- which operators help when the hotspot sits outside the sink corridor
- which operators help when gradient reduction is blocked by a dense cluster

The current summaries do not stratify strongly enough by:

- post-feasible regime
- dominant pressure
- spatial motif
- sink budget state

So the controller remains phase-aware but not motif-aware.

## 5. The Current Runtime Configuration Is Only Partially Live

The repository already wires:

- `memory.recent_window`
- `retry.timeout_seconds`

into actual execution.

However, under the current `chat_compatible_json` live path, `reasoning.effort` is not yet clearly propagated into the outgoing live request payload.

That is not the dominant reason for the current failure, but it means we should not attribute the observed controller behavior to a validated reasoning-effort mechanism.

## Design Goals

- Preserve the paper-facing fairness boundary completely.
- Keep `union` and `llm` on the same operator registry and same matched optimizer contract.
- Recover real semantic-operator visibility inside live `llm` control.
- Upgrade from coarse phase-aware control to action-conditioned spatial control.
- Add reflective retrieval and regime-conditioned operator credit without turning the method into a different optimizer class.
- Improve post-feasible Pareto expansion without sacrificing feasible preservation.

## Non-Goals

- Do not change the optimization problem, design variables, repair, PDE solve, evaluation spec, or survival semantics.
- Do not add `llm`-only privileged operators.
- Do not retune population size, generation count, or evaluation budget.
- Do not rewrite the experiment into direct design-vector generation by the `LLM`.
- Do not hardcode benchmark-seed exceptions or operator-name one-off patches.

## Proposed L2 Controller Design

The next controller should be framed as:

- `L2 semantic-action reflective controller`

still under the same matched `union` action registry.

Its role is not to invent new moves.
Its role is to schedule the existing mixed action space in a way that is:

- physically grounded
- phase-aware
- spatially aware
- reflection-driven

### Layer 1. Keep The Fixed Mixed Action Registry

The operator pool remains exactly the current paper-facing `union` registry.

That preserves the intended statement:

> `union` and `llm` use the same mixed action vocabulary; only the controller changes.

### Layer 2. Replace Hard Semantic Suppression With Controlled Visibility

The first design change is architectural, not prompt-only.

The `policy_kernel` should stop collapsing post-feasible candidate sets to stable-only subsets.
Instead it should produce:

- a stable preservation backbone
- plus bounded semantic visibility

Recommended rule:

- always keep the stable trio available:
  - `native_sbx_pm`
  - `global_explore`
  - `local_refine`
- and also keep at least `1` to `2` semantic candidates selected by regime-conditioned eligibility

This changes the controller from:

- hard filter then choose among stable actions

to:

- keep stable safety anchors but maintain semantic action opportunity

This is the single most important recovery step.

### Layer 3. Move From One-Stage Operator Choice To Two-Stage Hyper-Heuristic Choice

The next controller decision should be decomposed into:

1. choose operator intent or family
2. choose concrete operator inside that family

Suggested first-stage intents:

- `preserve_feasible`
- `frontier_expand`
- `sink_retarget`
- `congestion_relief`
- `hotspot_spread`
- `local_cleanup`
- `native_baseline`

Second-stage selection then maps intent to a specific operator id.

This makes the control problem closer to the hyper-heuristic literature and makes prompt reasoning easier and more interpretable.

### Layer 4. Add Action-Conditioned Spatial State

The prompt surface should add spatial evidence that directly connects state to semantic operator applicability.

Recommended new live features:

- `hotspot_to_sink_offset`
- `hotspot_inside_sink_window`
- `hottest_cluster_centroid`
- `hottest_cluster_compactness`
- `max_gradient_band_center`
- `local_congestion_pair`
- `nearest_neighbor_gap_min`
- `layout_bbox_fill_ratio`
- `sink_budget_bucket`
- `frontier_tradeoff_direction`

And for each semantic operator, derive compact applicability fields such as:

- `applicability`
- `expected_peak_effect`
- `expected_gradient_effect`
- `expected_feasibility_risk`
- `spatial_match_reason`

This keeps the prompt compact while making semantic actions legible.

### Layer 5. Build Regime-Conditioned Reflective Credit Tables

The reflection layer should stop behaving like a mostly global score summary and instead maintain compact credit by regime.

Recommended indexing:

- `phase`
- `dominant_violation_family`
- `sink_budget_bucket`
- `spatial_motif`

Recommended stored statistics:

- feasible preservation rate
- feasible regression rate
- frontier add count
- unique frontier add count
- average peak delta
- average gradient delta
- average total violation delta
- average post-feasible objective delta

This memory is still controller-only and still physically safe because it only summarizes evaluated outcomes.

### Layer 6. Retrieval-Augmented Operator Selection

At decision time, retrieve a small set of similar historical episodes:

- same phase
- similar sink utilization
- similar hotspot-to-sink geometry
- similar dominant pressure

Then show the `LLM` only the most relevant compact examples.

This is much stronger than showing raw recent history, and better aligned with:

- reflective hyper-heuristics
- sparse expensive-evaluation optimization
- engineering-domain state abstraction

### Layer 7. Separate Preserve Score And Frontier Score Explicitly

The current controller mixes preservation and expansion mostly through discrete fit labels.
`L2` should present both objectives explicitly:

- `preserve_score`
- `frontier_score`
- `regression_risk`

The `LLM` should be instructed to:

- reject high-frontier but high-regression actions during recover states
- allow moderate-risk frontier actions only when preserve score is already adequate

This creates a real post-feasible controller rather than a generic safe-action bias.

### Layer 8. Add A Semantic-Action Visibility Contract

The controller should emit diagnostics that make semantic usage auditable.

Required new diagnostics:

- `semantic_visibility_rate`
- `semantic_candidate_count_avg`
- `semantic_selection_rate`
- `semantic_frontier_add_count`
- `semantic_feasible_preservation_count`
- `stable_vs_semantic_pareto_ownership`

Without these metrics, the paper cannot clearly prove that the `LLM` actually used the semantic registry.

## Concrete Component Changes

### `optimizers/operator_pool/policy_kernel.py`

- replace hard post-feasible semantic suppression with bounded semantic visibility
- introduce intent-level candidate shaping
- add soft bias and quota-style family control instead of stable-only collapse

### `optimizers/operator_pool/state_builder.py`

- extend prompt panels with spatial motif summaries
- surface operator-conditioned applicability and expected effect signs
- preserve compactness and avoid raw geometry dumps

### `optimizers/operator_pool/domain_state.py`

- derive hotspot-to-sink and congestion motif features
- expose phase-specific trade-off direction signals
- make post-feasible pressure summaries more spatially explicit

### `optimizers/operator_pool/reflection.py`

- stratify operator credit by regime and motif
- compute unique frontier contribution counters
- add semantic-visibility and semantic-credit diagnostics

### `optimizers/operator_pool/prompt_projection.py`

- project the new intent-level and operator-conditioned state
- suppress low-value generic fields if they compete with spatial evidence
- keep prompt size bounded

### `optimizers/operator_pool/llm_controller.py`

- move prompt contract from single-step operator choice toward two-stage intent-plus-operator choice
- enforce explicit preserve versus expand reasoning
- keep fallback semantics and recent-dominance protections, but only as bounded safeguards

### `llm/openai_compatible/client.py`

- wire `reasoning.effort` into the live chat-compatible request path when the provider supports it
- keep compatibility-safe fallback behavior when unsupported

## Experimental Protocol

The main paper comparison remains unchanged:

1. `nsga2_raw`
2. `nsga2_union`
3. `nsga2_llm`

The `L2` controller is still evaluated as the `llm` route under the same matched setup.

Recommended internal ablations:

1. `L2-visible`
   - only recover semantic candidate visibility
2. `L2-spatial`
   - add action-conditioned spatial state
3. `L2-reflect`
   - add regime-conditioned retrieval and credit
4. `L2-full`
   - full two-stage controller

These ablations are useful for mechanism analysis even if only `L2-full` appears in the headline ladder.

## Validation Plan

### Automated Verification

Add or update focused tests for:

- policy-kernel candidate shaping under post-feasible phases
- semantic visibility guarantees
- state-builder spatial motif panels
- reflection credit stratification
- prompt projection size and field presence
- live config propagation for `memory.recent_window`, `retry.timeout_seconds`, and `reasoning.effort`

### Cheap Offline Diagnostics

Before another long live run, use current trace re-analysis and controller-state replay to confirm:

- semantic operators remain visible in post-feasible decisions
- no phase reduces to stable-only collapse by default
- retrieval outputs are compact and regime-relevant

### Live Validation

Run at least one matched live `s1_typical` seed-11 validation with:

- the same official `s1_typical_llm.yaml`
- the same budget
- the same operator pool
- `evaluation-workers <= 2`

Then evaluate:

- feasible rate
- Pareto size
- pooled non-dominated ownership
- semantic visibility rate
- semantic frontier contribution
- latency and fallback overhead

## Paper-Facing Success Criteria

`L2` is only paper-positive if it shows both:

1. controller-mechanism evidence
   - semantic operators are actually visible and selected in live post-feasible search
   - semantic operators contribute measurable frontier or preservation value
2. matched optimization evidence
   - at least one meaningful improvement over the current `llm` run on:
     - Pareto size
     - pooled non-dominated ownership
     - knee quality
     - feasible preservation under post-feasible search

The strongest success condition is not merely beating current `llm`.
The stronger result is:

- recovering a real semantic-controller story while staying inside the same matched experiment class

## Risks

### 1. Prompt Bloat

Adding spatial motifs can easily make the prompt too large and too noisy.
The design must stay compact and only retain decision-relevant geometric abstractions.

### 2. Semantic Over-Correction

If semantic visibility is enforced too aggressively, the controller may swing into the opposite failure mode:

- forcing semantic novelty when stable preservation is actually needed

So visibility should be bounded, not mandatory at every step.

### 3. Retrieval Leakage

Retrieval should remain run-internal and controller-local.
It must not become an external dataset shortcut or a benchmark-specific hardcoded policy.

### 4. Over-Interpreting Seed-11 Entry Metrics

Seed-11 remains weak evidence for controller-driven first-feasible conversion.
That limitation must remain explicit.

## Recommended Paper Narrative After L2

If `L2` succeeds, the cleanest narrative is:

- `raw` demonstrates the native optimizer backbone
- `union` demonstrates the value of expanding the action vocabulary with semantic thermal-layout operators
- current `L1 llm` proves live controller feasibility but reveals that phase-aware stable-family control alone is insufficient
- `L2 llm` restores semantic-action visibility and adds reflective spatial scheduling on the same fixed registry

That is a much stronger and fairer story than claiming a generic memory-based `LLM` optimizer.

## Final Recommendation

The next step should not be another prompt-only rerun.

The next step should be a controller-only `L2` redesign that:

- restores semantic operator visibility
- adds action-conditioned spatial evidence
- adds regime-conditioned reflective retrieval
- keeps the same fixed mixed action registry and matched optimizer contract

That is the most scientifically defensible way to turn the current live `llm` route from a runnable stable-family selector into the semantic controller required by the paper.
