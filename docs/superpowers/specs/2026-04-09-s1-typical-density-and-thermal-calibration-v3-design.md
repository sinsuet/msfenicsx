# S1 Typical Density And Thermal Calibration V3 Design

> Status: approved direction after re-checking the active `s1_typical` layout-density metric, the original `radiation_gen` area-ratio definition, current optimizer legality gaps, and the teacher feedback on thermal plausibility.
>
> This design supersedes the earlier partial realism retunes by directly recalibrating the active `s1_typical` template instead of introducing a new benchmark template or optimizer-side family windows.

## 1. Goal

Upgrade the active paper-facing `s1_typical` mainline so that:

- layouts are visibly denser and closer to a realistic packed electronics deck
- the official density target aligns with the original `radiation_gen` notion of area ratio
- optimized representatives no longer fake compactness by collapsing clearance to zero
- all fifteen components clearly participate in waste-heat generation
- temperature fields show a wider and more interpretable contrast range
- the physics story can answer the teacher's questions about ambient background cooling and hotspot sources without changing the benchmark class

This work must preserve the active benchmark identity from `AGENTS.md`:

- `s1_typical` remains the active paper-facing benchmark
- one operating case
- fifteen named components
- `x/y` optimization only
- no optimized rotation
- `32D` decision encoding
- `summary.temperature_max` and `summary.temperature_gradient_rms` remain the paper-facing objectives
- the official sink model remains the current single top-edge `line_sink`
- `raw`, `union`, and `llm` remain directly comparable

## 2. Problem Statement

### 2.1 The Density Target Has Been Mixed Across Different Denominators

The active codebase currently exposes several density-like quantities with different meanings.

In `core/generator/layout_metrics.py`:

- `component_area_ratio = total_component_area / placement_area`
- `active_deck_occupancy = total_component_area / active_deck_area`
- `bbox_fill_ratio = total_component_area / layout_bbox_area`

These are not interchangeable.

For the current `s1_typical` geometry:

- total component area is approximately `0.223742`
- full panel area is `1.0 * 0.8 = 0.8`
- current `placement_region` area is `(0.95 - 0.05) * (0.72 - 0.05) = 0.603`
- therefore current `component_area_ratio ~= 0.371`
- current full-panel absolute fill is only `0.2797`

This matters because the original `radiation_gen` `area_ratio_range: [0.4, 0.5]` is not a full-panel absolute fill target. It is explicitly a layout-domain-relative target:

- `total_component_area / layout_domain_area`

The active mainline therefore cannot claim to match the reference density regime unless the official target is defined using the same denominator family.

### 2.2 The Current Template Is Still Too Loose Even After Earlier Retunes

Even after the previous realism updates, the deck still reads as under-packed because:

- component footprint budget is still materially below the intended `0.4~0.5` layout-domain regime
- the effective placement region is still broad enough to tolerate large interior voids
- optimized solutions can legally collapse to near-touching layouts because optimizer legality only rejects direct overlap

### 2.3 Minimum Gap Exists In Generation But Not In Optimization

The generator already carries family-level `clearance` and checks it during placement.

However, the active optimizer-side legality path still only enforces:

- in-bounds
- direct overlap rejection
- sink-span constraint

It does not consistently enforce:

- `distance(i, j) >= max(clearance_i, clearance_j)`

As a result:

- generated baseline layouts may look reasonable
- but `raw` and `union` representatives can drift toward unrealistic near-contact packing

### 2.4 The Thermal Story Is Still Too Flat And Too Implicit

The active single-case mainline already assigns nonzero `total_power` to all fifteen components, so the answer to "do other components produce waste heat?" is already yes.

The real issues are different:

- only a minority of components have explicit `source_area_ratio`
- components without `source_area_ratio` currently spread heat over the full component polygon
- the power ladder is too smooth and does not create a strong hot / warm / cool hierarchy
- the solver currently adds convective and radiative sink terms only on the top `line_sink`
- `ambient_temperature` currently exists mostly as a default scalar and is not yet a first-class weak outer-boundary background cooling condition in the active single-case path

These choices flatten local heat density and make the temperature field harder to defend qualitatively.

## 3. Rejected Directions

### 3.1 Do Not Solve This By Changing The Denominator Only

One tempting shortcut is to rename the target around `active_deck_occupancy` or another smaller denominator and declare success.

Reject this as the main solution because:

- it raises the reported number without necessarily making the actual layout denser
- the teacher can still see loose silhouettes and large empty regions in the figures
- the benchmark would look numerically improved while remaining visually unconvincing

### 3.2 Do Not Introduce Optimizer-Side Family Windows

Another considered direction was to tighten realism by constraining `raw` and `union` search ranges with family-aware spatial windows and zone-restore logic.

Reject this because:

- it adds benchmark-specific optimizer mechanics
- it makes the search problem more hidden-policy-driven
- it complicates repair and controller interpretation
- it reduces the cleanliness of `raw` and `union` as algorithm baselines

### 3.3 Do Not Fork A New `s2` Or Revive `radiation_gen` As Runtime Architecture

