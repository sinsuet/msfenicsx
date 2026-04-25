# Operator Redesign And Policy Split Design

> Status: approved design direction for the operator-layer refactor that resets `raw` and `union` to clean baselines and makes assisted framework advantages explicit on the `llm` line.
>
> This spec is intentionally allowed to override the assumptions implied by the current paper-facing mainline docs. The goal is not to preserve the current `union` story, but to rebuild the operator and legality stack into a form that is experimentally defensible and ablation-friendly.

## 1. Goal

Redesign the optimizer action layer so that:

- `raw` remains the native backbone baseline
- `union` becomes a clean random-over-primitive-operators baseline
- `llm` can keep assisted framework advantages, but those advantages are explicit and removable
- repair, legality restoration, and controller policy are no longer mixed into one hidden shared path
- traces, analytics, and rendered layouts represent the actual evaluated path instead of silently replaying everything through full repair

This is a fairness and experiment-design refactor first, not a cosmetic operator renaming exercise.

Scope note:

- this spec is written against the active paper-facing `nsga2_raw` / `nsga2_union` / `nsga2_llm` ladder
- other optimizer families may later adopt equivalent primitive registries and legality policies, but that is not required for the first implementation wave

## 2. Why The Current Chain Is Too Strong

The current stack is stronger than the labels `raw` and `union` suggest.

### 2.1 Shared strong preprocessing before PDE

`ThermalOptimizationProblem` currently evaluates every optimizer proposal by:

1. applying `repair_case_payload_from_vector(...)`
2. running `evaluate_cheap_constraints(...)`
3. only then deciding whether PDE evaluation should run

Source:

- `optimizers/problem.py`
- `optimizers/repair.py`
- `optimizers/cheap_constraints.py`

This means the recorded decision vector is not the same thing as the actually evaluated geometry whenever repair changes the layout.

### 2.2 Current repair is not a light canonicalization pass

The current repair path includes:

- bound clamping on component variables
- sink interval projection and ordering
- overlap separation
- local legality restoration over the component set

That is an assisted geometry-restoration mechanism, not a neutral decoding step.

### 2.3 Union is stronger than “randomly choose an operator”

The `union` controller is currently random-uniform, but the action pool is not primitive.

It contains task-aware macro-operators such as:

- `move_hottest_cluster_toward_sink`
- `spread_hottest_cluster`
- `smooth_high_gradient_band`
- `reduce_local_congestion`
- `rebalance_layout`

These operators:

- inspect multi-component spatial motifs
- encode target-seeking logic tied to heat/sink intuition
- often move multiple components and sometimes the sink together

That already exceeds the “simple mixed operator baseline” story.

### 2.4 Union also gets extra repair-aware proposal filtering

In the current genetic union adapter, each proposal is:

1. generated
2. repaired immediately
3. deduplicated once in raw proposal space
4. deduplicated again in repaired-vector space

So the random controller is benefiting from repair-aware selection pressure before the shared evaluation chain even starts.

### 2.5 Analytics and rendering already assume semantic operators

Current operator ids are embedded into:

- route-family diagnostics
- expected peak / gradient effect annotations
- controller-state panels
- reflection summaries
- staged audits
- layout replay logic

As a result, the current operator layer is not just a proposal generator. It is a controller-facing semantic ontology plus an analysis ontology.

### 2.6 Rendered layout history is also currently “repaired”

`render_assets.py` rebuilds optimizer layouts by preferring `repair_case_payload_from_vector(...)` when replaying history rows. This can make a clean baseline look more legal or more structured than the actual proposal/evaluation path.

## 3. Literature Principles That Drive The Redesign

The redesign follows four principles supported by the optimization literature.

### 3.1 Baseline continuous-search variation should stay primitive

For real-coded evolutionary search, `SBX` and polynomial mutation are standard primitive operators for continuous variables. They are appropriate as the baseline anchor because they are representation-aware but not task-semantic.

References:

- Deb, K. and Agrawal, R. B., “Simulated Binary Crossover for Continuous Search Space”, *Complex Systems*, 1995.  
  https://www.complex-systems.com/abstracts/v09_i02_a02/
- Deb, K. et al., “A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II”, 2002.  
  https://web.njit.edu/~horacio/Math451H/download/2002-6-2-DEB-NSGA-II.pdf

### 3.2 Operator pool and controller policy are separate experiment axes

Adaptive operator selection work treats:

- the available operators
- the operator credit signal
- the operator selection policy

as separate design choices. Therefore “random controller over a semantic macro-action pool” is not equivalent to “random controller over primitive operators”.

References:

