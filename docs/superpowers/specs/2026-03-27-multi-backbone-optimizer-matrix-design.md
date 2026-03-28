# Multi-Backbone Optimizer Matrix Design

> Status: approved optimizer-platform direction. The pure `NSGA-II` run remains the active paper-facing classical baseline, and the repository now also includes the first-batch six-backbone raw matrix runtime.
>
> This spec supersedes the earlier single-backbone operator-pool planning direction. Future operator-pool and controller work should target the multi-backbone matrix defined here rather than reviving an `NSGA-II`-only branch.
>
> Update on 2026-03-28: this spec remains the optimizer-platform and cross-backbone track. The next paper-facing `LLM` controller story is now documented separately in `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`.
>
> Later implementation update: the repository now includes the raw matrix runtime and an exploratory `union-uniform` matrix runtime across the same six approved backbones. Any older `pool-random` wording below should be read as superseded by the current `union` terminology and runtime shape.
>
> Immediate-focus update on 2026-03-28: the matrix track remains available for platform experiments, but the immediate paper-facing next implementation step is the separate `NSGA-II` `L1-union-llm` controller line rather than a broad matrix-`LLM` rollout.

## 1. Goal

Define the next optimizer-platform architecture for `msfenicsx` so that:

- the paired hot/cold benchmark remains unchanged
- the current pure `NSGA-II` path remains the active paper-facing classical baseline
- the first-batch raw matrix runtime remains compatible with the same benchmark, evaluation, repair, and artifact contract
- future classical experiments expand into a multi-backbone matrix instead of a single `NSGA-II` hybrid branch
- one shared domain operator pool can be compared fairly across multiple `pymoo` backbones
- future `LLM` strategy work becomes a controller-layer replacement on the same action space rather than a special case for one algorithm

This spec now coexists with a separate `NSGA-II` hybrid-union controller line for the paper-facing `LLM` story. The matrix track remains the platform story for cross-backbone infrastructure and matched shared-pool comparisons.

## 2. Why The Single-Backbone Operator-Pool Direction Is No Longer Enough

The earlier `NSGA-II`-only operator-pool idea was a useful intermediate framing, but it is not the right long-term research platform because:

- it binds the domain action space to one classical backbone
- it weakens the claim that the `LLM` strategy layer is algorithm-agnostic
- it leaves no clean path for many-objective, decomposition-based, or swarm-based comparisons
- it would force later rewrites when adding `NSGA-III`, `C-TAEA`, `RVEA`, `MOEA/D`, or `CMOPSO`

Therefore, the operator pool must be elevated from an `NSGA-II` extension into a platform-level proposal layer that multiple backbone families can share.

## 3. Selected First-Batch Backbone Matrix

The first complete experiment batch should include six backbones:

1. `NSGA-II`
   - classic Pareto baseline
   - reviewer-friendly anchor
2. `NSGA-III`
   - reference-direction many-objective baseline
3. `C-TAEA`
   - constrained many-objective baseline
4. `RVEA`
   - alternative reference-direction baseline
5. `MOEA/D`
   - decomposition-based baseline
   - requires repository-owned constraint handling because the current local `pymoo` implementation does not support constrained problems directly
6. `CMOPSO`
   - multiobjective swarm baseline
   - satisfies the requirement to include at least one non-evolutionary population method

These six algorithms are the approved first batch for full raw and union-uniform comparison.

Algorithms such as `SMS-EMOA` and `SPEA2` remain valid future extensions, but they are intentionally deferred so the first implementation wave stays tractable.

## 4. Experiment Ladder

The approved ladder is no longer a single-backbone `B0/B1/P1` sequence.

It is now a matrix:

### B0-Matrix-Raw

Run the six backbones in raw form:

- `nsga2`
- `nsga3`
- `ctaea`
- `rvea`
- `moead`
- `cmopso`

Purpose:

- establish the raw classical baseline surface across multiple optimizer families

### P1-Matrix-Union-Uniform

