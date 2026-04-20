# Logging & Visualization Refactor — Design

- **Date**: 2026-04-16
- **Scope**: single unified design covering run layout, trace schema, analytics, visualization style, figure factory, CLI, testing, and environment prep.
- **Applies to**: `optimizers/` drivers (raw/union/llm), `optimizers/operator_pool/` controller, `optimizers/artifacts.py`, `optimizers/run_telemetry.py`, `visualization/`, `optimizers/cli.py`.
- **Does not apply to**: `scenarios/templates/s1_typical.yaml` (the active benchmark template is NOT modified by this spec; multi-seed template changes are deferred to a follow-up spec — see § 3.4, Option B).

## 1. Motivation

Current run outputs have four concrete problems driving this refactor:

1. **Inverted heat colorbar.** `visualization/figure_axes.py:44` builds the colorbar bottom-up with `bar_y + float(steps - 1 - index) * step_height`, so the visual gradient is reversed while tick labels still say max-on-top. Every temperature/gradient SVG rendered via `case_pages.py` carries this bug.
2. **Messy LLM line logs.** `optimizers/operator_pool/llm_controller.py` writes raw prompt strings inline into `llm_request_trace.jsonl`, producing multi-KB lines that are unusable for diff/analysis. Prompts and responses are not cross-linkable to a decision.
3. **Non-publication-grade figures.** Hand-rolled SVG via `visualization/static_assets.py` (`svg_rect`, `svg_polyline`, etc.) cannot hit IEEE/Elsevier submission conventions: no vector-clean matplotlib output, no Okabe-Ito colorblind palette, no 600+dpi rasters, no controlled axes/legend typography.
4. **Deep, noisy directory layout.** Current representative paths reach six levels (e.g. `.../representatives/knee-candidate/figures/gradient-field.svg`), with empty `logs/` folders and 10+ mixed files at run root. Users browsing a run must dig through irrelevant scaffolding.

The refactor treats raw / union / llm uniformly — they share the same analytics, the same figures, the same directory layout. Missing LLM-only artifacts (e.g., controller traces) are simply null in raw/union.

## 2. Non-Goals

- Modifying `scenarios/templates/s1_typical.yaml` itself (design variables, bounds, operating case). Multi-seed problem generation is deferred to a separate spec.
- Extending the algorithm layer (no new operators, no NSGA-II variants).
- Dual-writing old + new schema for backward compatibility. Old runs under `scenario_runs/s1_typical/<timestamp>__<mode>/` are one-shot; not migrated.
- Writing the paper itself. This spec ships assets (figures, tables, animations); prose is authored manually.

## 3. Run Directory Layout

### 3.1 Single-seed (current default, N=1)

```
scenario_runs/s1_typical/<MMDD_HHMM>__<mode>/
├── run.yaml                    # canonical run manifest (spec paths, seeds, timing)
├── results.yaml                # Pareto set + per-individual metadata
├── traces/                     # JSONL only; see § 4
│   ├── evaluation_events.jsonl
│   ├── generation_summary.jsonl
│   ├── operator_trace.jsonl
│   ├── controller_trace.jsonl      # llm only; absent for raw/union
│   ├── llm_request_trace.jsonl     # llm only
│   └── llm_response_trace.jsonl    # llm only
├── prompts/                    # llm only; content-addressed markdown; see § 4.3
│   └── <sha1>.md
├── analytics/                  # computed from traces; see § 5
│   ├── pareto.parquet
│   ├── hypervolume.csv
│   ├── decision_outcomes.csv
│   ├── phase_alignment.csv         # llm only
│   ├── cost_per_improvement.csv    # llm only
│   ├── guardrail_timeline.csv      # llm only
│   └── operator_phase_heatmap.csv
├── figures/                    # raster figures for browsing; vector companions live under figures/pdf/
│   ├── pareto_front.png
│   ├── hypervolume_progress.png
│   ├── objective_progress.png
│   ├── temperature_trace.png
│   ├── gradient_trace.png
│   ├── constraint_violation_progress.png
│   ├── operator_phase_heatmap.png
│   ├── temperature_field_<repr>.png
│   ├── gradient_field_<repr>.png
│   ├── layout_evolution.gif        # animated layout progression
│   └── pdf/
│       ├── pareto_front.pdf
│       ├── hypervolume_progress.pdf
│       ├── objective_progress.pdf
│       ├── temperature_trace.pdf
│       ├── gradient_trace.pdf
│       ├── constraint_violation_progress.pdf
│       ├── operator_phase_heatmap.pdf
│       ├── temperature_field_<repr>.pdf
│       └── gradient_field_<repr>.pdf
├── tables/                     # CSV + LaTeX booktabs
│   ├── summary_statistics.csv / .tex
│   └── representative_points.csv / .tex
└── representatives/            # flat: 2-level max, not 6
    └── <representative_id>/
        ├── case.yaml
        ├── solution.yaml
        ├── evaluation.yaml
        └── fields/
            ├── temperature_grid.npz
            └── gradient_magnitude_grid.npz
```