- Fialho, A., *Adaptive Operator Selection and Management in Evolutionary Algorithms*, thesis draft.  
  https://groups.csail.mit.edu/EVO-DesignOpt/pb/uploads/Site/FialhoThesisDraft.pdf
- Sharma, M. et al., “An Overview on Evolutionary Algorithm Based Adaptive Operator Selection”, 2020.  
  https://arxiv.org/abs/2005.05613

### 3.3 Constraint handling must be explicit because it changes optimizer behavior

Repair, feasibility rules, and bound-handling are not neutral plumbing. They materially affect search dynamics and performance, so they must be treated as explicit policy choices, especially in a fairness-sensitive benchmark.

References:

- Deb, K., “An Efficient Constraint Handling Method for Genetic Algorithms”, *Computer Methods in Applied Mechanics and Engineering*, 2000.  
  https://www.sciencedirect.com/science/article/abs/pii/S0045782599003898
- Boks, S. et al., “Handling Bound Constraints for Numerical Optimization by Differential Evolution”, 2021.  
  https://arxiv.org/abs/2105.06757
- Lagaros, N. D. et al., review on constraint handling in evolutionary optimization, 2023.  
  https://link.springer.com/article/10.1007/s11081-022-09782-9

### 3.4 Layout neighborhoods are usually primitive perturbations, not objective-labeled macros

Floorplanning and facility-layout literature usually relies on simple perturbation neighborhoods such as move, swap, insert, resize, and related local actions. That is the correct precedent for a clean layout-search operator registry.

References:

- Chang, Y.-C. et al., “B*-Trees: A New Representation for Non-Slicing Floorplans”, DAC 2000.  
  https://websrv.cecs.uci.edu/~papers/compendium94-03/papers/2000/dac00/pdffiles/27_1.pdf
- Palubeckis, G. et al., survey/review material on layout-search neighborhoods, 2022.  
  https://www.mdpi.com/2227-7390/10/13/2174

## 4. Design Principles

The new operator system must satisfy the following rules.

### 4.1 Primitive baseline operators may be representation-aware

They may know:

- that each component has paired `x/y` variables
- that the sink is represented by `start/end`
- the per-variable bounds

They may not know:

- which cluster is “hottest”
- which direction is predicted to improve peak temperature
- which route family is currently underused
- which operator historically preserved feasibility better

### 4.2 Objective-aware and state-aware actions are framework features

If an action uses:

- hotspot targeting
- congestion diagnosis
- gradient-band shaping
- route-family balancing
- policy-phase logic

then it belongs to the assisted `llm` framework line, not to the clean `union` baseline.

### 4.3 Repair is a legality policy, not an operator

Actions like `repair_sink_budget` are misnamed under the current design. They are legality or restoration policies and must move out of the operator registry.

### 4.4 Traces must distinguish proposal from evaluated geometry

Every stage that can modify a vector must be logged explicitly. The system must not rely on the word `repair` as a catch-all.

### 4.5 Rendering must follow the recorded evaluation policy

A clean baseline run must be replayed as a clean baseline run. A framework-assisted run may be replayed through assisted evaluation geometry. This decision must come from manifest metadata, not from a hardcoded rendering shortcut.

## 5. Options Considered

Three directions were considered.

### Option A: Keep the current semantic pool and only rename it

Pros:

- lowest implementation effort

Cons:

- does not fix the fairness problem
- leaves semantic macro-actions inside the baseline
- still hides repair strength inside shared evaluation and replay

Decision: reject.

### Option B: Primitive baseline registry plus explicit assisted registry

Pros:

- creates a defensible `raw` / `union` baseline
- makes `llm` framework advantages explicit
- supports later ablations cleanly
- aligns with AOS and layout-neighborhood literature

Cons:

- requires trace and replay contract updates
- requires migration of current semantic operators into a new assisted layer

Decision: select this option.

### Option C: Remove everything except native SBX/PM

Pros:

- strongest simplicity story

Cons:

- collapses `union` into a nearly meaningless variant of `raw`
- wastes the representation structure of the layout problem
- removes useful primitive neighborhoods such as sink-only or component-only actions

Decision: reject.

## 6. Selected Architecture

The action stack is split into four explicit layers.

### 6.1 Primitive Operator Registry

Purpose:

- proposal generation for clean baselines

Properties:

- representation-aware
- objective-agnostic
- state-agnostic
- no repair
- small and stable

Used by:

- `union`
- optional internal `llm_clean` ablations

### 6.2 Assisted Action Registry

Purpose:

- higher-level layout actions for the assisted `llm` framework line

Properties:

- may use controller state
- may use domain motifs
- may bundle multiple primitive moves
- may incorporate spatial heuristics

