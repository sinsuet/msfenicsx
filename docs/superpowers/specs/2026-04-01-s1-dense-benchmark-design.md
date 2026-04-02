# S1 Dense Benchmark Design

> Status: approved direction for the next compact four-component benchmark and three-mode comparison scene.
>
> This spec adds a new short-name benchmark alongside the current paper-facing four-component baseline. It does not replace the existing benchmark immediately. The purpose is to introduce a more compact, engineering-plausible layout scene that can be reused fairly across `nsga2_raw`, `nsga2_union`, and `nsga2_llm`.

## 1. Goal

Define a new benchmark scene named `S1_dense` so that:

- the benchmark name is short, memorable, and stable in experiment paths
- the scene remains within the current `msfenicsx` solver and optimizer contract
- the four-component layout becomes meaningfully compact rather than visually sparse
- the benchmark stays credible as an engineering layout problem instead of becoming an artificial packing toy
- the same benchmark can be reused fairly across the three official paper-facing modes:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`

## 2. Why A New Benchmark Is Needed

The current active four-component benchmark is useful as a baseline, but it is too sparse for the next stage of engineering-facing comparison work.

Observed issue:

- the current panel domain is large relative to the component footprint
- the current placement region is broad and permissive
- generator placement is legal but not compactness-aware
- optimizer repair enforces legality but does not impose tighter engineering packing logic

As a result, the generated layouts can look too open relative to real spacecraft internal packaging, where area and routing margin are expensive.

This should be treated primarily as a benchmark-definition problem, not as a hidden generator bug.

## 3. Naming Direction

The new benchmark family should use short scenario ids.

Selected naming:

- scenario template id: `S1_dense`
- template file: `scenarios/templates/s1_dense.yaml`
- evaluation spec: `scenarios/evaluation/s1_dense_eval.yaml`
- raw mode optimization spec: `scenarios/optimization/s1_dense_raw.yaml`
- union-uniform optimization spec: `scenarios/optimization/s1_dense_union.yaml`
- union-llm optimization spec: `scenarios/optimization/s1_dense_llm.yaml`

Rationale:

- `S1` is easy to remember in discussion, reports, and figure captions
- `dense` communicates the intended engineering characteristic directly
- short ids produce cleaner experiment roots under `scenario_runs/<scenario_template_id>/experiments/...`
- the file names remain Linux-friendly and avoid mixed-case path friction even though the template id itself is compact

## 4. Selected Design Direction

Three directions were considered:

### Option A: Rename only

Keep the current geometry and only shorten file and scene names.

Pros:

- lowest implementation cost
- zero thermal recalibration effort

Cons:

- does not solve the realism problem
- preserves the visually sparse layout character

Decision: reject.

### Option B: Add a compact four-component benchmark

Keep the four-component thermal story but redefine the geometry envelope and optimization bounds so the same component set must compete for limited usable area.

Pros:

- preserves continuity with the current benchmark and evaluation story
- keeps the decision encoding small and reviewer-friendly
- isolates the change to benchmark realism rather than changing the entire scientific question
- supports fair three-mode comparison

Cons:

- requires benchmark retuning and feasibility calibration

Decision: select this option.

### Option C: Jump directly to six or more components

Build a larger and more realistic subsystem inventory immediately.

Pros:

- stronger apparent realism

Cons:

- changes both density and problem scale at once
- makes it harder to attribute future three-mode differences cleanly
- raises feasibility risk and calibration cost

Decision: defer.

## 5. Benchmark Identity

`S1_dense` is a compact four-component hot/cold thermal benchmark.

It keeps:

- one `1.0 x 0.8` rectangular panel domain
- one top-edge radiator feature
- two operating cases: `hot` and `cold`
- four named component roles:
  - `processor`
  - `rf_power_amp`
  - `obc`
  - `battery_pack`
- the same broad physical story:
  - hot-case cooling pressure from `processor` and `rf_power_amp`
  - cold-case survival pressure from `battery_pack`
  - moderate coupling realism from `obc`

It changes:

- layout density
- usable placement envelope
- per-component motion envelope
- benchmark naming and experiment identity

## 6. Engineering Realism Principles

`S1_dense` should feel constrained, but still physically credible.

The benchmark must follow these principles:

### 6.1 Compact but not impossible

- The scene should not be an extreme packing puzzle.
- Feasible layouts must still exist under the current repair and optimization pipeline.
- The layout should look like a constrained electronics deck, not like rectangles forced into near-contact everywhere.

### 6.2 Thermal role consistency

- `processor` and `rf_power_amp` should remain the main hot-case drivers.
- `battery_pack` should remain thermally sensitive in the cold case and should not be treated as a generic movable box.
- `obc` should remain a moderate-load coupling component, not a dominant hotspot.

### 6.3 Fairness across modes

- `nsga2_raw`, `nsga2_union`, and `nsga2_llm` must share the same benchmark source, evaluation spec, design encoding, repair contract, and expensive-evaluation budget.
- The benchmark must not privilege one mode by introducing a scene that only specialized operators can traverse.

### 6.4 Keep first implementation aligned with current repair scope

The current optimizer repair path is strongest on:

- variable clamping
- overlap repair
- radiator interval repair

The first `S1_dense` implementation should therefore prefer:

- tighter global placement regions
- tighter design-variable bounds
- moderate geometry retuning

and should avoid relying on complex optimizer-time keep-out semantics that the current repair layer does not explicitly restore.

## 7. Geometry And Layout Direction

## 7.1 Panel domain

Keep the panel domain at:

- width: `1.0`
- height: `0.8`

Rationale:

- preserves continuity with the current benchmark
- avoids mixing geometry-scale changes with density changes
- keeps solver and visualization interpretation stable

## 7.2 Placement region

The main change is to shrink the usable placement deck substantially relative to the current benchmark.

Target direction:

- reduce effective placement area to roughly `50%` to `60%` of the current placement-region area
- keep the compact deck centered in the lower-to-middle panel
- preserve a top-side thermal-control corridor aligned with the radiator story

This creates real competition for space without changing the panel outline itself.

## 7.3 Component size tuning

Component families should be retained, but their sampled size ranges should be slightly enlarged or tightened around larger nominal footprints so that overall occupancy increases.

Target occupancy direction:

- current component occupancy over placement area is too low for the desired engineering feel
- `S1_dense` should aim for component-area occupancy over usable placement area in the rough range of `18%` to `25%`

This is intentionally still below extreme packing density because real routing, fastening, insulation, and structural margin still exist.

## 7.4 Relative placement logic

The benchmark should encourage the following thermal logic:

- `processor` and `rf_power_amp` should be allowed to approach the radiator-side half of the deck
- `battery_pack` should be biased toward a safer lower or central-lower region rather than hugging the hottest local cluster
- `obc` should provide coupling realism near the middle of the deck

The first implementation may express this through conservative variable bounds rather than through hard family-specific placement rules if that is simpler and more robust under the current optimizer repair architecture.

## 8. Optimization Encoding Direction

The first `S1_dense` line should keep the same eight-variable decision encoding as the current paper-facing line:

- `processor_x`
- `processor_y`
- `rf_power_amp_x`
- `rf_power_amp_y`
- `battery_pack_x`
- `battery_pack_y`
- `radiator_start`
- `radiator_end`

Rationale:

- keeps the problem reviewer-friendly
- keeps the three-mode comparison fair
- isolates the benchmark change to scene realism rather than changing the optimizer state dimensionality

The `obc` should remain non-optimized in the first `S1_dense` iteration unless later calibration shows that a ninth and tenth variable are required.

## 9. Evaluation Direction

`S1_dense` should preserve the current multicase objective story:

- hot-case hotspot suppression
- cold-case battery survivability
- radiator resource restraint

and preserve the current thermal-constraint story:

- hot electronics limits
- cold battery floor
- hot spread control

The first version should therefore reuse the same evaluation semantics as the current four-component line, with renaming only where needed for consistency.

Numeric thresholds may need recalibration after compact-layout validation, but the objective meaning should not change.

## 10. Three-Mode Experiment Contract

`S1_dense` is intended to become a clean comparison scene for:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

The following must remain matched across all three modes:

1. scenario template
2. benchmark seed set
3. evaluation spec
4. design-variable encoding
5. repair logic
6. expensive-evaluation budget
7. representative-solution extraction rules
8. run artifact layout

This ensures that:

- `raw` measures native `NSGA-II` alone
- `union` measures action-space expansion without `LLM`
- `llm` measures controller value on the same action space

## 11. Implementation Boundaries

The first implementation of `S1_dense` should:

- add new scene/spec files rather than mutating the old benchmark in place
- avoid changing `core/` contracts unless a real missing capability is discovered
- avoid introducing scenario-specific logic into optimizer wrappers
- prefer template-level and spec-level configuration over hardcoded repair exceptions

The current long-name four-component benchmark should remain in the repository during the transition so that:

- older reports remain interpretable
- calibration can be compared side by side
- the new scene can be validated before any mainline replacement decision

## 12. Acceptance Criteria

`S1_dense` is successful when:

1. generated layouts appear materially more compact than the current four-component benchmark
2. the compactness arises from benchmark definition rather than hidden scene-specific repair hacks
3. the component arrangement still looks thermally and mechanically plausible
4. the benchmark remains solvable and feasible designs still exist
5. all three official modes can run on the same benchmark contract without special-case handling
6. experiment paths and report references become shorter and easier to remember

## 13. Planned Deliverables

The first implementation slice should produce:

- a new compact template at `scenarios/templates/s1_dense.yaml`
- a matching evaluation spec at `scenarios/evaluation/s1_dense_eval.yaml`
- three short-name optimization specs:
  - `scenarios/optimization/s1_dense_raw.yaml`
  - `scenarios/optimization/s1_dense_union.yaml`
  - `scenarios/optimization/s1_dense_llm.yaml`
- focused generator, optimizer, and CLI test updates where required
- README and `AGENTS.md` updates only if `S1_dense` becomes the active paper-facing benchmark rather than an added benchmark

## 14. Non-Goals For This Slice

This spec does not introduce:

- a six-plus-component benchmark
- new canonical physics beyond the current steady conduction plus nonlinear sink line
- new optimizer-layer scene-specific repair hacks
- benchmark-specific `LLM` prompt tuning
- scene-specific exceptions for particular seeds or operator names

## 15. Recommended Next Step

After this spec is approved, the next step should be a concrete implementation plan that:

- defines exact `S1_dense` geometry numbers
- identifies the file set to create or modify
- adds benchmark-validation and calibration steps before any full three-mode report run
