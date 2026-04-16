# S1 Typical Layout Realism Design

> Status: drafted after user-approved design direction. Pending final spec review before implementation planning.

## 1. Goal

Improve `s1_typical` layout generation so that generated scenes look and behave more like realistic compact engineering layouts while preserving the active paper-facing benchmark contract:

- still one operating case
- still fifteen named components
- still `x/y` optimization only for all fifteen components
- still no optimized rotation variable
- still one top-edge sink window
- still the same single-case raw / union / llm optimizer ladder

The change is about making the generated physical scene more credible, not about redefining the benchmark into a different optimization problem.

## 2. Current Diagnosis

The current `s1_typical` layout looks sparse and visually synthetic for four structural reasons.

### 2.1 Component semantics are too uniform

In [scenarios/templates/s1_typical.yaml](/home/hymn/msfenicsx/scenarios/templates/s1_typical.yaml), all fifteen component families:

- use `shape: rect`
- use very similar sizes
- use the same coarse `thermal_tags: [payload]`
- have no layout-oriented semantic hints

As a result, the template does not encode any distinction between boards, edge connectors, rounded housings, elongated items, or irregular packaged devices.

### 2.2 Area budget is too low

The current template allocates total component area `0.108`.

- panel area: `0.800`
- placement-region area: `0.603`
- component area / panel area: `13.5%`
- component area / placement-region area: `17.9%`

Even with better packing, that area budget still reads as under-populated for a representative engineering deck.

### 2.3 The generator only enforces legality

In [core/generator/layout_engine.py](/home/hymn/msfenicsx/core/generator/layout_engine.py), placement is currently:

1. sample one component
2. draw `x/y` uniformly inside the placement region
3. accept if inside domain, outside keep-out regions, and non-overlapping

This guarantees legal layouts, but it does not optimize for:

- compactness
- cluster structure
- edge affinity
- sink awareness
- service gaps
- alignment
- corridor preservation

The result is "randomly scattered but legal" rather than "structured and realistic."

### 2.4 Visualization currently hides shape fidelity

[core/solver/field_export.py](/home/hymn/msfenicsx/core/solver/field_export.py) exports only component bounds, and [visualization/case_pages.py](/home/hymn/msfenicsx/visualization/case_pages.py) renders those bounds as rectangles.

Even though [core/geometry/primitives.py](/home/hymn/msfenicsx/core/geometry/primitives.py) already supports `rect`, `circle`, `capsule`, `slot`, and `polygon`, the page-level output collapses every footprint back into a rounded rectangle.

### 2.5 Measured compactness is poor

Across seeds `1..100`, the current generator produces the following approximate statistics:

- placement-region coverage by the component bounding envelope: mean `83.8%`
- true component area divided by that envelope area: mean `21.5%`
- component nearest-neighbor edge gap: mean `0.0385`

This is the signature of a spread-out arrangement with many voids rather than a compact packed scene.

## 3. Approaches Considered

### Option A: Tune only the template geometry

Increase component sizes and slightly tighten placement regions without changing the generator.

Pros:

- lowest implementation cost
- minimal risk to generator internals

Cons:

- still produces random scatter
- does not create meaningful component classes
- does not solve the visual realism problem

Decision: reject as insufficient.

### Option B: Rule-driven semantic layout generation

Introduce a small set of component-layout semantics in the template and use a multi-stage placement heuristic:

- place anchors first
- place grouped thermal and functional clusters second
- run a compactness refinement pass last

Pros:

- high interpretability
- stable and testable behavior
- fits the current benchmark identity
- can preserve the existing `32D` optimizer encoding

Cons:

- requires coordinated updates across template, generator, repair, and visualization

Decision: select this option.

### Option C: Optimization-style scene synthesis

Replace the random generator with a force-based or annealing-based layout search that minimizes a compactness score.

Pros:

- potentially strongest packing quality

Cons:

- higher tuning burden
- lower explainability
- less deterministic to debug and maintain

Decision: reject for now.

## 4. Selected Design

The selected direction is to keep the benchmark contract stable while making the generated scene semantically richer and spatially more realistic.

### 4.1 Benchmark invariants to preserve

The following remain unchanged:

- fifteen fixed named component families
- one top-edge sink window
- single-case canonical flow
- `x/y` decision variables only for all components
- no optimized `rotation_deg`
- no optimized geometry, material, or power
- same paper-facing optimization spec family

This design changes the generated benchmark scene quality, not the optimization contract shape.

### 4.2 Template semantic enrichment

The `s1_typical` template should stop modeling every item as an anonymous payload rectangle.

Each component family should be able to declare optional layout semantics such as:

- `layout_tags`
  - examples: `high_power`, `logic_board`, `edge_connector`, `sensor_sensitive`, `elongated`, `service_clearance`
- `placement_hint`
  - examples: `top_band`, `center_mass`, `left_edge`, `right_edge`, `bottom_band`
- `adjacency_group`
  - lightweight grouping for intentional clustering
- `clearance`
  - minimum preferred gap, separate from strict non-overlap legality

These hints belong in the template as hand-authored scene semantics. The generator remains responsible for interpreting them.

### 4.3 Shape mix for realism

The active benchmark should use a controlled mixed footprint vocabulary.

Recommended starting mix across fifteen components:

- `8-10` board-like `rect` families
- `2-3` elongated `slot` or `capsule` families
- `1-2` `circle` families
- `1-2` constrained `polygon` families

This keeps the scene mostly recognizable as engineered modules while avoiding the current "all near-square rectangles" look.

### 4.4 Fixed-orientation realism without adding rotation variables

The benchmark does not expose `rotation_deg` as an optimization variable, and that should stay true.

