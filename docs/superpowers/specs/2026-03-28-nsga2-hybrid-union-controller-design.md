# NSGA-II Hybrid-Union Controller Design

> Status: approved next-stage paper and LLM controller direction.
>
> The pure `NSGA-II` run remains the active paper-facing classical baseline. The multi-backbone raw/pool matrix remains the optimizer-platform track. This spec adds a separate `NSGA-II`-only hybrid-union controller line for the paper-facing action-space and `LLM` strategy story.
>
> Implementation update on 2026-03-28: the `P1-union-uniform-nsga2` rung is now implemented and mechanism-analyzed. The immediate next paper-facing implementation step is `L1-union-llm-nsga2` on the same mixed action registry.

## 1. Goal

Define the next paper-facing optimizer direction so that:

- the active classical baseline remains plain `pymoo` `NSGA-II`
- a second `NSGA-II` line can search a larger mixed proposal space containing both native and custom actions
- a future `LLM` controller can be evaluated on exactly the same mixed action space as a non-LLM baseline
- the expensive evaluation loop, repair, benchmark, and artifact contract stay matched across the comparison

## 2. Why This Line Exists

The shared multi-backbone pool matrix is still the right platform story for:

- algorithm-agnostic proposal contracts
- family adapters
- cross-backbone raw vs pool comparisons

However, the paper-facing `LLM` controller story now needs a different experimental line:

- the optimizer anchor should remain `NSGA-II`
- the action space should contain both the native `NSGA-II` variation move and the benchmark-specific domain moves
- the `LLM` should win, if it wins, by choosing more useful actions on that same mixed action space

This makes the paper claim sharper:

- `pure-native` shows what classical `NSGA-II` can do alone
- `hybrid-uniform` shows what happens if we enlarge the action space without intelligent scheduling
- `hybrid-llm` shows whether controller intelligence improves search on the same action space

## 3. Relationship To Existing Docs

This spec does not replace the matrix platform docs.

Instead the repository now has two approved optimizer stories:

### 3.1 Platform Track

Defined by:

- `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`

Purpose:

- maintain the multi-backbone raw/pool experiment platform
- keep the shared custom operator pool algorithm-agnostic
- support later cross-backbone controller comparisons

### 3.2 Paper And LLM Track

Defined by this spec and its implementation plan.

Purpose:

- keep the active classical anchor as pure `NSGA-II`
- add one `NSGA-II` hybrid-union action-space line
- compare a weak non-LLM scheduler and a future `LLM` scheduler on that same mixed action set

## 4. Experiment Ladder

The approved paper-facing ladder is:

### P0-Native-NSGA2

- pure `NSGA-II`
- native `SBX + PM`
- no custom operator controller path

Purpose:

- reviewer-friendly classical anchor
- active baseline already implemented in the repository

### P1-Union-Uniform-NSGA2

- still `NSGA-II`
- same benchmark and same budget as `P0`
- offspring proposals are drawn from a mixed union action registry:
  - one native action
  - the approved shared custom operators
- controller is `random_uniform`

Purpose:

- measure what the larger mixed action space contributes before introducing `LLM` policy
- separate “more actions exist” from “actions are chosen intelligently”

### L1-Union-LLM-NSGA2

- same `NSGA-II`
- same benchmark
- same union action registry
- same repair
- same artifact schema
- only the controller changes from `random_uniform` to `llm`

Purpose:

- test whether `LLM` strategy improves feasibility speed, Pareto quality, or expensive-evaluation efficiency on the same mixed action space

## 5. Action-Space Contract

The paper-facing hybrid-union line is not a larger decision space.

The decision vector remains the same eight benchmark variables:

- `processor_x`
- `processor_y`
- `rf_power_amp_x`
- `rf_power_amp_y`
- `battery_pack_x`
- `battery_pack_y`
- `radiator_start`
- `radiator_end`

What changes is the proposal or action space.