Run the same six backbones with:

- the same domain operator pool
- the same legality repair
- a `random_uniform` controller

Purpose:

- measure what the shared operator pool contributes before any `LLM` policy is introduced

### L1-Matrix-Union-LLM

Future phase only:

- same six backbones
- same operator pool
- same legality repair
- same artifact schema
- only the controller changes from `random_uniform` to an `LLM` policy

Purpose:

- test whether `LLM` strategy improves feasibility speed, Pareto quality, or expensive-evaluation efficiency under matched budgets

## 5. Architectural Boundaries

### 5.1 Core Platform Boundaries

- `core/` remains the canonical kernel for schema, generation, solving, contracts, and artifact I/O
- `evaluation/` remains the only owner of objective and constraint logic
- `optimizers/` owns search-space encoding, backbone dispatch, operator pools, controller logic, and optimization artifacts
- `llm/` remains a separate future layer that consumes optimizer/controller contracts rather than modifying `core/`

### 5.2 Optimizer Package Shape

The optimizer layer should converge toward this structure:

- `optimizers/models.py`
- `optimizers/io.py`
- `optimizers/artifacts.py`
- `optimizers/problem.py`
- `optimizers/repair.py`
- `optimizers/raw_backbones/`
- `optimizers/operator_pool/`
- `optimizers/adapters/`
- `optimizers/drivers/`
- `optimizers/cli.py`

### 5.3 Family Adapters

The operator pool should not know the details of each algorithm.

Instead, family adapters bridge algorithm-specific parent/context handling into one shared proposal protocol:

- `genetic_family`
  - `NSGA-II`
  - `NSGA-III`
  - `C-TAEA`
  - `RVEA`
- `decomposition_family`
  - `MOEA/D`
- `swarm_family`
  - `CMOPSO`

## 6. Unified Optimizer Contract

Future optimizer specs should use a platform-level algorithm contract:

```yaml
algorithm:
  family: genetic | decomposition | swarm
  backbone: nsga2 | nsga3 | ctaea | rvea | moead | cmopso
  mode: raw | union
```

When `mode: union`, add:

```yaml
operator_control:
  controller: random_uniform | llm
  operator_pool:
    - sbx_pm_global
    - local_refine
    - hot_pair_to_sink
    - hot_pair_separate
    - battery_to_warm_zone
    - radiator_align_hot_pair
    - radiator_expand
    - radiator_contract
```

This replaces any single-field contract such as `algorithm.name: operator_pool_nsga2`.

## 7. Unified Operator Pool

The first approved shared operator pool remains intentionally small and benchmark-specific:

1. `sbx_pm_global`
2. `local_refine`
3. `hot_pair_to_sink`
4. `hot_pair_separate`
5. `battery_to_warm_zone`
6. `radiator_align_hot_pair`
7. `radiator_expand`
8. `radiator_contract`

Design rules:

- operators act on numeric decision vectors only
- operators are algorithm-agnostic
- operators do not mutate `obc`
- operators do not embed controller-like hidden rule cascades
- legality projection remains a shared post-processing step in `optimizers/repair.py`

## 8. Shared Proposal Protocol

The operator pool should be defined as a candidate-proposal layer:

`algorithm-specific parent/context -> controller state -> controller select -> operator propose -> repair -> evaluate -> algorithm-specific update`

The recommended operator interface is:

```python
def propose(
    parents,
    state,
    variable_layout,
    rng,
):
    ...
```

Where:

- `parents` is a family-neutral parent bundle
- `state` is a compact controller-facing summary
- `variable_layout` maps variable IDs to vector positions
- `rng` is the seeded random generator

## 9. Family-Specific Integration Rules

### 9.1 Genetic Family

For `NSGA-II`, `NSGA-III`, `C-TAEA`, and `RVEA`:

- keep the algorithm's original selection and survival identity
- inject the shared operator pool at offspring proposal time
- keep survival and ranking inside the backbone

