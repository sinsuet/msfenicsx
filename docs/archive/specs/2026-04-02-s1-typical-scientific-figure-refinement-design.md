# S1 Typical Scientific Figure Refinement Design

> Status: proposed follow-on design after the `s1_typical` visualization and logging reset implementation.
>
> This spec refines the new figure stack so exported visuals behave like research figures rather than dashboard cards. It keeps the single-case-first run tree and page architecture, but replaces the current ad hoc SVG composition style with a scientific-figure system built around white backgrounds, explicit axes and legends, field-first layouts, and export-grade semantics.

## 1. Goal

Refine the newly implemented `s1_typical` visualization output so that:

- exported figures look appropriate for scientific reporting and paper preparation
- single-case figures emphasize physical geometry and fields rather than decorative dashboard chrome
- mode and comparison figures show the right metrics with the right chart semantics
- figure filenames and figure contents align
- text never spills outside panels
- the same run bundle can support:
  - interactive HTML reading
  - scientific diagnosis
  - report and paper extraction

This is a refinement of the current new stack, not a rollback to the retired dashboard system.

## 2. Evidence From The Current Implementation

The current implementation already produces deterministic SVG outputs under the new run tree, but visual review of real outputs shows several issues:

- exported figures still use tinted dashboard backgrounds instead of white scientific backgrounds
- fixed-width text panels allow long strings to overflow beyond panel bounds
- several figures mix chart content and explanatory prose inside the same SVG
- comparison filenames imply physical-field comparison while the rendered content only shows hotspot summary statistics
- mode summary figures degenerate for single-seed runs into oversized bars with little analytical value
- progress figures use dense raw polylines without proper tick structure, milestone emphasis, or metric decomposition

These are not isolated style bugs. They arise from the current rendering model itself.

## 3. Root Cause Analysis

The current figure stack is built from a single reusable pattern:

- fixed-size canvas
- hard-coded panel coordinates
- card-style metric boxes
- optional text box panels
- minimal chart primitives with little figure-specific semantics

This creates four systematic problems.

### 3.1 Dashboard Template Leakage

The same visual grammar is being applied to:

- physical layout figures
- sampled field figures
- mode summaries
- cross-mode comparison figures

As a result, figures inherit dashboard conventions such as:

- tinted backgrounds
- rounded card panels
- oversized metric cards
- prose-heavy right-hand note panels

These conventions are acceptable for HTML shells, but not for export-grade scientific figures.

### 3.2 Missing Figure-Type Semantics

The renderer knows how to place rectangles and lines, but not how to express:

- axes
- ticks
- legends
- shared scales
- color bars
- difference-field semantics
- milestone annotations

Therefore many figures currently show data but do not communicate it in the expected scientific form.

### 3.3 No Text Layout Discipline

Current text panels assume:

- fixed width
- fixed line count
- no wrapping
- no clipping
- short content

Real run labels, component bounds, and explanatory lines violate those assumptions immediately.

### 3.4 Page And Figure Responsibilities Are Blended

The current SVG outputs try to function as both:

- figures
- explanatory mini-pages

This causes long notes, geometry listings, and guidance prose to occupy figure real estate that should instead be used by:

- geometry
- fields
- scales
- legends
- chart annotations

## 4. Design Options Considered

Three refinement directions were considered.

### Option A: Patch The Existing SVG Templates

Add wrapping, shrink fonts, switch to white backgrounds, and keep the current figure architecture.

Pros:

- lowest implementation cost

Cons:

- preserves the wrong figure composition model
- does not fix semantic mismatches such as `fields.svg` not being a true field comparison
- continues mixing long prose into figures

Decision: reject.

### Option B: Keep Deterministic SVG Export But Add A Scientific Figure Layer

Keep the current no-heavy-dependency SVG path, but introduce explicit figure families, export rules, and figure-specific layout systems.

Pros:

- compatible with the current HTML integration
- deterministic and repository-controlled
- moderate implementation cost
- sufficient for the current `s1_typical` scientific workflow

Cons:

- requires a nontrivial reorganization of rendering helpers
- still needs careful custom implementation of axes, color bars, and annotation logic

Decision: select this option.

### Option C: Move Most Figures To A Plotting Backend

Use a plotting library for progress and field figures while keeping hand-built SVG only for geometry overlays.

Pros:

- strongest built-in scientific plotting affordances

Cons:

- introduces a second rendering stack
- increases maintenance and integration complexity
- not necessary for the immediate current requirements

Decision: defer for a later phase if Option B proves insufficient.

## 5. Selected Direction

