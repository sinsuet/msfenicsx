# Restore Fair raw / union / llm Comparison Design

> Status: approved design direction for restoring a defensible `raw / union / llm` comparison contract on the `s1_typical` and `s2_staged` paper-facing mainlines. This spec replaces the implicit "B-shape" agreement reached during brainstorming with an explicit written contract, scoped module boundaries, and a two-phase implementation order.
>
> This spec is intentionally allowed to override parts of the current `README.md` and `AGENTS.md` paper-facing narrative where they diverge from the agreed comparison contract. It does **not** override `core/` schema/contract guarantees, `evaluation/` evaluation-spec semantics, or `optimizers/algorithm_config.py` repository-wide backbone defaults.

## 1. Goal

Restore a comparison contract under which:

- `raw`, `union`, `llm` can be reported side-by-side as fair baselines on the same problem
- the `llm` line's measurable advantages can be attributed to its representation/decision layer, not to a stronger search substrate
- the `union` line stops being structurally collapsed onto sink-only operators
- documentation, scenario specs, and runtime implementation tell the same story

The contract used in this spec is the "B-shape" definition agreed during brainstorming:

> `union` and `llm` share the same search substrate (decision encoding, operator pool, registry profile, repair / legality policy, cheap constraints, expensive evaluation budget). `llm` may differ from `union` only in a representation layer that biases choice within the shared candidate support — it must not change the candidate support itself.

This spec is the source of truth for that contract. Where existing docs disagree, this spec wins and they are updated.

## 2. Why The Current Chain Has Drifted

The current chain has drifted in two directions at once.

### 2.1 The `llm` line crossed the substrate boundary

Paper-facing scenario specs assign different substrates to `union` and `llm`:

- `union` uses `registry_profile: primitive_clean` and `legality_policy_id: minimal_canonicalization` ([scenarios/optimization/s1_typical_union.yaml:147](scenarios/optimization/s1_typical_union.yaml#L147), [scenarios/optimization/s1_typical_union.yaml:158](scenarios/optimization/s1_typical_union.yaml#L158))
- `llm` uses `registry_profile: primitive_plus_assisted` and `legality_policy_id: projection_plus_local_restore` ([scenarios/optimization/s1_typical_llm.yaml:147](scenarios/optimization/s1_typical_llm.yaml#L147), [scenarios/optimization/s1_typical_llm.yaml:182](scenarios/optimization/s1_typical_llm.yaml#L182))
- the `s2_staged` ladder is identical in shape ([scenarios/optimization/s2_staged_union.yaml:147](scenarios/optimization/s2_staged_union.yaml#L147), [scenarios/optimization/s2_staged_llm.yaml:147](scenarios/optimization/s2_staged_llm.yaml#L147), [scenarios/optimization/s2_staged_llm.yaml:182](scenarios/optimization/s2_staged_llm.yaml#L182))

In addition, `policy_kernel.build_policy_snapshot` actively narrows the operator support. It produces `allowed_operator_ids` and `suppressed_operator_ids`, and current branches re-write them based on phase, recent concentration, and reset state ([optimizers/operator_pool/policy_kernel.py:451-559](optimizers/operator_pool/policy_kernel.py#L451-L559)). The LLM controller then receives the already-narrowed candidate set, and the system prompt explicitly tells the model that an operator was "removed from the current candidate set" ([optimizers/operator_pool/llm_controller.py:727-797](optimizers/operator_pool/llm_controller.py#L727-L797)). That is a hard support change, not a soft hint.

### 2.2 The `union` line has a structurally sink-biased shared pool

`union` shares the same primitive pool as the contract requires, and `random_uniform` samples it uniformly over `candidate_operator_ids`. But the clean pool itself is small and asymmetric in leverage:

- the canonical clean pool has 7 operators, 2 of which are sink-class ([optimizers/operator_pool/primitive_registry.py:6-14](optimizers/operator_pool/primitive_registry.py#L6-L14))
- sink operators move only `sink_start / sink_end` and have stable, high-yield effects on objectives in the current low-dimensional formulation
- component operators move 1–2 components and frequently fail legality or have noisier objective effects

This is not a `union` controller bug. It is a shared-pool design imbalance, which means it cannot be cleanly compensated for inside the `llm` controller without crossing the substrate boundary.

### 2.3 Documentation is internally inconsistent

- `README.md` describes `llm` as the "assisted framework line" and explicitly contrasts clean vs. assisted legality ([README.md:12](README.md#L12), [README.md:33](README.md#L33))
- `AGENTS.md` documents the registry/legality split as the active ladder ([AGENTS.md:14-17](AGENTS.md#L14-L17))
- `CLAUDE.md` still says "same mixed action registry, only controller changed" ([CLAUDE.md:288-289](CLAUDE.md#L288-L289))

These three files describe three different contracts. Restoring the contract therefore means rewriting at least these three docs together, not just one of them.

## 3. The Comparison Contract (B-Shape)

This is the contract this spec restores. Everything downstream — spec edits, code edits, tests, doc rewrites — exists to make this contract true and verifiable.

### 3.1 Substrate fields that must be identical across `union` and `llm`

For each paper-facing scenario (`s1_typical`, `s2_staged`):

- `decision_variables` and bounds
- `operator_pool` (concrete operator id list)
- `operator_control.registry_profile`
- `evaluation_protocol.legality_policy_id`
- the cheap-constraints chain
- the repair chain
- `evaluation_spec_path`
- `population_size`, `num_generations`, `seed`, evaluation worker count

If `union` and `llm` disagree on any of these, the contract is broken.

### 3.2 Allowed `llm`-only differences

`llm` may differ only in fields that affect how the same candidate support is interpreted by the controller, not what that support contains:

- `operator_control.controller` (`random_uniform` vs `llm`)
- `operator_control.controller_parameters` for the LLM provider, retry, memory window, reflection interval, fallback controller
- the prompt construction itself, including:
  - state textualization / summary projection
  - reflection over recent generations
  - generation-local memory of recent decisions
  - soft policy / guardrail advice rendered as text
- LLM-only telemetry (request/response/reflection traces)

### 3.3 Forbidden `llm`-only mechanisms

These mechanisms are explicitly out of contract for paper-facing `llm`:

- different `registry_profile` (e.g. `primitive_plus_assisted`) on the `llm` line
- different `legality_policy_id` (e.g. `projection_plus_local_restore`) on the `llm` line
- any code path that delivers to the LLM a `candidate_operator_ids` smaller than the shared full pool
- any `policy_kernel` output that mutates the candidate support (`allowed_operator_ids` shrinking, `suppressed_operator_ids` populated)
- any guardrail that removes an operator from the current selection round
- any retrieval/exact-positive mechanism that reveals evidence on the `llm` side that `union` cannot see at all

The `policy_kernel` evidence summarization and `guardrail` concentration detection are not removed. They are downgraded to soft-advice producers. See §4.C and §4.D.

### 3.4 Why this contract is defensible

Under this contract, `llm` advantage over `union` (when present) can only come from:

- better state interpretation
- better choice within the same support
- better use of memory / reflection over the same evidence stream

That is exactly the claim the paper wants to make, and it is now structurally enforced rather than narratively asserted.

## 4. Module Boundaries After Restoration

The contract must be enforced at four layers. This section pins the responsibility of each layer so future work cannot quietly re-grow `llm`-only substrate advantages.

### 4.A Scenario / spec layer — first-class fairness contract

The paper-facing `union` and `llm` specs are the primary place where the substrate contract is declared. After restoration:

- `s1_typical_union.yaml` and `s1_typical_llm.yaml` must agree on every §3.1 field
- `s2_staged_union.yaml` and `s2_staged_llm.yaml` must agree on every §3.1 field
- `llm` specs may add `controller_parameters` for the representation layer only
- assisted operators (e.g. `hotspot_pull_toward_sink`, `gradient_band_smooth`, `congestion_relief`, `sink_retarget`, `layout_rebalance`) and the `primitive_plus_assisted` registry profile are removed from paper-facing `llm` specs

### 4.B Primitive registry / operator pool — single shared substrate

The primitive registry stays the single source of truth for the clean shared pool. Concretely:

- `optimizers/operator_pool/primitive_registry.py` defines the canonical clean primitive ids
- paper-facing `union` and `llm` specs both list operators that are a subset of this registry
- the assisted registry remains in code for non-paper-facing experiments and for the future Phase 2 ablation roadmap, but is not used by the paper-facing `llm` mainline

If, in Phase 2, the shared pool needs to grow to address sink-bias structural imbalance, that growth happens in the shared registry and applies to both `union` and `llm` simultaneously.

### 4.C `policy_kernel` — annotator, not gatekeeper

`policy_kernel.build_policy_snapshot` keeps its evidence summarization role and its phase / role / route-budget annotations. It must change in two ways:

- it must not return an `allowed_operator_ids` that is smaller than the input `candidate_operator_ids`
- it must not return a non-empty `suppressed_operator_ids`

All current "narrowing" branches (cold-start stable bootstrap, pre-feasible speculative family suppression, pre-feasible convert entry bias, pre-feasible forced reset, expand saturation demotion, etc.) must be rewritten so their effect is expressed as `candidate_annotations` (scores, warnings, role tags, concentration notes) rather than as support changes.

The downstream consumer (`llm_controller`) consumes those annotations as text in the prompt. The `random_uniform` consumer ignores them.

### 4.D `llm_controller` — representation layer only

`llm_controller` keeps:

- prompt projection and metadata panels
- reflection over recent decisions
- generation-local memory of recent decisions
- recent-concentration text advisories

`llm_controller` must change in three ways:

- the `candidate_operator_ids` it passes to the model must equal the shared full pool, never a narrowed set
- the prompt must not contain phrases asserting that an operator has been removed from the candidate set; concentration messages must be phrased as advice rather than removal
- guardrails that previously removed an operator from the current round must be replaced with text-only "this operator has been heavily concentrated recently — consider alternatives unless current state requires it" advice

The fallback controller (`random_uniform`) remains, but is invoked only on schema / semantic invalid responses, not as a way to bypass the contract.

### 4.E `domain_state` / `state_builder` / `reflection`

State features and reflection summaries can stay as-is. They produce text the LLM reads. The new constraint is structural: any consumer of `domain_state` outputs may only use them to bias choice or annotate text. They may not reach back into the registry / policy / candidate pipeline to mutate support.

### 4.F Documentation

`README.md`, `AGENTS.md`, and `CLAUDE.md` are rewritten to describe one contract:

- `union` and `llm` share the same shared semantic primitive pool and the same legality policy
- `llm` differs from `union` only in a representation layer that produces decisions over the same support
- `policy_kernel` and `guardrail` are described as soft-advice producers, not gatekeepers

The wording must be aligned across all three files in the same change set. Phrases like "assisted framework line", "clean baselines vs. assisted `llm` runs", and "primitive_plus_assisted on `llm`" are removed from the paper-facing description.

## 5. Two-Phase Implementation Order

Restoration is split into two phases on purpose. Mixing them would make later results un-attributable.

### 5.1 Phase 1 — restore the contract (no performance chasing)

Goal: make the contract true and verifiable. Performance regressions on the `llm` line are acceptable in Phase 1 if they are caused by removal of out-of-contract mechanisms; that is information, not failure.

Phase 1 scope:

1. Update paper-facing scenario specs (`s1_typical_union/llm`, `s2_staged_union/llm`) so the §3.1 fields match
2. Make `policy_kernel.build_policy_snapshot` annotation-only (per §4.C)
3. Make `llm_controller` candidate-preserving (per §4.D)
4. Update `README.md`, `AGENTS.md`, `CLAUDE.md` to match the contract
5. Add or update the contract tests described in §6.A

Phase 1 explicitly does **not**:

- redesign the shared primitive pool
- change repair / cheap-constraint logic
- attempt to restore any prior `llm` advantage by tuning representation parameters

### 5.2 Phase 2 — rebalance the shared pool

Goal: address `union`'s structural collapse onto sink operators, in a way that benefits `union` and `llm` equally.

Phase 2 scope:

1. Diagnose the actual sink-vs-component leverage gap with Phase 1 traces
2. Propose shared-pool changes (likely additional component-class clean primitives, possibly small re-weighting of how `vector_sbx_pm` interacts with the pool)
3. Land the shared-pool change in the shared registry, not in `llm`-only code
4. Re-run paper-facing comparisons under the Phase 1 contract on the new pool

Phase 2 deliberately depends on Phase 1: without the contract, any pool change is confounded with the substrate split.

### 5.3 What this spec does not cover

- The exact composition of the Phase 2 rebalanced pool. That requires Phase 1 trace evidence and will be its own design pass.
- An `llm`-line ablation matrix (B0/B1/B2). The contract restored here makes that ablation meaningful, but the ablation itself is a future spec.
- Optimization runs on `s3` / `s4` benchmarks. Those have their own scale design ([docs/superpowers/specs/2026-04-27-s3-s4-scale-benchmarks-design.md](docs/superpowers/specs/2026-04-27-s3-s4-scale-benchmarks-design.md)) and are out of scope here.

## 6. Verification And Success Criteria

Verification is split per phase. Phase 1 success is contract-shaped, not performance-shaped.

### 6.A Phase 1 — contract verification

Phase 1 succeeds when all of the following hold.

**Spec contract tests** (new or updated):

- `s1_typical_union.yaml` and `s1_typical_llm.yaml` agree on every §3.1 field
- `s2_staged_union.yaml` and `s2_staged_llm.yaml` agree on every §3.1 field
- `llm` specs differ from `union` specs only in `controller`, `controller_parameters`, and LLM-only telemetry settings

**`policy_kernel` contract tests** (under `tests/optimizers/`):

- `build_policy_snapshot` returns `allowed_operator_ids == input candidate_operator_ids` for representative phases (cold_start, prefeasible_*, post_feasible_*)
- `suppressed_operator_ids` is always empty
- annotations populated for every input operator id

**`llm_controller` contract tests** (under `tests/optimizers/`):

- `candidate_operator_ids` passed into the model equals the shared full pool from the spec
- the rendered system prompt never contains the "removed from the current candidate set" phrasing or any equivalent
- guardrail advice appears in the prompt as text but does not reduce the candidate set

**Trace / artifact verification** (manual on a focused smoke run):

- `controller_trace.jsonl` shows the same candidate pool size on every decision row, equal to the shared full pool
- `operator_trace.jsonl` records selections drawn from the full pool
- both `union` and `llm` runs reference the same `registry_profile` and `legality_policy_id` in their per-seed `run.yaml`

**Documentation verification:**

- `README.md`, `AGENTS.md`, `CLAUDE.md` describe one contract, with no remaining language about `primitive_plus_assisted` or `projection_plus_local_restore` on the paper-facing `llm` line

Per project policy, Phase 1 verification runs focused tests under the affected files first (e.g. `tests/optimizers/test_llm_controller.py`, `tests/optimizers/test_llm_policy_kernel.py`, `tests/optimizers/test_operator_pool_contracts.py`, plus any new spec contract test). The full suite is escalated to only if focused tests pass but cross-module behavior still looks suspicious, in line with `CLAUDE.md`'s test-scope guardrail.

### 6.B Phase 2 — rebalance verification

Phase 2 succeeds when the following hold under the restored contract.

**Process indicators (from `union` smoke run):**

- the share of selected operators that touch components rises meaningfully compared to current `union` runs
- the share of selected operators that touch only sink falls compared to current `union` runs
- feasibility-preserving rate of component-class operators is acceptable (not collapsing legality)

**Result indicators:**

- under matched budget, `union` reaches a Pareto frontier no worse than its current state, with broader spread along component-driven dimensions
- under matched budget, `llm` retains a measurable advantage over `union` on the agreed objectives, attributable to representation-layer effects under the contract

If Phase 2 fails to lift component exploration without breaking feasibility, the response is to iterate on the shared pool or the cheap-constraint chain — not to add `llm`-only mechanisms.

## 7. Risks And Stop Conditions

**Risk 1 — `llm` advantage shrinks after Phase 1.**

Likely if a non-trivial part of the previous advantage was coming from out-of-contract substrate differences. The correct response is to enter Phase 2 and address shared-pool imbalance, not to silently re-introduce the substrate split. If `llm` still shows no advantage after a properly rebalanced Phase 2 pool, that is a real result and should be reported as such.

**Risk 2 — `union` remains sink-biased after Phase 2.**

Means the structural imbalance is deeper than primitive-count adjustment. The response is another iteration on shared-pool design (e.g. clearer component-class leverage, or a re-examination of `vector_sbx_pm`'s role inside the clean pool), still inside the shared substrate.

**Risk 3 — drift returns.**

The spec contract tests in §6.A are the primary defense. If they are weakened or skipped under time pressure, drift returns. Treat those tests as load-bearing.

**Hard stop condition.**

If during Phase 1 the contract turns out to be impossible to enforce without structural changes to the optimizer driver (`raw_driver.py`, `union_driver.py`, or the LLM driver), stop and revise this spec rather than work around the contract.

## 8. Out-Of-Scope

The following are explicitly out of scope for this spec:

- the `raw` line's internal mechanics (it remains the native-vector backbone baseline)
- any optimization-objective change, evaluation-spec change, or PDE-solver change
- any visualization / artifact-rendering refactor beyond what is required to read trace fields verifying the contract
- any cross-benchmark generalization beyond `s1_typical` and `s2_staged`

## 9. References

- [README.md](README.md)
- [AGENTS.md](AGENTS.md)
- [CLAUDE.md](CLAUDE.md)
- [scenarios/optimization/s1_typical_union.yaml](scenarios/optimization/s1_typical_union.yaml)
- [scenarios/optimization/s1_typical_llm.yaml](scenarios/optimization/s1_typical_llm.yaml)
- [scenarios/optimization/s2_staged_union.yaml](scenarios/optimization/s2_staged_union.yaml)
- [scenarios/optimization/s2_staged_llm.yaml](scenarios/optimization/s2_staged_llm.yaml)
- [optimizers/operator_pool/primitive_registry.py](optimizers/operator_pool/primitive_registry.py)
- [optimizers/operator_pool/policy_kernel.py](optimizers/operator_pool/policy_kernel.py)
- [optimizers/operator_pool/llm_controller.py](optimizers/operator_pool/llm_controller.py)
- [optimizers/operator_pool/random_controller.py](optimizers/operator_pool/random_controller.py)
- [optimizers/operator_pool/domain_state.py](optimizers/operator_pool/domain_state.py)
- [docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md](docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md)
- [docs/superpowers/specs/2026-04-25-operator-redesign-design.md](docs/superpowers/specs/2026-04-25-operator-redesign-design.md)
