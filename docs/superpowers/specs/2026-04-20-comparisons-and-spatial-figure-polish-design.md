# Comparisons & Spatial Figure Polish — Design

- **Date**: 2026-04-20
- **Scope**: extend the logging/visualization refactor with automatic suite-owned `comparisons/` outputs, richer cross-mode comparison artifacts, objective trace figures, and a publication-grade spatial-panel contract.
- **Applies to**: `optimizers/run_suite.py`, `optimizers/compare_runs.py`, `optimizers/render_assets.py`, `optimizers/run_telemetry.py`, `visualization/figures/`, `README.md`, `AGENTS.md`.
- **Depends on**: [docs/superpowers/specs/2026-04-16-logging-visualization-refactor-design.md](2026-04-16-logging-visualization-refactor-design.md)

## 1. Motivation

The current post-refactor output is materially cleaner than the legacy stack, but six paper-facing gaps remain:

1. **Cross-mode compare is still manual.** `compare-runs` can only compare explicit concrete run roots, so a suite run still requires a second manual step before the final result is inspectable.
2. **Compare output is too thin.** Current compare output covers Pareto, hypervolume, and best-so-far progress only. It does not answer the practical questions users ask first: which mode finds feasible points earlier, which mode improves faster per PDE solve, and how objectives behave before the best-so-far envelope updates.
3. **Progress figures hide current objective values.** The run-level `objective_progress` figure only shows `best_*_so_far`; it does not expose the per-evaluation `current temperature` / `current gradient` trajectory that is needed to understand search stability and wasted solve budget.
4. **Layout panels still look like engineering diagnostics rather than paper figures.** Capsule-component labels can spill outside the body, sink windows read like hairlines on the boundary, and the figure face does not explain what the colors mean or which algorithm / mode / model produced the result.
5. **Field figures still lack stable publication composition.** Temperature and gradient tiles may ship without explicit titles, and colorbar spacing is still delegated to matplotlib auto-layout rather than a locked panel composition.
6. **Multi-seed compare semantics are under-explained.** `by_seed/` and `aggregate/` are both useful, but the current contract does not clearly separate “same problem instance across modes” from “across-seed rollup”.

This spec closes those gaps without reintroducing the deleted legacy `comparison/` page stack.

## 2. Non-Goals

- Reintroducing legacy suite-owned `comparison/` roots, HTML page stacks, or old `mode_pages` / `comparison_pages` flows.
- Supporting historical mixed old/new runs.
- Reintroducing noisy “many tiny charts by default” compare bundles. The goal is fewer, denser, more legible artifacts.
- Changing the physical panel geometry contract. The board remains a real `1.0 x 0.8` domain; the change is visual presentation, not data semantics.

## 3. Automatic `comparisons/` Contract

### 3.1 Naming and ownership

Automatic compare output is allowed again, but under a new contract:

- The directory name is **`comparisons/`**, never legacy `comparison/`.
- It is owned only by a **suite root** produced by `run-benchmark-suite`.
- Standalone `optimize-benchmark` runs remain single-run bundles with no auto-generated compare subtree.
- The external CLI `compare-runs` remains available for ad hoc comparisons and writes anywhere the caller requests.

### 3.2 When to auto-generate

`run-benchmark-suite` must auto-generate suite comparisons when and only when:

- at least **two modes** are selected, and
- each selected mode produced at least one concrete seed bundle.

If the suite contains only one mode, no `comparisons/` subtree is created.

### 3.3 Directory layout

#### Single-seed suite

When the suite contains exactly one benchmark seed:

```text
scenario_runs/<template>/<run_id>/
└── comparisons/
    ├── manifest.json
    ├── analytics/
    ├── figures/
    │   └── pdf/
    └── tables/
```

`comparisons/` itself is the final compare bundle.

#### Multi-seed suite

When the suite contains two or more benchmark seeds:

```text
scenario_runs/<template>/<run_id>/
└── comparisons/
    ├── manifest.json
    ├── by_seed/
    │   ├── seed-11/
    │   │   ├── analytics/
    │   │   ├── figures/
    │   │   │   └── pdf/
    │   │   └── tables/
    │   └── seed-17/
    └── aggregate/
        ├── analytics/
        ├── figures/
        │   └── pdf/
        └── tables/
```

Rules:

- `by_seed/seed-<n>/` compares the same benchmark seed across modes.
- `aggregate/` is the across-seeds rollup layer for the same set of compared modes.
- No compare artifact is written back into any source mode seed root.