Used by:

- `llm`
- later framework ablations only

### 6.3 Legality Policy

Purpose:

- convert a proposal into the geometry that is actually screened and possibly solved

This becomes an explicit policy id attached to each run.

### 6.4 Replay Policy

Purpose:

- reconstruct layout frames from the same evaluated geometry contract used at runtime

This must be driven by run metadata, not by renderer guesses.

## 7. Clean Baseline Legality Policy

The approved baseline legality policy is the previously agreed minimal version.

Selected baseline legality policy: `minimal_canonicalization`

It includes:

- vector bound clipping
- sink interval ordering
- sink interval projection into declared bounds and budget ceiling

It does not include:

- component overlap separation
- local legality restoration
- geometry relocation search
- repair-aware deduplication

Cheap constraints still run before PDE, but they operate on the minimally canonicalized proposal. If geometry remains illegal, the proposal is marked infeasible and PDE is skipped.

Rationale:

- preserves a usable continuous search space
- avoids trivial failures caused by malformed sink intervals
- does not smuggle geometry intelligence into the baseline

## 8. Assisted Framework Legality Policy

Selected assisted legality policy: `projection_plus_local_restore`

This corresponds to the current strong repair behavior and remains available only for the assisted framework line unless a specific ablation enables it elsewhere.

It includes:

- vector bound clipping
- sink interval projection
- overlap separation
- local legality restoration

This policy is allowed for:

- `llm`
- future explicit ablation modes such as `union_assisted`

It is not part of the clean paper-facing `raw` or `union` baselines.

## 9. New Primitive Operator Registry

The paper-facing primitive registry is intentionally small.

### 9.1 `vector_sbx_pm`

Category:

- global real-coded recombination

Arity:

- 2 parents

Touched variables:

- all active variables

Notes:

- standard continuous-search anchor
- for the active paper-facing `nsga2_union` line, this absorbs the current `native_sbx_pm`
- `global_explore` is not retained as a separate baseline semantic id

### 9.2 `component_jitter_1`

Category:

- local component perturbation

Arity:

- 1 parent

Touched variables:

- one randomly selected component pair `(x, y)`

Notes:

- small Gaussian or bounded local move
- no hotspot targeting

### 9.3 `component_relocate_1`

Category:

- component relocation

Arity:

- 1 parent

Touched variables:

- one randomly selected component pair `(x, y)`

Notes:

- resamples one component inside its legal variable box
- provides escape behavior without semantic guidance

### 9.4 `component_swap_2`

Category:

- permutation-style neighborhood on component positions

Arity:

- 1 parent

Touched variables:

- two randomly selected component pairs `(x, y)`

Notes:

- swaps their positions in vector space
- mirrors classic swap-style layout neighborhoods

### 9.5 `sink_shift`

Category:

- sink-only local move

Arity:

- 1 parent

Touched variables:

- `sink_start`, `sink_end`

Notes:

- moves sink center while preserving span
- still uses minimal canonicalization after proposal generation

### 9.6 `sink_resize`

Category:

- sink-only span move

Arity:

- 1 parent

Touched variables:

- `sink_start`, `sink_end`

Notes:

- changes span while preserving center when possible
- no hotspot alignment logic

## 10. Explicitly Rejected Baseline Operators

The following current operators must not remain in the clean baseline registry:

- `local_refine`
- `move_hottest_cluster_toward_sink`
- `spread_hottest_cluster`
- `smooth_high_gradient_band`
- `reduce_local_congestion`
- `repair_sink_budget`
- `slide_sink`
- `rebalance_layout`

Reasons:

- they are objective-labeled or motif-labeled
- several of them move multiple objects based on state-derived targeting
- several of them bundle sink and component updates into one macro action
- `repair_sink_budget` is legality handling, not variation

## 11. Assisted Action Registry

The current semantic operators should migrate into an assisted registry used only by the `llm` framework line.

Initial assisted action families:

- hotspot pull toward sink
- hotspot spread
- gradient-band smoothing
- congestion relief
- sink retarget / sink budget recenter
- global rebalance

Important rule:

- assisted actions are allowed to remain bundled and state-aware
- they are not part of the fairness baseline and must not be described as if they were ordinary union operators

## 12. Experiment Lines After The Refactor

### 12.1 Paper-facing lines

- `raw = native backbone + minimal_canonicalization + cheap_constraints`
- `union = primitive registry + random controller + minimal_canonicalization + cheap_constraints`
- `llm = llm controller + primitive registry + assisted registry + projection_plus_local_restore + framework guardrails`

### 12.2 Internal ablation lines