Changes from current layout:

- Empty `logs/` folders removed.
- Representative depth reduced from 6 levels to 3 (`representatives/<id>/fields/*.npz`).
- Figures and SVGs no longer live inside per-representative dirs; rendered centrally in `figures/` and named by representative id.
- All traces move into `traces/` subfolder; all `.json` converted to `.jsonl` (one record per line) for streaming + diff-friendliness.
- No `comparison/` sibling inside a single run — each run is single-mode. Cross-mode comparison is a separate CLI operation (§ 8.2).

### 3.2 Multi-seed (N>=2)

When `--benchmark-seed` is passed multiple times (or algorithm seed varies), the layout wraps per-seed dirs:

```
scenario_runs/s1_typical/<MMDD_HHMM>__<mode>/
├── seeds/
│   ├── seed-7/
│   │   ├── run.yaml, results.yaml, traces/, analytics/, figures/, representatives/
│   └── seed-11/
│       └── ...
└── aggregate/                  # descriptive across-seeds rollup; see § 5.4
    ├── hypervolume_iqr.csv
    ├── hypervolume_iqr.png
    ├── attainment_surface.png
    ├── pdf/
    │   ├── hypervolume_iqr.pdf
    │   └── attainment_surface.pdf
    └── mann_whitney.csv
```

Flat vs wrapped is a pure directory-level switch — same file names inside. Later extensions may write an `aggregate/` descriptive rollup for `N>=2`; inferential-statistics claims remain meaningful only with >=3 seeds.

### 3.3 Cross-mode comparison (`compare-runs`) and suite-owned `comparisons/`

Standalone `compare-runs` accepts only concrete single-mode run roots and must write an external bundle outside all source runs:

```
scenario_runs/compare_reports/<compare_id>/
├── manifest.json
├── analytics/
│   ├── summary_rows.json
│   └── timeline_rollups.json
├── figures/
│   ├── pareto_overlay.png
│   ├── hypervolume_comparison.png
│   ├── objective_progress_comparison.png
│   ├── temperature_trace_comparison.png
│   ├── gradient_trace_comparison.png
│   ├── constraint_violation_comparison.png
│   ├── feasible_progress_comparison.png
│   └── pdf/
└── tables/
    ├── summary_table.csv / .tex
    ├── mode_metrics.csv / .tex
    └── pairwise_deltas.csv / .tex
```

When `run-benchmark-suite` finishes a suite with two or more participating modes, it additionally auto-writes a suite-owned `comparisons/` subtree:

- single-seed suite: `<suite_root>/comparisons/`
- multi-seed suite: `<suite_root>/comparisons/by_seed/seed-<n>/` plus `<suite_root>/comparisons/aggregate/`

Neither path revives legacy `comparison/`, and neither path writes comparison artifacts back into source mode seed roots.

### 3.4 Multi-seed template changes — DEFERRED (Option B chosen)

The active `scenarios/templates/s1_typical.yaml` generates a fixed single case. Multi-seed design for paper-grade MOEA statistics (30+ seeds, Mann-Whitney, attainment surface) requires disentangling:

- **benchmark_seed** — controls problem instance generation (component layout, boundary profile).
- **algorithm_seed** — controls NSGA-II search RNG (initial population, mutation draws).