Semantic rule:

- `by_seed/` answers “for this exact benchmark instance, how do raw / union / llm differ?”
- `aggregate/` answers “across all included seeds, what is the descriptive summary of those mode differences?”
- `aggregate/` exists for any suite with `N>=2` compared benchmark seeds.
- inferential-statistics language is only allowed when the bundle contains `N>=3` seeds; for `N=2`, aggregate remains descriptive only.

### 3.4 Manifest

`comparisons/manifest.json` must capture:

- `suite_root`
- `mode_ids`
- `benchmark_seeds`
- `comparison_kind`: `single_seed` or `multi_seed`
- `by_seed_paths`
- `aggregate_path` (multi-seed only)
- `created_at`

## 4. Compare Artifact Contract

### 4.1 Per-seed compare bundle

Each per-seed compare bundle must write:

#### `figures/`

- `summary_overview.png`
- `final_layout_comparison.png`
- `temperature_field_comparison.png`
- `gradient_field_comparison.png`
- `progress_dashboard.png`
- optional low-level charts such as `pareto_overlay.png`, `hypervolume_comparison.png`, or `objective_progress_comparison.png` only when they carry non-trivial information
- PDF companions under `figures/pdf/`

#### `tables/`

- `summary_table.csv/.tex`
- `mode_metrics.csv/.tex`
- `pairwise_deltas.csv/.tex`

#### `analytics/`

- `summary_rows.json`
- `timeline_rollups.json`

Semantics:

- `summary_overview` is the first-stop artifact: a single publication-style summary table rendered as a figure preview. It includes `mode`, `algorithm`, `model` (llm only), `front_size`, `pde_evaluations`, `solver_skipped_evaluations`, `first_feasible_pde_eval`, `best_temperature_max`, `best_gradient_rms`, `feasible_rate`, `hypervolume`, and the representative id used for visual tiles.
- `final_layout_comparison` is the primary visual compare tile. It renders one selected representative per mode using the same spatial-panel contract as run-level figures. Two-mode compares render two columns; three-mode compares render three columns.
- `temperature_field_comparison` and `gradient_field_comparison` render the corresponding physical-field mosaics for the same representative choice used by `final_layout_comparison`.
- `progress_dashboard` consolidates the high-value progress information into one artifact: current-vs-best temperature trace, current-vs-best gradient trace, hypervolume over generations, and feasible-rate / constraint-violation evolution. The compare bundle should not default to one-file-per-metric if those panels can live together cleanly.
- Optional low-level charts are allowed only when they convey additional structure that is not already obvious from the overview or dashboard. Low-information singleton plots should be suppressed rather than emitted mechanically.

Representative-selection rule:

- The per-seed compare builder must choose one deterministic “paper default” representative per mode for visual mosaics.
- Preferred order: `knee`, then `min-temperature-max`, then `min-temperature-gradient-rms`.
- This is a new-chain-only selection policy, not a legacy fallback mechanism.

### 4.2 Aggregate compare bundle

The multi-seed `aggregate/` bundle must write:

#### `figures/`

- `summary_overview.png`
- `hypervolume_iqr_comparison.png`
- `temperature_trace_median_band.png`
- `gradient_trace_median_band.png`
- `seed_outcome_dashboard.png`
- PDF companions under `figures/pdf/`

#### `tables/`

- `per_seed_metrics.csv/.tex`
- `aggregate_mode_summary.csv/.tex`
- `pairwise_win_rate.csv/.tex`

#### `analytics/`

- `aggregate_mode_summary.json`
- `pairwise_win_rate.json`
- `seed_metric_rows.json`

Semantics:

- Aggregate trace figures must use **median + interquartile band** per mode, not raw spaghetti plots.
- Aggregate tables must be seed-aligned: every row is keyed by `(benchmark_seed, mode_id)`.
- `summary_overview` must clearly state `Across <N> seeds`.
- `seed_outcome_dashboard` is the descriptive across-seeds overview. It should privilege paired, seed-aligned comparisons over anonymous boxplot spam.
- If `N=2`, aggregate output remains descriptive and must avoid wording that implies statistical significance.
- If `N>=3`, the builder may additionally emit stronger cross-seed summaries such as win rates or inferential statistics, but those are secondary to the descriptive dashboard.

### 4.3 LLM-only compare add-ons