However, the template generator may still assign fixed or sampled family-level orientations for selected families, for example:

- edge connectors locked to `0` or `90`
- elongated parts chosen from a small family-specific orientation set

This preserves the optimizer contract while improving realism.

### 4.5 Higher target area budget

The initial target for total component area should move from `17.9%` of placement-region area to roughly `30-40%`.

The exact target should be chosen conservatively enough to:

- visibly reduce wasted empty space
- keep layouts solvable and legible
- avoid turning the benchmark into a near-impossible dense-packing problem

This should be implemented through template geometry updates, not by shrinking the whole placement region into an artificially tiny box.

### 4.6 Multi-stage placement engine

The generator should move from uniform scatter to staged semantic placement.

Proposed flow:

1. Sample all component geometry and semantic hints.
2. Partition components into placement order buckets:
   - anchors
   - high-power / sink-aware group
   - grouped functional modules
   - free fillers
3. Place anchors using their preferred edges or bands.
4. Place grouped components near target centroids while respecting keep-out regions and preferred clearances.
5. Place remaining components into legal gaps.
6. Run a compactness refinement pass that attempts small legal moves to:
   - reduce global bounding-envelope area
   - reduce cluster dispersion
   - preserve required clearances
   - avoid breaking edge affinity
7. If semantic placement fails, fall back to the existing simple legal sampler rather than failing the whole case immediately.

The fallback keeps robustness. The semantic path becomes the preferred generator, not the only possible path.

### 4.7 Compactness scoring

The generator should gain a small internal scoring function for comparing candidate placements during refinement.

Recommended score terms:

- global layout envelope area
- summed distance to adjacency-group centroid
- penalty for violating preferred minimum gaps
- penalty for drifting high-power groups away from the sink corridor
- penalty for isolated elongated edge-aligned parts appearing in interior regions

This score is for generation quality only. It is not a new paper-facing optimization objective.

### 4.8 Shape-aware downstream support

If mixed shapes become part of the official benchmark, downstream geometry handling must remain coherent.

Required follow-on changes:

- visualization must render real outlines, not only rectangular bounds
- representative bundle exports must include footprint outlines
- optimizer repair must stop assuming every component has `geometry.width` and `geometry.height`

Without these changes, the benchmark would be physically richer in the template but still visually or operationally treated as rectangles downstream.

## 5. Module-Level Design

### 5.1 `scenarios/templates/`

Update [s1_typical.yaml](/home/hymn/msfenicsx/scenarios/templates/s1_typical.yaml) to encode:

- richer component shapes
- more realistic size distribution
- semantic layout hints
- stronger component-family differentiation

No business logic should move into `scenarios/`. It remains a declarative input layer.

### 5.2 `core/generator/`

[layout_engine.py](/home/hymn/msfenicsx/core/generator/layout_engine.py) becomes the main implementation site for:

- placement ordering
- anchor placement
- cluster placement
- compactness refinement
- fallback behavior

[parameter_sampler.py](/home/hymn/msfenicsx/core/generator/parameter_sampler.py) should sample any new optional template fields that affect generated layout behavior, including fixed-or-choice orientation hints.

### 5.3 `core/geometry/`

Existing polygon footprint logic is already sufficient as the geometric truth source.

Additional helpers may be added for:

- shape-aware spacing
- edge affinity checks
- envelope metrics
- outline serialization

### 5.4 `optimizers/`

[repair.py](/home/hymn/msfenicsx/optimizers/repair.py) currently computes overlap separation using `geometry.width` and `geometry.height`, which is rectangle-specific.

It should become footprint-aware so that official optimizer runs remain compatible with mixed shapes in the benchmark case.

The optimization specs should continue to expose the same `32` variables unless a later, separate design intentionally changes the benchmark contract.

### 5.5 `visualization/`

Representative layout figures should render actual footprints.

This requires:

- field export to preserve shape outlines
- case page rendering to draw polygons and circles instead of rectangle bounds only
- tests updated to validate mixed-shape rendering

## 6. Verification Strategy

The new generator should be validated at three levels.

### 6.1 Schema and generation correctness

- template remains valid
- generated cases remain inside domain
- keep-out regions remain respected
- no overlapping footprints

### 6.2 Compactness and realism regression checks

Add focused tests for layout-quality metrics such as:

- total sampled component area ratio
- bounding-envelope fill ratio
- nearest-neighbor gap distribution
- anchor placement compliance
- group compactness

These checks should use generous, stable thresholds rather than brittle exact placements.

### 6.3 Visualization fidelity

Mixed-shape scenes must render with shape-aware outlines in representative pages and not regress to axis-aligned box placeholders.

## 7. Non-Goals

This design does not:

- add rotation as an optimization variable
- change the two official paper objectives
- add new operating cases
- add multi-board or hierarchical assemblies
- turn generation into a full CAD-like packing solver

## 8. Risks And Mitigations

### Risk 1: Generator becomes too brittle

Mitigation:

- keep fallback to simple legal sampling
- use heuristic thresholds instead of exact-placement expectations

### Risk 2: Mixed shapes break optimizer repair

Mitigation:

- update repair in the same implementation track before claiming official support

### Risk 3: Layout-quality metrics become flaky

Mitigation:

- test distributions and thresholds over multiple seeds
- avoid asserting specific coordinates

## 9. Implementation Phasing

Recommended phasing:

1. Update template semantics and target geometry mix.
2. Implement rule-driven semantic placement plus compactness refinement.
3. Make field export and visualization shape-aware.
4. Upgrade optimizer repair to shape-aware overlap handling.
5. Add focused tests for generation, visualization, and optimizer compatibility.

This order gives fast visible improvement while keeping the official optimization route coherent before completion.