Reject creating a new active benchmark template or reviving the old dataset runtime because:

- the repository guidance says `s1_typical` is the active paper-facing mainline
- the right move here is to recalibrate the current benchmark, not to split the experiment story again

## 4. Selected Design

### 4.1 Use Layout-Domain Area Ratio As The Official Density Budget

The official density target for this upgrade should be the current code's `component_area_ratio`, not full-panel absolute fill.

That means the design target becomes:

- `component_area_ratio = 0.44~0.46`

Interpretation:

- numerator: total component footprint area
- denominator: official placement-region area

Why this is the right target:

- it aligns with the original `radiation_gen` `0.4~0.5` definition
- it matches the current mainline metric already computed in `core/generator/layout_metrics.py`
- it separates template density calibration from full-panel absolute occupancy, which is not what the reference project used

This also implies an important implementation consequence:

- under the old fixed template, `component_area_ratio` was nearly constant and therefore not a runtime optimization signal
- after this recalibration, it becomes a template-design target, not an optimizer objective or runtime penalty

### 4.2 Recalibrate The Active `s1_typical` Template Instead Of Adding A New One

Directly retune `scenarios/templates/s1_typical.yaml`.

Recommended geometric strategy:

- increase total component footprint budget by roughly `8%~10%`
- tighten the official placement region by roughly `8%~10%`
- keep the panel size and fifteen-component identity intact

This mixed strategy is preferred over a one-sided change because:

- scaling only components risks making some families visually exaggerated
- shrinking only the denominator risks turning the metric into accounting instead of actual density
- combining both changes better matches how real packed decks evolve

Component-shape guidance:

- preserve the current mixed-shape inventory of `rect`, `slot`, `capsule`, and `circle`
- do not let the recalibration drift back toward a visual field of only similar rectangles
- preferentially enlarge major boards, elongated edge hardware, and a subset of rounded packages so the silhouette remains heterogeneous

Zone guidance:

- keep generation-only zones
- narrow `active_deck`, `dense_core`, and `top_sink_band` moderately
- keep left/right edge lanes recognizable
- do not push those zones into optimizer-side hard movement windows

### 4.3 Keep Runtime Compactness Signals Generic

Do not add `panel_fill_ratio` or `component_area_ratio` as runtime optimizer penalties.

Under the fixed benchmark geometry, those quantities are either constant or almost constant across candidate layouts and therefore do not help the search discriminate between solutions.

Instead, preserve and strengthen only the generic compactness signals that actually vary with placement:

- `bbox_fill_ratio`
- nearest-neighbor gap tendency
- adjacency-group dispersion
- `largest_dense_core_void_ratio`

This keeps the runtime logic generic and benchmark-compatible while still pushing the generator toward more realistic layouts.

### 4.4 Turn `clearance` Into A Real Legality Rule End-To-End

Promote `clearance` from a generation-only hint into the unified legality definition used by:

- generation placement
- generator compactness refinement
- optimizer cheap constraints
- optimizer repair

The legality rule should be:

- `distance(component_i, component_j) >= max(clearance_i, clearance_j)`

Consequences:

- no representative layout should be considered legal if components visually appear glued together
- "compact" should mean "dense subject to assembly gap", not "nearly touching"
- the optimizer still remains free to move components anywhere allowed by the benchmark bounds, but it must respect the same manufacturable gap rule as the generator

Clearance calibration guidance:

- high-power dense modules and long slot-like hardware should keep the largest clearances
- ordinary boards should use moderate clearances
- small round sensor packs may remain slightly tighter
- the overall gap regime should increase modestly, not dramatically

### 4.5 Make All Fifteen Heat Sources Explicitly Structured

All fifteen components already have nonzero `total_power`. Keep that design principle and make it explicit in the template and documentation:

- every component generates waste heat

The missing realism step is to make all fifteen heat-source footprints explicit.

Recommended rule:

- assign `source_area_ratio` to every component family

Suggested family pattern:

- hot modules: smallest `source_area_ratio`
- warm boards: medium `source_area_ratio`
- support, harness, and sensor families: larger `source_area_ratio`

This preserves total power but changes local flux density, which is a much more credible way to raise thermal contrast than arbitrarily spiking total power alone.

### 4.6 Replace The Smooth Linear Power Ladder With Clear Thermal Tiers

Retune the current power ladder into three or four interpretable tiers while keeping all powers nonzero.

Intent:

- clearly separate hot, warm, and cool families
- keep the benchmark answer to "do all components produce waste heat?" as yes
- produce more visible hotspot ordering even when the optimizer tries to flatten the field

The target is not to reproduce the extreme `radiation_gen` spans.

The target is to leave the current too-flat regime and move toward a moderate but clearly visible contrast band that remains believable for the active benchmark.

### 4.7 Add Weak Outer-Boundary Background Cooling Without Changing The Official Sink Model

Keep the official paper-facing single top-edge `line_sink`.

Add a second, weaker cooling mechanism on the full outer panel boundary:

- weak convective exchange to ambient
- weak radiative exchange to ambient