The platform should keep deterministic SVG rendering, but replace the current dashboard-style figure composition with a scientific-figure system.

The key rule is:

- HTML pages may remain richer and more descriptive
- exported figures must be sparse, white, disciplined, and semantically precise

## 6. Figure-System Principles

All new or revised figures must follow these principles.

### 6.1 White-Background Rule

All exported figures under `figures/` must use:

- white figure background
- neutral panel fills only when absolutely necessary
- thin neutral strokes

Decorative tinted dashboard backgrounds should remain page-only and must not appear in export figures.

### 6.2 Figure-First Content Rule

Figures should contain only the content necessary to interpret the visual.

Allowed inside figures:

- title
- legend
- axis labels and ticks
- color bars
- concise annotation labels
- milestone markers

Not allowed inside figures when equivalent page content exists:

- long geometry note lists
- prose explanations
- multi-sentence reading guides
- detailed diagnostic narratives

Those belong in HTML tables or report prose.

### 6.3 Stable Naming Rule

Canonical figure filenames should remain stable where they are already linked from pages, but their content must match the name.

Required meaning:

- `layout.svg`
  - panel geometry and component placement
- `temperature-field.svg`
  - sampled temperature field
- `temperature-contours.svg`
  - contour overlay on the temperature field
- `gradient-field.svg`
  - sampled gradient magnitude field
- `mode-summary.svg`
  - true mode-level metric overview, not a decorative card dashboard
- `progress.svg`
  - true cross-mode progress comparison
- `fields.svg`
  - true cross-mode field comparison

### 6.4 Export-Tier Rule

Each figure family should support consistent export tiers:

- `web`
  - current HTML embedding
- `report`
  - larger white-background export
- `paper`
  - paper-ready aspect ratio and typography

The first refinement phase may still physically write one canonical SVG per figure, but the rendering code should be structured with these tiers in mind.

## 7. Figure Families

The renderer should explicitly treat each figure family differently.

### 7.1 Single-Case Geometry Figures

Purpose:

- show the actual component arrangement
- show sink location and span
- optionally show hotspot marker

Required content:

- panel boundary
- component rectangles
- sink segment
- optional hotspot marker
- compact legend

Removed from the SVG:

- component-by-component bounds list
- explanatory prose

That content should move to HTML tables.

Recommended outputs:

- `layout.svg`
  - clean geometry figure
- optional later:
  - `layout-labeled.svg`
  - `layout-paper.svg`

### 7.2 Single-Case Field Figures

Purpose:

- show the physical field itself
- allow direct cross-case and cross-mode visual comparison

Required content:

- sampled field raster or contour plot
- component outlines
- hotspot marker where relevant
- color bar
- min/max scale annotation
- shared field domain coordinates

Rules:

- the main plot area should dominate the figure
- right-side note panels should not be used
- field summary text should be replaced by color bars and compact annotations
- comparison views must use shared color ranges within each comparison class

### 7.3 Mode Progress Figures

Purpose:

- summarize optimization progress within one mode

Required views:

- best peak temperature vs evaluation index
- best gradient RMS vs evaluation index
- feasible count or feasible rate vs evaluation index
- Pareto size vs evaluation index

Rules:

- single-seed runs should prefer line or step charts, not giant one-bar panels
- milestone markers for first feasible and major Pareto growth should be visible
- overview composition may combine several small scientific panels

### 7.4 Cross-Mode Progress Figures

Purpose:

- compare `raw`, `union`, and `llm` under the same evaluation budget

Required views:

- peak objective progress
- gradient objective progress
- feasible count or feasible rate progress
- Pareto-size progress

Rules:

- the current `progress.svg` should become a true multi-metric comparison overview
- line panels should use sensible tick density
- lines should be milestone-aware rather than dense raw polylines only
- legend and mode color mapping must be explicit and reused consistently

### 7.5 Cross-Mode Field Figures

Purpose:

- compare actual physical fields, not just hotspot summary values

Required first-phase comparison composition:

- aligned representative selection by semantic role
- side-by-side field panels for enabled modes
- shared color bar
- hotspot and contour overlays where meaningful

Optional second-phase extensions:

- difference field such as `union - raw`
- difference field such as `llm - union`
- aligned contour overlays

Rule:

- a figure named `fields.svg` must contain actual field plots
- hotspot `x/y` bar charts may still exist, but under different figure names

### 7.6 LLM And Controller Figures

Purpose:

- make controller value visible, not just controller logs readable

Required future figures:

- operator selection timeline
- first-feasible discovery comparison
- key-decision improvement deltas
- cumulative feasible and Pareto contribution after controller interventions

