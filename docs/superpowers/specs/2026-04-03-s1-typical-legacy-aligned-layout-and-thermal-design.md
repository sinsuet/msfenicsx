# S1 Typical Legacy-Aligned Layout And Thermal Design

> Status: approved direction after comparing the current `s1_typical` mainline against the reference `radiation_gen` flow and reviewing real generated artifacts.
>
> This design does not reset the benchmark again. It keeps the active `s1_typical` paper-facing contract and retrofits the parts of the legacy generator that actually produced denser layouts and stronger thermal contrast.

## 1. Goal

Improve `s1_typical` so that generated scenes are:

- more compact and visually closer to a real electronics deck
- less dominated by empty interior whitespace
- thermally less flat, with hotspot structure driven by both sink distance and local heat density
- still fully compatible with the active single-case `s1_typical` raw / union / llm pipeline

The intended result is a `legacy-inspired, mainline-compatible` upgrade:

- keep the current clean `msfenicsx` contracts and architecture
- recover the useful realism mechanisms from `radiation_gen`
- avoid reintroducing the retired random-count, random-domain, multi-cooling-line dataset workflow as the new paper-facing mainline

## 2. Evidence And Diagnosis

### 2.1 Current `s1_typical` Is Still Too Sparse

The current end-to-end chain has already been run on the active mainline:

- validate
- generate
- solve
- evaluate
- render

Representative artifact bundle:

- `scenario_runs/real_checks/20260403_layout_realism_seed11/s1_typical/s1_typical-seed-0011/pages/index.html`
- `scenario_runs/real_checks/20260403_layout_realism_seed11/s1_typical/s1_typical-seed-0011/figures/layout.svg`
- `scenario_runs/real_checks/20260403_layout_realism_seed11/s1_typical/s1_typical-seed-0011/figures/layout-preview.png`

Observed `seed=11` signals:

- `component_count = 15`
- `shape_families = ['capsule', 'circle', 'rect', 'slot']`
- `bbox_occupancy_ratio = 0.2386`
- `temperature_min = 301.814 K`
- `temperature_max = 303.581 K`
- `temperature_span = 1.7667 K`

This confirms that the recent mixed-shape and shape-aware rendering work improved appearance, but it did not solve the deeper density problem. The layout still reads as too loose for a realistic packed deck.

### 2.2 The Thermal Field Is Systematically Too Flat

The small temperature span is not a one-off seed artifact.

Measured multi-seed spans on the current mainline:

- `seed 11 -> 1.7667 K`
- `seed 17 -> 1.8463 K`
- `seed 23 -> 1.8911 K`
- `seed 29 -> 1.8251 K`
- `seed 31 -> 1.9134 K`

The active baseline therefore behaves like a nearly isothermal plate with only mild edge-cooling influence. That is not close to the reference legacy behavior and is not a convincing research layout benchmark.

### 2.3 Root Cause In The Current Mainline

The current behavior comes from a combination of layout and physics choices.

#### Layout-side cause

In `core/generator/layout_engine.py`, the current generator:

- uses broad `placement_hint` bands
- places components legally inside those bands
- applies only a light one-pass compactness refinement
- scores mainly by global envelope area plus simple edge-band penalties

What it does not currently do:

- define a target dense core
- explicitly reserve structured edge lanes
- place anchor families first into named zones
- sort by area or thermal importance before packing
- enforce an occupancy target
- treat compactness as a first-class generation objective

So the generator is better than pure scatter, but still not density-driven.

#### Physics-side cause

In `scenarios/templates/s1_typical.yaml`, the current default physics is:

- `panel_substrate conductivity = 25`
- `electronics_housing conductivity = 160`
- `sink_temperature = 286 K`
- `transfer_coefficient = 10`

In `core/solver/physics_builder.py`, load power is applied as:

- `total_power / component_polygon.area`

That means each component dumps heat uniformly over its full footprint. Combined with the relatively high conductivities, the field smooths quickly, so hotspot ordering is driven mostly by vertical distance to the top sink instead of by local power concentration.

### 2.4 Sensitivity Checks Show Conductivity And Source Localization Matter, Not `h`

The current mainline has already been perturbed to test thermal sensitivity.

Measured span responses:

- `baseline -> 1.7667 K`
- `panel_k_5 -> 7.1770 K`
- `panel_k_1 -> 32.3783 K`
- `comp_k_20 -> 2.7182 K`
- `panel5_comp20 -> 9.4932 K`
- `sink_h_3 -> 1.7695 K`

Interpretation:

- lowering `transfer_coefficient` mostly shifts the absolute level and barely changes internal contrast
- reducing conductivity, especially panel conductivity, strongly increases internal gradients
- the next realism lever after conductivity is source localization, because the current solver still spreads power across the entire component footprint

## 3. What The Legacy Reference Actually Does Better

The old reference workflow under `radiation_gen/` was executed in a temporary output directory and produced real comparison evidence.

Representative run root:

- `/tmp/radiation_gen_run_20260403/radiation_20260403_013928`

Observed successful sample statistics:

- `sample_00000 -> area ratio 0.4271, span 87.514 K`
- `sample_00001 -> area ratio 0.4629, span 74.602 K`
- `sample_00003 -> area ratio 0.4192, span 89.171 K`
- `sample_00004 -> area ratio 0.4944, span 98.990 K`

Representative artifact paths:

- `/tmp/radiation_gen_run_20260403/radiation_20260403_013928/samples/sample_00004/layout.png`
- `/tmp/radiation_gen_run_20260403/radiation_20260403_013928/samples/sample_00004/temperature.png`
- `/tmp/radiation_gen_run_20260403/radiation_20260403_013928/samples/sample_00004/heat_source.png`

The legacy generator looks more realistic for three structural reasons:

- layout density is explicitly high: total component area ratio is usually `0.4~0.5`
- material conductivity is extremely low: `kappa = 1.155`
- heat is locally intense and cooling is spatially localized, so the field is hotspot-driven rather than nearly uniform

Important conclusion:

The legacy effect is not just a better placer. It is the result of density, local heat flux, and localized cooling acting together.

## 4. Constraints We Must Preserve

The new design must keep the active mainline identity from `AGENTS.md`.

### 4.1 Hard Invariants

Do not change:

- `s1_typical` as the only active paper-facing benchmark
- one operating case
- fifteen fixed named components
- `x/y`-only optimization for all fifteen
- no optimized rotation variable
- the current `32D` decision encoding
- the single top-edge sink feature as the official paper-facing sink model
- the canonical `scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle` flow
- the raw / union / llm optimizer ladder

### 4.2 Explicit Non-Goals

Do not do any of the following as part of this work:

- fully restore `radiation_gen` as a new runtime path
- adopt random component count as the new paper-facing benchmark
- adopt random square domain size as the new paper-facing benchmark
- switch the official benchmark to multiple cooling lines
- expose geometry, material, power, or rotation as new optimizer decision variables

## 5. Options Considered

### Option A: Patch Layout Density Only

Increase footprint sizes and tighten the existing placement heuristics, but leave the thermal model mostly unchanged.

Pros:

- smallest code change
- minimal solver risk

Cons:

- does not address the thermally flat `~2 K` behavior
- would still leave hotspot ranking dominated by `y` location
- would look better without behaving more realistically

Decision: reject.

### Option B: Reproduce `radiation_gen` Nearly As-Is

Reuse the legacy project almost directly, including area-ratio logic, random domain sizing, and multi-edge cooling.

Pros:

- closest to the teacher-provided reference
- likely to recreate strong contrast quickly

Cons:

- conflicts with the active `s1_typical` benchmark contract
- breaks single-case fixed-scene paper-facing semantics
- would reintroduce a second architecture instead of improving the current one

Decision: reject.

### Option C: Legacy-Inspired, Mainline-Compatible Retrofit

Keep the current clean mainline, but reintroduce the three legacy ideas that matter:

- density-driven layout
- localized heat generation
- more local sink-driven thermal contrast

Pros:

- preserves the approved paper-facing benchmark
- fixes both sparse geometry and flat thermals
- keeps optimizer, repair, and artifact infrastructure usable

Cons:

- requires coordinated changes across template, generator, solver, and reporting
- needs deliberate calibration, not one-parameter tuning

Decision: select this option.

## 6. Selected Design

### 6.1 Build On The Current Mixed-Shape Mainline Instead Of Replacing It

The recent layout-realism work already delivered:

- mixed-shape component families
- family-level layout semantics such as `layout_tags`, `placement_hint`, and `adjacency_group`
- shape-aware field export and page rendering
- mixed-shape repair support

This design keeps those gains and adds the next missing layer:

- stronger spatial organization
- explicit occupancy targets
- thermal realism calibration

### 6.2 Introduce Generation-Only Deck Zones

The placement region should remain the canonical optimization domain, but generation should stop treating it as one undifferentiated rectangle.

Add generation-only zone semantics under `generation_rules`, for example:

- `dense_core`
- `top_sink_band`
- `left_io_edge`
- `right_service_edge`

These are not new optimizer variables and not new top-level contracts. They are generation hints that tell the layout engine how to produce a realistic initial case.

Recommended intent:

- `top_sink_band`: sink-coupled and high-power families that should plausibly interact with the top sink
- `left_io_edge`: edge connectors and IO-heavy families
- `right_service_edge`: routed or service-oriented elongated families
- `dense_core`: the main packed electronics block

### 6.3 Move From Legal Placement To Density-Driven Placement

The generator should follow a more deliberate packing order.

Recommended placement flow:

1. materialize all component footprints and metadata
2. classify each family into zone and priority buckets
3. place edge anchors first
4. place large and high-power dense-core families next, ordered by effective footprint area
5. place remaining support families into legal residual gaps
6. run a local compactness refinement pass that minimizes a multi-term score instead of only envelope area
7. if the semantic path fails, fall back to the current robust legal sampler

Recommended score terms:

- dense-core envelope area
- total component-to-zone drift
- adjacency-group dispersion
- preferred-clearance slack penalties
- penalty for leaving large voids in the dense core

### 6.4 Add Explicit Layout Quality Targets

The generator should no longer be judged only by “did all components fit?”

Add first-class layout metrics, with two gates:

- `active_deck_occupancy`
- `bbox_fill_ratio`

Recommended definitions:

- `active_deck_occupancy = total_component_area / active_deck_area`
- `bbox_fill_ratio = total_component_area / layout_bbox_area`

Both are needed:

- `active_deck_occupancy` prevents a low-fill deck
- `bbox_fill_ratio` prevents fake improvements created only by shrinking the denominator

Calibration targets for the updated generator:

- `active_deck_occupancy = 0.38~0.45`
- `bbox_fill_ratio >= 0.38`
- five-seed generation with no dropped components for `11, 17, 23, 29, 31`

### 6.5 Thermal Realism V1

The thermal upgrade should be intentionally moderate. It should move toward the legacy behavior without fully copying the old physics envelope.

#### Material calibration

Set the mainline default conductivities to a middle regime:

- `panel_substrate conductivity -> 5`
- `electronics_housing conductivity -> 20`

Rationale:

- this matches the sensitivity evidence that `5/20` produces meaningful internal contrast without jumping all the way to legacy-level `kappa=1.155`
- it keeps the benchmark inside a believable engineering calibration range while materially improving hotspot contrast

#### Sink calibration

Keep one top-edge sink, but stop using a near-full-width default sink window.

Selected direction:

- the template default sink span should be centered and more local than the current full-band baseline
- the optimization budget constraint remains `case.total_radiator_span <= 0.48`
- the generated default case should not consume more sink span than the allowed budget, and it should preferably start below that ceiling

This preserves the paper-facing single-sink identity while making the thermal field more spatially structured.

#### Load localization

Introduce optional per-load `source_area_ratio` semantics in the template and carry them into the generated case.

Recommended implementation:

- each load still keeps `total_power`
- the solver derives an internal source polygon by scaling the component footprint about its centroid
- the scaled polygon area approximates `component_area * source_area_ratio`
- heat source density becomes `total_power / source_polygon.area`, not `total_power / component_polygon.area`

This is the most important thermal realism addition after the conductivity retune.

Recommended first-pass ratios:

- high-power families: `0.18~0.30`
- logic / service families: `0.30~0.45`
- sensor / low-power families: `0.45~0.65`

This keeps total power unchanged while producing more realistic local hotspots.

### 6.6 Power-Tier Rebalancing Is Phase 2, Not Phase 1

The current power ladder is still relatively smooth across all fifteen families. That is another reason the field is too even.

However, this should not be the first change.

Phase 1:

- keep the current family count and general power ordering
- first fix density, conductivity, sink span, and source localization