If and only if one of the compared modes is `llm`, the compare builder may additionally write:

- `figures/llm_operator_mix.png`
- `figures/llm_latency_tokens.png`
- `tables/llm_decision_overview.csv/.tex`

These artifacts must be skipped, not stubbed, when no `llm` run participates.

## 5. Progress Telemetry Extension

### 5.1 New timeline fields

`build_progress_timeline(...)` must be extended so each row may carry:

- `current_temperature_max`
- `current_gradient_rms`
- `current_total_constraint_violation`
- `status`
- `solver_skipped`
- `pde_attempted`
- `pde_evaluation_index`
- `first_feasible_pde_eval_so_far`

Existing fields remain:

- `evaluation_index`
- `best_temperature_max_so_far`
- `best_gradient_rms_so_far`
- `best_total_constraint_violation_so_far`
- `first_feasible_eval_so_far`
- `feasible_count_so_far`
- `feasible_rate_so_far`
- `pareto_size_so_far`

Rules:

- `current_*` values come from the exact evaluation row being processed, even when infeasible.
- Failed evaluations must not inject gigantic sentinel values into plotted axes. Failures are represented through `status`, not by plotting `1e12`.
- `best_*_so_far` only updates on feasible rows, as today.
- `evaluation_index` stays as the optimizer sequence for correlation with controller / operator / LLM traces.
- Paper-facing axes labeled `PDE evaluations` must use `pde_evaluation_index`, defined as the cumulative count of non-baseline rows with `solver_skipped == false`.
- `first_feasible_pde_eval_so_far` is the PDE-attempt count at which feasibility is first reached; it is the paper-facing counterpart to optimizer-sequence `first_feasible_eval_so_far`.

### 5.2 New run-level figures

Each concrete run bundle rendered by `render-assets` must additionally write:

- `figures/temperature_trace.png`
- `figures/gradient_trace.png`
- `figures/constraint_violation_progress.png`

Semantics:

- `temperature_trace`: current `temperature_max` plus best-so-far `temperature_max`
- `gradient_trace`: current `temperature_gradient_rms` plus best-so-far `temperature_gradient_rms`
- `constraint_violation_progress`: current total violation plus best-so-far total violation
- failures and infeasible evaluations are kept visible via point style / event markers instead of destructive clipping

## 6. Spatial Figure Contract

This section applies to:

- `layout_initial`
- `layout_final`
- layout evolution frames
- `temperature_field_<representative>`
- `gradient_field_<representative>`

### 6.1 Geometry presentation

Spatial figures must:

- preserve the real panel aspect ratio
- show the board boundary
- omit `x` / `y` axis labels
- omit numeric coordinate ticks
- keep the title above the panel

The figures are still geometrically faithful to the `1.0 x 0.8` panel; the axes are hidden because they add noise without adding decision value at this stage.

### 6.2 Component labels

All spatial figures must show component labels using short paper tokens:

- `C01`
- `C02`
- ...
- `C15`

Rules:

- labels are derived deterministically from component ordering / canonical component ids
- the same component uses the same label token on every figure
- full raw ids such as `c01-001` stay in structured data and tables, not on the figure face

### 6.3 Layout panel contract

Layout figures are not bare board snapshots anymore. They are publication panels with:

- a left main board tile
- a right metadata strip
- a concise title above the figure

The right metadata strip should carry the minimum context needed to understand the artifact without opening YAML:

- scenario id
- algorithm family, reported as `NSGA-II`
- mode id (`raw`, `union`, or `llm`)
- llm model id when mode is `llm`
- benchmark seed
- representative id / label
- best `Tmax` and best gradient metrics when available

Label rules for pure layout figures:

- labels must stay inside the component body; external callouts are not allowed
- capsule-like components should place the token along the long axis rather than ejecting the token outside the shape
- labels should use a light neutral chip with dark text unless the component fill itself already provides enough contrast

Color rules:

- optimizer layout figures must not imply semantic category information unless a legend explicitly defines it
- the default layout treatment is a restrained, low-saturation component fill plus dark outline
- if future work introduces category colors, the meaning must be stated in the metadata strip or an explicit legend

### 6.3.1 Layout evolution semantics

`layout_evolution` is a paper-facing **milestone replay**, not a literal per-generation storyboard.

Rules:

- start from the baseline / initial layout
- follow the best-so-far trajectory induced by the display ranking already used for representative selection
- keep the first feasible milestone when one exists
- keep later milestones only when component placement changes materially, so sink-only micro-adjustments do not dominate the story
- always keep the final best-so-far layout
- preserve individual frames as `layout_evolution_frames/step_<NNN>.png`, not `gen_<NNN>.png`

This figure is therefore allowed to skip generations and evaluations that do not materially change the spatial arrangement.

### 6.4 Field panel contract

For temperature and gradient fields:

- titles are mandatory and sit above the panel
- component outlines remain visible above the field
- component labels must remain readable on both dark and bright regions
- the colorbar column must use a fixed composition so that the board tile and colorbar remain visually aligned
- sink windows must use the same explicit visual language as layout panels rather than a barely visible border line

Field labels therefore use a **single white paper chip**:

- fill `#FFFDF8`
- text `#111111`
- border `#2A2A2A`
- opacity in the `0.94-0.96` range is allowed

Additional rules:

- rounded rectangle chip
- thin border
- subtle opacity allowed
- a light text stroke / halo is allowed as a second readability guard, but the chip itself stays white
- prefer internal placement; only move a label away from the centroid when the local field contrast makes the internal placement unreadable

### 6.5 Outline and sink styling

Stable figure styling:

- board border: `#1A1A1A`
- layout-figure component outline: `#2A2A2A`
- field-figure component outline: `#F7F7F4`
- sink highlight: `#00A9B7`
- sink border accent: `#0D3B40`

Sink rendering rule:

- sinks must be rendered as an inset ribbon or bar inside the panel boundary, not as a hairline coincident with the board edge
- the sink mark should carry a small `SINK` label or equally explicit textual cue when space allows

These values are chosen to remain readable against both restrained layout fills and the `inferno` / `viridis` field maps.

## 7. Figure Titles

Spatial figure titles should be short, noun-based, and publication-friendly. Preferred examples:

- `Initial Layout`
- `Final Layout`
- `Temperature Field · Knee`
- `Temperature Field · Min Peak`
- `Gradient Field · Min Gradient`
- `Temperature Trace`
- `Gradient Trace`

Titles should not repeat internal file naming noise such as `seed-11` unless the figure is explicitly part of a compare bundle where the seed boundary matters. Compare bundles should prefer `Seed 11` or `Across 3 Seeds` over filesystem-style tokens.

## 8. Implementation Notes

### 8.1 Compare builder decomposition

The compare implementation should be decomposed into:

- a **seed-level compare builder** that consumes concrete run roots
- a **suite-level compare orchestrator** that maps suite roots to per-seed comparisons and aggregate statistics

This preserves the ad hoc `compare-runs` CLI while letting `run-benchmark-suite` auto-generate `comparisons/`.

### 8.2 Backward compatibility stance

This spec follows the pure new-chain policy:

- no compatibility for mixed old/new suites
- no suite-root `comparison/`
- no restoration of old HTML pages
- no reintroduction of per-representative pages or summaries

## 9. Testing Requirements

Focused tests must cover:

1. suite auto-generation of `comparisons/` for single-seed and multi-seed mode suites
2. absence of `comparisons/` when only one mode is selected
3. per-seed compare contents and aggregate compare contents
4. new timeline fields for current objective / violation values
5. trace figures ignoring failure sentinels while keeping failure events visible
6. layout figures keeping capsule labels inside the component body
7. layout figures rendering an explicit sink ribbon instead of a barely visible border line
8. spatial figures omitting axes and ticks
9. spatial figures rendering component labels
10. layout panels carrying the right-side metadata strip
11. field labels using the same white chip on both dark and bright backgrounds without losing readability
12. compare bundles emitting `summary_overview`, mode-mosaic field/layout panels, and a consolidated progress dashboard
13. aggregate bundles describing themselves as across-seeds rollups and remaining descriptive for `N=2`

## 10. Success Criteria

This extension is complete when:

- a multi-mode suite automatically leaves behind a usable `comparisons/` subtree
- users can inspect both per-seed and aggregate comparison output without rerunning CLI tools manually
- per-seed compare bundles lead with one summary figure, one layout mosaic, two field mosaics, and one progress dashboard rather than a scatter of low-information singleton charts
- run-level figures include current-vs-best traces for temperature and gradient objectives
- layout and field figures are clean, axis-free, consistently labeled with `C01..C15`, and make sink placement visually explicit
- field labels remain readable across both dark and bright colormap regions while keeping a single white-chip visual language