These are not required for the first refinement pass, but the architecture should reserve a place for them.

## 8. Figure Layout Standards

### 8.1 Typography

Figure typography should switch from decorative serif styling to neutral scientific styling.

Recommended default:

- `Arial, Helvetica, DejaVu Sans, sans-serif`

Rules:

- title weight moderate, not heavy display style
- annotation text smaller and lighter than titles
- numeric emphasis only where analytically important

### 8.2 Margins And Safe Zones

Each figure template should reserve:

- top title band
- main plot band
- legend or color bar band
- optional caption band

Text and marks must remain within safe zones with clipping or truncation safeguards.

### 8.3 Text Overflow Rules

The renderer must support:

- wrapping by available width
- max line count
- ellipsis for overflow
- clip paths inside fixed panels

No text element should extend beyond its parent panel.

### 8.4 Color Use

Use restrained, publication-friendly color systems:

- white background
- dark gray text
- one consistent categorical palette for mode identity
- one perceptually ordered palette for temperature
- one perceptually ordered palette for gradient magnitude

Avoid dashboard-style warm paper tones in exported figures.

### 8.5 Legends And Color Bars

Field figures should use:

- explicit color bar
- labeled min and max
- optional contour-level legend when contours are drawn

Progress figures should use:

- explicit legend when multiple modes appear in one panel

## 9. Page And Figure Responsibility Split

The HTML page should become the place for:

- long tables
- geometry notes
- component thermal tables
- solver diagnostics
- constraint details
- LLM prompt and decision logs

The figure should become the place for:

- geometry
- fields
- trends
- key visual comparisons

This split should be enforced across all new renderers.

## 10. Rendering Architecture Changes

The current helper module should evolve from primitive shape helpers into a scientific-figure helper layer.

### 10.1 New Helper Responsibilities

`visualization/static_assets.py` should grow helpers for:

- figure canvas presets
- scientific typography presets
- text box wrapping and clipping
- axes and tick generation
- color bars
- legends
- milestone markers
- shared-scale panel layouts

### 10.2 Figure Builders

`visualization/case_pages.py` should split into dedicated builders for:

- geometry figure
- field figure
- contour figure

`visualization/mode_pages.py` should build:

- mode overview figure
- metric-specific progress subfigures or panels

`visualization/comparison_pages.py` should build:

- multi-metric progress overview
- actual field comparison figure
- optional auxiliary hotspot statistics figure later under a distinct name

### 10.3 Figure Metadata

Each figure should optionally record summary-side metadata such as:

- figure type
- representative alignment role
- color scale source
- value range
- metric family

This will help later report automation and reproducibility.

## 11. Migration Strategy

The refinement should be applied in four steps.

### Step 1: Scientific Figure Foundation

Implement:

- white-background figure preset
- typography reset
- text wrapping and clipping
- axis and legend helpers
- color bar helpers

### Step 2: Single-Case Figure Cleanup

Refactor:

- `layout.svg`
- `temperature-field.svg`
- `temperature-contours.svg`
- `gradient-field.svg`

Move geometry notes and prose fully out of the SVGs.

### Step 3: Comparison Figure Semantic Fix

Refactor:

- `progress.svg`
- `fields.svg`

Ensure:

- `progress.svg` becomes a real multi-metric progress figure
- `fields.svg` becomes a real field-comparison figure

### Step 4: Mode And LLM Follow-Through

Refactor:

- `mode-summary.svg`
- future controller and LLM evidence figures

## 12. Acceptance Criteria

The refinement is complete only when all of the following are true.

- all exported figures under `figures/` have white backgrounds
- no text overflows any panel
- geometry figures no longer contain long geometry-note prose
- field figures include color scale information
- `fields.svg` contains actual field-comparison content
- `progress.svg` contains real progress-comparison content across required metrics
- single-seed mode figures no longer rely on giant single bars as their main analytical expression
- figure names match figure contents
- SVG exports remain deterministic
- PNG export can be added without redesigning figure composition again

## 13. Non-Goals For This Refinement

The following are explicitly out of scope for this phase:

- changing the run tree again
- rolling back the single-case-first page model
- moving the whole stack to a plotting library immediately
- redesigning LLM report content structure beyond what is needed for figure integration

## 14. Final Direction

The correct next step is not to keep patching the current dashboard-like SVGs.

The correct next step is to build a scientific figure system on top of the new `s1_typical` visualization stack so that:

- single-case pages remain the main entrypoint
- figures become publication-grade
- pages keep the detailed explanatory burden
- comparison outputs finally show actual physical-field and progress evidence rather than placeholders or surrogate summaries