The current template fuses both under a single `benchmark_source.seed`. Cleaning this up requires template schema changes, solver cache invalidation plans, and driver refactors that are out of scope for this logging/visualization refactor. **Deferred to a separate spec.** This refactor supports the multi-seed *layout* (§ 3.2) and *aggregation analytics* (§ 5.4) so that when the template is updated later, no visualization or CLI work is required.

## 4. Trace Schema

All traces are JSONL (UTF-8, no BOM). Correlation across traces uses a single `decision_id` field with format `g{gen:03d}-e{eval:04d}-d{dec:02d}` (e.g. `g005-e0042-d01`). Every record that describes one LLM decision or one evaluation carries this id.

### 4.1 evaluation_events.jsonl

One record per non-baseline optimizer evaluation. Fields:

- `decision_id` (may be null for seed population)
- `generation` (int)
- `eval_index` (int, monotonic across the non-baseline run; this is the optimizer evaluation sequence, not the paper-facing PDE budget)
- `individual_id` (str)
- `objectives`: `{ temperature_max, temperature_gradient_rms }`
- `constraints`: `{ total_radiator_span, radiator_span_max, violation }`
- `status`: one of `ok`, `infeasible`, `failed`
- `solver_skipped` (bool; `true` means cheap constraints rejected the candidate before any PDE solve was attempted)
- `timing`: `{ cheap_ms, solve_ms }`

Paper-facing `PDE evaluations` are derived downstream as the cumulative count of rows with `solver_skipped == false`. This keeps cheap-reject evidence visible in the trace while preventing figures and compare tables from overstating expensive solver usage.

### 4.2 generation_summary.jsonl

One record per generation. Fields:

- `generation`
- `population_size`, `num_feasible`, `num_infeasible`
- `front_objectives`: list of Pareto-front objective tuples
- `hypervolume` (2D HV against reference point)
- `operator_usage`: `{operator_name: count}`
- `controller_phase` (llm only, e.g. `prefeasible`, `post_feasible_recover`, etc.)

### 4.3 operator_trace.jsonl (all modes)

One record per operator application (emitted by every driver — raw/union/llm):

- `decision_id` (null for raw/union — no controller decision; kept for schema uniformity)
- `generation`
- `operator_name`
- `parents`: list of individual ids
- `offspring`: list of individual ids
- `params_digest`: sha1 of operator parameters for reproducibility
- `wall_ms`

This is what lets raw/union share the § 5.2 operator-usage analytics uniformly with llm.

### 4.4 controller_trace.jsonl (llm only)

One record per controller decision:

- `decision_id`
- `phase`
- `operator_selected`
- `operator_pool_snapshot`
- `input_state_digest` (sha1 of domain state presented to LLM)
- `prompt_ref`: `prompts/<sha1>.md` (relative path; see § 4.6)
- `rationale` (LLM-emitted explanation)
- `fallback_used` (bool; true if controller fell back to random_uniform)
- `latency_ms`

### 4.5 llm_request_trace.jsonl / llm_response_trace.jsonl (llm only)

One record per HTTP round-trip:

- `decision_id`
- `prompt_ref` (request side)
- `response_ref`: `prompts/<sha1>.md` (response side, if we store response bodies; see § 4.6)
- `model`
- `tokens`: `{ prompt, completion, total }`
- `finish_reason`
- `http_status`, `retries`, `latency_ms`

No raw prompt text inside `.jsonl`. This fixes the current "messy LLM log" problem — trace lines stay narrow (<1KB) and grep-friendly; full text lives in de-duplicated markdown files.

### 4.6 prompts/ — content-addressed markdown

Each unique prompt body and each unique response body is written once to `prompts/<sha1>.md`. Format:

```markdown
---
kind: request | response
sha1: abc123...
model: gpt-5.4
decision_ids: [g005-e0042-d01, g005-e0048-d01]
first_seen_at: 2026-04-16T08:21:03Z
---

# System

...

# User

...
```

Benefits: prompt bodies deduplicated across calls that share the same text (very common in our controller); reviewers can diff by file; machine-readable frontmatter enables analytics (e.g., "which prompt template correlated with most improvement").