For `mode: union`, the action registry should contain:

1. `native_sbx_pm`
2. `sbx_pm_global`
3. `local_refine`
4. `hot_pair_to_sink`
5. `hot_pair_separate`
6. `battery_to_warm_zone`
7. `radiator_align_hot_pair`
8. `radiator_expand`
9. `radiator_contract`

Interpretation:

- `native_sbx_pm` is the repository-owned wrapper around the backbone-native `NSGA-II` proposal move
- the remaining eight actions are the current shared custom operator set

## 6. Spec Contract

The recommended spec form for this line is:

```yaml
algorithm:
  family: genetic
  backbone: nsga2
  mode: union
```

and:

```yaml
operator_control:
  controller: random_uniform | llm
  operator_pool:
    - native_sbx_pm
    - sbx_pm_global
    - local_refine
    - hot_pair_to_sink
    - hot_pair_separate
    - battery_to_warm_zone
    - radiator_align_hot_pair
    - radiator_expand
    - radiator_contract
```

Rationale:

- keep the current `family/backbone/mode` contract intact
- avoid overloading `mode: pool` because the union line is no longer “custom shared operators only”
- reuse the existing controller wiring and trace vocabulary where practical

## 7. Integration Rules

For `NSGA-II hybrid-union`:

- keep native `NSGA-II` parent selection
- keep native `NSGA-II` survival and ranking
- insert the controller only at offspring proposal time
- let the controller choose one action per proposal decision
- in mixed generations, if the chosen action is `native_sbx_pm`, emit one proposal through the repository-owned native wrapper
- preserve an exact all-native fast path so that native-only union can still be checked against raw `NSGA-II`
- if the chosen action is one of the shared custom operators, emit one proposal using the existing numeric-vector operator contract
- send every proposal through the same shared repair step before evaluation

This preserves `NSGA-II` identity while allowing the controller to operate over a mixed proposal vocabulary.

## 8. Fairness Rules

The following must stay matched across `P1` and `L1`:

1. benchmark template
2. benchmark seed set
3. evaluation spec
4. design-variable encoding
5. legality repair
6. union action registry contents
7. artifact schema
8. expensive-evaluation budget
9. representative-candidate extraction rules

Comparison rules:

- `P0` vs `P1` differs by action-space size and controller path
- `P1` vs `L1` differs only by controller decision making

This is fair because the `LLM` is being evaluated precisely as a strategy layer over the same mixed action set, not as a holder of privileged extra actions.

## 9. Evidence Rules

Paper-facing evidence for this line should report:

- budget and seed set
- first feasible evaluation
- feasible rate
- Pareto size
- Pareto-set quality metrics such as hypervolume when appropriate
- action-usage traces
- failure and dominant-violation patterns

Mechanism claims should remain explicit:

- if `hybrid-uniform` beats `pure-native`, the claim is about the mixed action space
- if `hybrid-llm` beats `hybrid-uniform`, the claim is about controller intelligence on a matched action space

## 10. Non-Goals

This line does not require, in its first implementation wave:

- multi-backbone hybrid-union support
- an additional non-LLM adaptive controller rung
- direct `LLM` emission of decision vectors
- replacing the multi-backbone matrix platform track

## 11. Acceptance Criteria

This design is acceptable only if:

1. the active paper-facing classical baseline remains pure `NSGA-II`
2. the new hybrid-union line is documented as a separate paper and `LLM` track, not a replacement for the matrix platform line
3. `P1` and `L1` use the same mixed action registry
4. the native `NSGA-II` move is represented explicitly as `native_sbx_pm`
5. controller and operator traces can show which union action was selected for each proposal decision, including a shared `decision_index` when one native decision expands into sibling offspring on the all-native fast path
6. repository status docs distinguish clearly between:
   - the multi-backbone matrix platform track
   - the `NSGA-II` hybrid-union paper and `LLM` track