Phase 2, only if needed after calibration:

- consolidate the highest powers into a smaller, stable subset of thermal-heavy families

This avoids mixing too many physics changes into the first correction pass.

### 6.7 Preserve Optimizer Compatibility

The optimizer layer should remain structurally unchanged:

- same design-vector shape
- same repair strategy family
- same cheap-constraint-before-PDE rule

But it must remain compatible with the denser generated cases.

Implications:

- the current mixed-shape repair path should be revalidated against the denser template
- if the denser geometry stresses local legality restoration, repair parameters may need moderate retuning
- no family-specific hard constraints should be baked into repair as benchmark-specific hacks

### 6.8 Make Layout Signals Visible In Artifacts

Layout realism should not be judged only by manual image inspection.

Add generation-time layout metrics to case provenance and surface them in:

- evaluation derived signals
- representative case pages
- calibration reports

At minimum, expose:

- `layout.active_deck_occupancy`
- `layout.bbox_fill_ratio`
- `layout.nearest_neighbor_gap_mean`

These are diagnostics, not new paper-facing optimization objectives.

## 7. Module-Level Design

### 7.1 `scenarios/templates/s1_typical.yaml`

Update the hand-authored template to define:

- generation-only zone semantics under `generation_rules`
- a denser area budget consistent with the new occupancy target
- a narrower default top sink span
- the `5/20` conductivity pair
- per-family load localization hints via optional `source_area_ratio`

### 7.2 `core/schema/validation.py`

Extend validation so the new optional template and case fields are checked explicitly instead of remaining untyped pass-through data.

In scope:

- optional load-rule and load-level `source_area_ratio`
- optional generation-rule zone payload shape

### 7.3 `core/generator/layout_engine.py`

Refactor generation around:

- zone-aware anchor placement
- area-ordered dense-core packing
- stronger compactness scoring
- fallback to the current legal sampler when necessary

### 7.4 `core/generator/layout_metrics.py`

Expand layout metrics to include `active_deck_occupancy` and any other calibration signals needed to keep the new generator honest.

### 7.5 `core/generator/parameter_sampler.py` And `core/generator/case_builder.py`

Carry the new optional load localization and layout-metric provenance data from template sampling into the canonical generated case.

### 7.6 `core/solver/case_to_geometry.py` And `core/solver/physics_builder.py`

Interpret the new source-localization metadata and construct effective source regions before assembling the PDE.

The official PDE remains steady conduction with nonlinear radiation-style sink boundaries. This design changes source support, not the benchmark equation class.

### 7.7 `evaluation/metrics.py` And `visualization/case_pages.py`

Surface the new layout realism signals in evaluation artifacts and representative pages so calibration evidence becomes easy to inspect.

### 7.8 `optimizers/repair.py`

Keep the current projection plus local legality restoration approach, but revalidate it against the denser template and tune only if the new footprint packing exposes robustness issues.

## 8. Validation Targets

The updated mainline should be considered successful only if all of the following are demonstrated.

### 8.1 Generation Targets

- generated `s1_typical` cases remain legal for seeds `11, 17, 23, 29, 31`
- no component dropouts
- `active_deck_occupancy` lands in the `0.38~0.45` target band on the calibration sample
- `bbox_fill_ratio` materially improves over the current `~0.24` representative behavior

### 8.2 Thermal Targets

- five-seed solved cases show `temperature_span = 8~20 K`
- hotspot ranking is not explained only by `y` position; power density must matter
- the updated benchmark remains numerically solvable and evaluation-compatible

### 8.3 Architecture Targets

- no contract regression for the active paper-facing specs
- no revival of retired multi-case or legacy benchmark assets
- no benchmark-specific controller hacks in the optimizer layer

## 9. Rollout Sequence

The implementation should proceed in three phases.

### Phase 1: Layout Densification

- template zone semantics
- target occupancy metrics
- dense-core placement
- generator regression tests

### Phase 2: Thermal Realism V1

- `5/20` conductivity retune
- narrower default top sink span
- localized source support via `source_area_ratio`
- solver and case tests

### Phase 3: Reporting And Calibration

- layout metrics in provenance and pages
- repair revalidation
- five-seed smoke runs
- evidence report under `docs/reports/`

This sequence keeps the highest-risk physical changes after the geometric generation path is already behaving correctly.