## 5. Analytics Layer

A new package `optimizers/analytics/` computes all derived data from raw traces. Driver code does NOT compute these; drivers only emit traces. Analytics is a pure function of traces → artifacts.

### 5.1 Module layout

```
optimizers/analytics/
├── __init__.py
├── loaders.py              # streams JSONL → typed records
├── pareto.py               # Pareto filtering, HV
├── correlate.py            # joins traces by decision_id
├── rollups.py              # per-generation summaries
├── decisions.py            # decision_outcomes, phase_alignment, cost_per_improvement (llm only)
├── guardrails.py           # guardrail_timeline (llm only)
├── heatmap.py              # operator × phase usage grid
└── aggregate/              # multi-seed (§ 5.4)
    ├── iqr.py
    ├── attainment.py
    └── stats.py            # Mann-Whitney, Wilcoxon
```

### 5.2 Computed artifacts (all runs)

- **`pareto.parquet`** — Pareto set with objectives, constraint slack, representative flag. Parquet (not CSV) because it holds vector columns efficiently.
- **`hypervolume.csv`** — `(generation, hypervolume)` plus reference point metadata.
- **`operator_phase_heatmap.csv`** — rows: operators; cols: phases (for raw/union there is a single `n/a` column, so the heatmap is degenerate but still rendered for uniformity).

### 5.3 Computed artifacts (llm only)

- **`decision_outcomes.csv`** — per controller decision: was it applied, did offspring improve HV, by how much.
- **`phase_alignment.csv`** — agreement rate between controller-declared phase and post-hoc labeled phase (based on feasibility ratio thresholds).
- **`cost_per_improvement.csv`** — (tokens / HV gain) per decision; low is good.
- **`guardrail_timeline.csv`** — timeline of fallback activations, operator-pool-shrink events, JSON-parse failures.

### 5.4 Multi-seed aggregation

- **`hypervolume_iqr.csv`** — per-generation median + 25/75 percentiles across seeds.
- **`attainment_surface`** — 50% / 75% / 90% attainment surfaces in objective space.
- **`mann_whitney.csv`** — pairwise mode comparisons (raw-vs-union, union-vs-llm, raw-vs-llm) with U statistic, p-value, effect size.

Descriptive across-seeds rollups can exist for `N>=2`, but inferential-statistics language should be reserved for `N>=3`. This prevents misleading two-seed “statistics” while still allowing useful paired summaries for small local runs.

## 6. Visualization Style Baseline

A new package `visualization/style/` replaces `figure_theme.py`, `static_assets.py`, `figure_axes.py`, and `case_pages.py`.

### 6.1 rcParams baseline (`visualization/style/baseline.py`)

```python
FONT_FAMILY = ["DejaVu Serif", "Noto Serif CJK SC", "serif"]   # WSL-portable, includes CJK
FONT_FAMILY_MATH = "stix"
BASE_FONT_SIZE = 9    # IEEE/Elsevier double-column baseline
DPI_DEFAULT = 600
DPI_HIRES = 1200
DPI_FIELD_HIRES = 2400   # field plots only (pcolormesh shading='gouraud')
COLORMAP_TEMPERATURE = "inferno"
COLORMAP_GRADIENT = "viridis"
PALETTE_CATEGORICAL = [   # Okabe-Ito colorblind-safe
    "#000000", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
]
```

rcParams applied: `font.family`, `font.size`, `mathtext.fontset`, `axes.linewidth=0.6`, `axes.labelsize`, `xtick.direction="in"`, `ytick.direction="in"`, `legend.frameon=False`, `figure.constrained_layout.use=True`.

### 6.2 Figure sizes

- Single-column: 3.5" × ~2.6"
- Double-column: 7.0" × ~3.2"
- Field plots (square aspect): 3.5" × 3.5" or 7.0" × 7.0"

### 6.3 DPI policy

- PDFs: vector, DPI irrelevant.
- PNGs: 600 DPI default. `--hires` CLI flag bumps non-field plots to `DPI_HIRES` (1200) and field plots (temperature/gradient) to `DPI_FIELD_HIRES` (2400) with `pcolormesh(shading='gouraud')` for smooth continuous color.