### 9.2 MOEA/D

For `MOEA/D`:

- keep neighborhood mating
- keep decomposition-based replacement
- add repository-owned constraint handling for the benchmark

Recommended replacement rule:

1. smaller total constraint violation wins over larger total constraint violation
2. if both candidates are feasible, compare decomposition value
3. if both are infeasible, compare total constraint violation only

This preserves the decomposition identity while making the algorithm usable on the current constrained benchmark.

### 9.3 CMOPSO

For `CMOPSO`:

- keep particle, leader, and archive mechanics
- treat the operator pool as proposal augmentation, not as a replacement for swarm motion
- allow the pool to transform the raw swarm proposal before repair and evaluation

This preserves the swarm identity while letting the same operator space participate in the experiment matrix.

## 10. Fairness Rules

All raw, union-uniform, and future union-LLM comparisons must keep the following matched unless the experiment is explicitly framed otherwise:

1. benchmark template
2. benchmark seeds
3. evaluation spec
4. design-variable encoding
5. legality repair
6. operator pool implementation
7. artifact schema
8. representative-candidate extraction rules
9. total expensive-evaluation budget

Comparison rules:

- raw vs union differs only by whether the shared proposal-layer controller path is enabled
- union-uniform vs union-LLM differs only by controller decision making
- algorithm identity comes only from the selected backbone and its family adapter

## 11. Naming And Artifact Rules

### 11.1 Spec Naming

Raw specs:

- `panel_four_component_hot_cold_nsga2_raw_b0.yaml`
- `panel_four_component_hot_cold_nsga3_raw_b0.yaml`
- `panel_four_component_hot_cold_ctaea_raw_b0.yaml`
- `panel_four_component_hot_cold_rvea_raw_b0.yaml`
- `panel_four_component_hot_cold_moead_raw_b0.yaml`
- `panel_four_component_hot_cold_cmopso_raw_b0.yaml`

Union-uniform specs:

- `panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml`
- `panel_four_component_hot_cold_nsga3_union_uniform_p1.yaml`
- `panel_four_component_hot_cold_ctaea_union_uniform_p1.yaml`
- `panel_four_component_hot_cold_rvea_union_uniform_p1.yaml`
- `panel_four_component_hot_cold_moead_union_uniform_p1.yaml`
- `panel_four_component_hot_cold_cmopso_union_uniform_p1.yaml`

Future union-LLM specs follow the same pattern with `_union_llm_l1`.

### 11.2 Artifact Rules

Always write:

- `optimization_result.json`
- `pareto_front.json`
- `manifest.json`

When `mode: pool`, also write:

- `controller_trace.json`
- `operator_trace.json`

The core optimization result contract should stay algorithm-agnostic and should not be repolluted with operator telemetry fields.

## 12. Non-Goals

This design does not require immediate implementation of:

- all `pymoo` algorithms
- algorithm-specific operator pools
- weighted or phased controllers
- surrogate models
- `LLM` execution
- bulk paper-scale experiment automation

## 13. Acceptance Criteria

The next optimizer-platform phase is acceptable only if all of the following hold:

1. The current pure `NSGA-II` mainline remains intact until the matrix work is implemented and verified.
2. The repository documents no longer describe the operator pool as an `NSGA-II`-only extension.
3. The six selected backbones have a clear raw/pool contract and naming scheme.
4. `MOEA/D` has an explicit constrained adaptation rule instead of relying on unsupported library behavior.
5. `CMOPSO` has a clearly defined pool-augmentation path that preserves swarm identity.
6. Future `LLM` controller work can plug into the same operator pool without changing benchmark, repair, or artifact contracts.

## 14. Relationship To Existing Benchmark Docs

The earlier benchmark design doc remains the source of truth for:

- benchmark scene content
- paired hot/cold operating cases
- physics scope
- objectives and constraints

This spec supersedes only the optimizer-platform direction that had been described there as a single-backbone `NSGA-II` ladder.