This should be modeled as a background outer-boundary condition, not as additional named sink features.

Why this is the right level of complexity:

- it answers the teacher's concern about ambient background radiation in a physically defensible way
- it avoids introducing multiple benchmark sink features
- it is much cheaper and cleaner than component-to-environment surface-radiation modeling
- it gives the whole plate a plausible leakage path while keeping the top sink as the dominant cold boundary

Recommended contract shape:

- make `ambient_temperature` explicit in `physics`
- add an explicit optional background-boundary cooling block under `physics`
- if the block is absent, keep a backward-compatible zero-strength default

### 4.8 Keep The Physics Upgrade Moderate

Do not attempt:

- component-to-component radiation
- enclosure radiation view-factor models
- transient heating
- optimizer-visible new thermal constraints

This phase should remain a steady conduction problem with:

- localized internal sources
- single strong top sink
- weak global background cooling

That is enough to make the thermal explanation more realistic without destabilizing the solver architecture.

## 5. Detailed Template Targets

### 5.1 Layout Targets

The recalibrated `s1_typical` template should be tuned toward:

- `component_area_ratio = 0.44~0.46`
- `bbox_fill_ratio >= 0.48` on calibration seeds
- visibly smaller interior voids
- no clearance violations in representative layouts

The target should not be stated as:

- full-panel absolute occupancy of `0.45`

because that is not the reference `radiation_gen` definition and would imply a much denser benchmark class than the one actually requested.

### 5.2 Thermal Targets

The recalibrated template should be tuned toward:

- a representative temperature span closer to roughly `8~15 K`
- stronger local hotspots around hot families
- a clear but not pathological cold bias near the top sink
- no visually confusing large cold patch that appears to contradict sink placement

This target band is intentionally moderate:

- much stronger than the current weak-contrast behavior
- much less extreme than the old dataset generator's tens-of-kelvin contrast regime

### 5.3 Reporting Targets

Representative bundles and page views should make the following explicit:

- `component_area_ratio`
- `active_deck_occupancy`
- `bbox_fill_ratio`
- `largest_dense_core_void_ratio`
- minimum or mean nearest-neighbor gap
- explicit ambient/background cooling settings
- explicit note that all fifteen components are waste-heat sources

## 6. Module Impact

Primary files expected to change:

- `scenarios/templates/s1_typical.yaml`
- `core/generator/layout_engine.py`
- `core/generator/layout_metrics.py`
- `core/generator/case_builder.py`
- `core/generator/parameter_sampler.py`
- `core/schema/validation.py`
- `core/solver/case_to_geometry.py`
- `core/solver/physics_builder.py`
- `evaluation/metrics.py`
- `visualization/case_pages.py`
- targeted tests under `tests/generator/`, `tests/solver/`, `tests/evaluation/`, `tests/visualization/`, and `tests/optimizers/`

Secondary documentation expected to change:

- `README.md`
- relevant docs under `docs/`
- possibly `AGENTS.md` only if repository guidance itself changes

## 7. Validation Plan

### 7.1 Layout Validation

Use the standard calibration seeds:

- `11`
- `17`
- `23`
- `29`
- `31`

Acceptance checks:

- all seeds generate without dropped components
- `component_area_ratio` lands in the target band
- `bbox_fill_ratio` improves materially over the current regime
- large empty-core patches are reduced
- no clearance violations survive generation or representative export

### 7.2 Thermal Validation

Acceptance checks:

- all fifteen components are reflected as nonzero heat sources in the interpreted case
- every family has an explicit source localization policy
- the updated thermal span moves into the target band on calibration seeds
- representative thermal pages remain physically interpretable relative to sink position
- ambient/background settings are visible and reproducible from saved case artifacts

### 7.3 Optimizer Validation

Acceptance checks:

- `raw` and `union` remain on the same paper-facing objectives and constraints
- cheap constraints reject clearance-invalid layouts before PDE solve
- repair restores both non-overlap and minimum-gap legality
- representative optimized layouts retain the denser template character without introducing optimizer-side family windows

## 8. Implementation Order

1. Recalibrate the active `s1_typical` template geometry, zones, clearance, powers, and explicit source-area ratios.
2. Extend schema and case-building support for explicit ambient/background boundary cooling settings.
3. Apply unified clearance legality to generator, cheap constraints, and repair.
4. Update solver interpretation and variational form assembly for weak outer-boundary ambient exchange.
5. Refresh evaluation and visualization outputs so the new density and ambient signals are visible in representative bundles.
6. Rebaseline targeted tests and run focused real validation on generation, solve, evaluation, and `raw` / `union` representatives.

## 9. Final Recommendation

Proceed with a direct recalibration of the existing `s1_typical` mainline.

The core tradeoff is intentional:

- keep the optimizer architecture clean
- move realism into the benchmark template, legality definition, and moderate physics calibration

This is the smallest change set that simultaneously addresses:

- the wrong density intuition
- the too-small temperature range
- the unrealistic glued-together optimized layouts
- the missing explicit story for ambient background cooling
- the teacher's question about whether all other components also produce waste heat