## 7. Figure Factory

A new package `visualization/figures/` with one module per figure kind. Each module exposes `render(inputs: AnalyticsBundle, output_dir: Path, hires: bool=False) -> None`.

### 7.1 Modules

```
visualization/figures/
├── __init__.py
├── pareto.py                   # pareto_front + overlay variants
├── hypervolume.py              # single-run + multi-seed IQR band
├── temperature_field.py        # pcolormesh + contour + colorbar (CORRECT orientation)
├── gradient_field.py
├── layout_evolution.py         # animated GIF + frame PNGs preserved
├── operator_heatmap.py
└── guardrail_timeline.py       # llm only
```

### 7.2 Colorbar correctness

All field figures use `fig.colorbar(im, ax=ax)` directly — matplotlib handles orientation automatically. The hand-built `render_colorbar_panel` at `visualization/figure_axes.py:11-98` is deleted. A regression test (§ 9.1) asserts that a high-value pixel in the input maps to the top of the colorbar.

### 7.3 Layout evolution GIF

For each run, emit `figures/layout_evolution.gif` as a replay of **best-so-far spatial milestones**, not per-generation representative snapshots. The milestone sequence is:

- `initial layout`
- first feasible best-so-far layout (or best-near-feasible fallback if the run never becomes feasible)
- any later best-so-far frame that introduces a material component-placement shift
- `final layout`

This keeps the figure mode-agnostic across `raw`, `union`, and `llm`, while avoiding misleading sink-only frame churn. Individual frames are preserved as `figures/layout_evolution_frames/step_<NNN>.png`; titles carry the actual generation / evaluation provenance when needed. Built with `matplotlib.animation.PillowWriter` at 2 fps.

## 8. CLI Integration

### 8.1 New subcommand: `render-assets`

```
python -m optimizers.cli render-assets \
  --run scenario_runs/s1_typical/0416_2030__llm \
  [--hires]
```

Idempotent: reads `traces/`, writes `analytics/`, `figures/`, `tables/`. Can be rerun after a driver finishes; does not touch traces.

### 8.2 New subcommand: `compare-runs`

```
python -m optimizers.cli compare-runs \
  --run scenario_runs/s1_typical/0416_2030__raw \
  --run scenario_runs/s1_typical/0416_2033__union \
  --run scenario_runs/s1_typical/0416_2041__llm \
  --output scenario_runs/compare_reports/0416_2100__raw_vs_union_vs_llm
```

Produces a structured compare bundle (`analytics/`, `figures/`, `tables/`) and does not modify source runs.

### 8.3 Driver integration

At the end of each driver's main path (raw/union/llm), call the new asset-rendering pipeline automatically so that `optimize-benchmark` produces a complete run by default. `--skip-render` flag available for fast debugging.

### 8.4 Pop/gen CLI overrides

Add to `optimize-benchmark` and `run-benchmark-suite` subparsers in [optimizers/cli.py](optimizers/cli.py):

```
--population-size INT   # override algorithm.population_size from spec
--num-generations INT   # override algorithm.num_generations from spec
```

Applied after `load_optimization_spec()` via `algorithm_config._deep_merge` — spec files remain canonical and unchanged.

## 9. Testing & Migration

### 9.1 Kept tests (only these — minimum to lock regressions)

| test file | purpose |
|---|---|
| `tests/visualization/test_heatfield_orientation.py` | regression lock for the colorbar-inversion bug |
| `tests/visualization/test_render_assets_fixtures.py` | end-to-end: synthetic trace bundle → `render-assets` → assert all outputs exist + deterministic hashes |
| `tests/optimizers/test_multi_seed_layout.py` | asserts flat layout for N=1, `seeds/seed-<n>/` wrapping for N>=2, and the current aggregate gate semantics |

Explicitly NOT added (previously proposed, dropped as over-granular): separate `test_loaders`, `test_correlate`, `test_rollups`, `test_prompt_dedup`, `test_style_baseline`, `test_aggregate_multi_seed`. The end-to-end fixture test exercises these paths.

### 9.2 Smoke verification — 10×5