The platform should support internal ablations even if they are not the main paper labels:

- `llm_clean = llm controller + primitive registry + minimal_canonicalization`
- `union_assisted = random controller + primitive registry + assisted registry + assisted legality`
- `union_clean_plus_repair = random controller + primitive registry + projection_plus_local_restore`

This is the minimum structure needed to answer whether gains come from:

- controller quality
- operator semantics
- legality restoration
- downstream framework guardrails

## 13. Trace Contract Changes

Current trace fields use `repaired_vector`, which is too specific and misleading once baseline runs stop using full repair.

The new contract should record:

- `proposal_vector`
- `evaluated_vector`
- `legality_policy_id`
- `vector_transform_codes`
- `proposal_status`
- `duplicate_status`

Definitions:

- `proposal_vector`: direct output of the selected operator
- `evaluated_vector`: vector actually used for cheap constraints and possible PDE
- `legality_policy_id`: one of `minimal_canonicalization`, `projection_plus_local_restore`, or future explicit modes
- `vector_transform_codes`: for example `bound_clip`, `sink_reorder`, `sink_project`
- `proposal_status`: one of `accepted_for_screening`, `rejected_duplicate`, `rejected_illegal`, `accepted_for_pde`, `cheap_infeasible`

Rules:

- baselines may still have `proposal_vector != evaluated_vector` when minimal canonicalization changes sink encoding
- the old name `repaired_vector` should be retired from new traces once migration is complete

## 14. Evaluation History Contract Changes

History rows inside `optimization_result.json` should no longer expose only the raw decision vector.

Each row should carry both:

- `proposal_decision_vector`
- `evaluated_decision_vector`

and:

- `legality_policy_id`
- `cheap_constraint_issues`
- `solver_skipped`

This is required because:

- analytics needs to know what was truly screened
- rendering needs the evaluated geometry
- duplicate analysis must not confuse proposal-space and evaluated-space identity

## 15. Replay And Visualization Changes

`render_assets` must become policy-aware.

### 15.1 New replay rule

For every layout frame:

- prefer `evaluated_decision_vector`
- reconstruct geometry using the run’s declared legality policy
- never default to full repair for a clean baseline run

### 15.2 Impact scope

This is not a major visualization redesign, but it is a real contract update.

Expected impact by area:

- trace writers: moderate
- optimization result/history schema: moderate
- render replay helpers: moderate
- downstream figure code: low
- comparison reports: low to moderate

So the logging and visualization system does need changes, but the main blast radius is contract plumbing, not figure styling or rendering architecture.

## 16. Migration Plan

The implementation should happen in four phases.

### Phase 1: Introduce explicit legality and replay policies

- add `LegalityPolicy` abstraction
- add `ReplayPolicy` / manifest metadata
- separate proposal vector from evaluated vector

### Phase 2: Introduce primitive registry

- implement the six primitive operators
- wire `union` to the primitive registry
- keep current semantic registry temporarily available only behind assisted mode flags

### Phase 3: Move semantic operators into assisted registry

- migrate current semantic operator ids away from baseline route families
- restrict controller-state semantic annotations to assisted mode
- remove repair-aware dedup from clean union

### Phase 4: Update analytics and rendering

- migrate traces from `repaired_vector` to `evaluated_vector`
- make `render_assets` use policy-aware replay
- update comparison and audit tooling to use new metadata

## 17. Testing Requirements

Focused tests must cover:

- minimal canonicalization behavior
- assisted legality behavior
- clean union without repair-aware dedup
- proposal vs evaluated vector trace integrity
- render replay using the run legality policy
- raw/union fairness smoke checks

Specific maintained test areas likely affected:

- `tests/optimizers/`
- `tests/visualization/`

The current equivalence check that forces union to choose only `native_sbx_pm` should be preserved in spirit, but updated to the new primitive registry and legality policy naming.

## 18. Risks And Non-Goals

### Risks

- short-term `union` performance may drop
- old semantic analytics panels may become temporarily less informative
- historical run re-rendering may need compatibility handling

### Non-goals

- preserving backward semantic meaning for old operator ids
- keeping current route-family dashboards unchanged
- hiding framework strength differences for easier storytelling

## 19. Decision Summary

The approved redesign is:

- keep `raw` as the native baseline
- rebuild `union` around a small primitive operator registry
- keep strong repair and semantic macro-actions only on the assisted `llm` framework line
- make legality policy, evaluated geometry, and replay policy explicit in logs and artifacts

This is the minimum redesign that makes the benchmark defensible when comparing:

- native optimizer behavior
- random mixed-operator behavior
- LLM-guided framework behavior

without conflating those three questions.