```bash
python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --population-size 10 --num-generations 5 \
  --output-root ./scenario_runs/s1_typical/smoke-llm
```

Scale: 10 + 10×5 = 60 PDE solves (~10× faster than current 32×16 = 544). Add `scripts/smoke_render_assets.sh` that runs all three modes at 10×5 + `render-assets` + non-zero exit on missing outputs.

### 9.3 Test commands — necessary only

```bash
# Fast refactor loop — the only command dev should run by default
conda run -n msfenicsx pytest -v \
  tests/visualization/test_heatfield_orientation.py \
  tests/visualization/test_render_assets_fixtures.py \
  tests/optimizers/test_multi_seed_layout.py

# Smoke (manual, once per major change)
bash scripts/smoke_render_assets.sh
```

No `pytest -v` over the whole repo unless a change bleeds into shared modules. If so, call out specifically affected tests in the plan.

### 9.4 Migration steps

1. Land § 6 style + § 7 figure factory + § 4 trace schema under new module paths (no callers yet).
2. Switch drivers to write new-schema traces; delete old-schema writers in the same PR (no dual-write).
3. Add `render-assets` and `compare-runs` CLI subcommands; legacy `visualization/case_pages.py` etc. stay.
4. Delete legacy paths: `visualization/case_pages.py`, `figure_axes.py`, `figure_theme.py`, old `artifacts.py` writer.
5. Run kept tests + one 10×5 smoke per mode. Commit.

Old runs under `scenario_runs/s1_typical/<timestamp>__<mode>/` are not migrated; archive or delete at user discretion.

## 10. Environment Prep

### 10.1 Apt mirror switch (Tsinghua) — first

Ubuntu 24.04 uses deb822 format at `/etc/apt/sources.list.d/ubuntu.sources`.

```bash
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
sudo sed -i \
  -e 's|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
  -e 's|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
  /etc/apt/sources.list.d/ubuntu.sources
sudo apt update
```

Fallback: Aliyun (`https://mirrors.aliyun.com/ubuntu`). Revert: `sudo mv .../ubuntu.sources.bak .../ubuntu.sources`.

### 10.2 Install texlive-full

```bash
sudo apt install -y texlive-full   # ~6GB; ~3-6 min on Tsinghua
```

Includes `texlive-xetex`, `texlive-lang-chinese` (ctex), `texlive-fonts-extra`, `fonts-noto-cjk`, and IEEE/Elsevier classes.

### 10.3 CTAN mirror for tlmgr (optional, for paper phase)

```bash
sudo tlmgr option repository https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/tlnet
```

### 10.4 Verify

```bash
xelatex --version
kpsewhich ctex.sty
fc-list | grep -i "noto serif cjk"
```

### 10.5 matplotlib font cache refresh

```bash
conda run -n msfenicsx python -c "import matplotlib.font_manager as fm; fm._load_fontmanager(try_read_cache=False)"
```

## 11. Success Criteria

- All three modes (raw/union/llm) produce identical top-level layout under `scenario_runs/s1_typical/<MMDD_HHMM>__<mode>/`.
- Representative figure paths are at most 3 levels deep.
- No empty `logs/` directories.
- Colorbar regression test passes: high-value input pixel → top of rendered colorbar.
- `render-assets` on a 10×5 smoke run completes in < 60s and produces all PDFs + PNGs + GIF + tables.
- `llm_request_trace.jsonl` lines are <1KB each; prompt bodies externalized under `prompts/<sha1>.md`.
- Kept test suite (3 files) runs in <30s on WSL2.
- `xelatex` and `ctex.sty` available on host for paper-phase work.

## 12. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Matplotlib font fallback warnings noisy on first run | One-time font-cache refresh in § 10.5; document in README |
| `pcolormesh(shading='gouraud')` slow at 2400 DPI | Only triggered via `--hires` flag; default 600 DPI path is fast |
| Content-addressed prompt dedup collides on sha1 | sha1 collision probability negligible at our scale; document as accepted risk |
| Old runs become unreadable by new CLI | Acceptable — old runs are one-shot; not migrating |
| Template multi-seed changes needed sooner than expected | Aggregation layer already supports N>=3; template change is one follow-up PR away |
