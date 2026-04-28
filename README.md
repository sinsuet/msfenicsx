# msfenicsx

`msfenicsx` is a research platform for:

- 2D thermal dataset generation
- steady conduction with nonlinear radiation-style sink boundaries
- canonical FEniCSx thermal solves
- single-case thermal-layout optimization with manifest-backed artifacts

## Active Mainline

The active paper-facing mainlines are `s1_typical`, `s2_staged`, `s3_scale20`, and `s4_dense25`. `s2_staged` is the current controller-sensitive S2 companion benchmark. `s3_scale20` and `s4_dense25` are the larger companions in the same paper-facing `raw / union / llm` ladder. In that ladder, `union` and `llm` use the same primitive operator substrate and legality policy; `llm` differs through its representation-layer controller only.

- one operating case
- fixed named components per benchmark
- mixed-shape component families with semantic placement hints
- all components optimize `x/y` only
- no optimized rotation
- one top-edge sink window with movable `start/end`
- scenario-specific decision dimensions:
  - S1/S2: 32 variables, `c01_x/c01_y ... c15_x/c15_y + sink_start/sink_end`
  - S3: 42 variables, `c01_x/c01_y ... c20_x/c20_y + sink_start/sink_end`
  - S4: 52 variables, `c01_x/c01_y ... c25_x/c25_y + sink_start/sink_end`
- two objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard constraints:
  - geometry legality
  - `case.total_radiator_span <= radiator_span_max`
- generator uses semantic band and edge hints before falling back to generic legal placement
- S2 targets `component_area_ratio ~= 0.45`; S3 and S4 intentionally use higher occupancy targets around `0.52-0.55` and `0.60-0.63`
- all active components generate waste heat and declare explicit localized `source_area_ratio` values
- generation and cheap constraints enforce real minimum-clearance legality instead of overlap-only packing
- solver keeps the official top-edge `line_sink` and adds weak ambient outer-boundary cooling for background heat leakage
- cheap legality checks run before any expensive PDE solve
- paper-facing `union` and `llm` runs both use `minimal_canonicalization`; `llm` keeps policy and guardrail signals as soft textual guidance over the same candidate support
- active optimizer modes:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`

## Active Inputs

Implemented (`s1_typical`):

- template: `scenarios/templates/s1_typical.yaml`
- evaluation spec: `scenarios/evaluation/s1_typical_eval.yaml`
- raw spec: `scenarios/optimization/s1_typical_raw.yaml`
- union spec: `scenarios/optimization/s1_typical_union.yaml`
- llm spec: `scenarios/optimization/s1_typical_llm.yaml`
- raw profile: `scenarios/optimization/profiles/s1_typical_raw.yaml`
- union profile: `scenarios/optimization/profiles/s1_typical_union.yaml`

Implemented (`s2_staged`):

- template: `scenarios/templates/s2_staged.yaml`
- evaluation spec: `scenarios/evaluation/s2_staged_eval.yaml`
- raw spec: `scenarios/optimization/s2_staged_raw.yaml`
- union spec: `scenarios/optimization/s2_staged_union.yaml`
- llm spec: `scenarios/optimization/s2_staged_llm.yaml`
- raw profile: `scenarios/optimization/profiles/s2_staged_raw.yaml`
- union profile: `scenarios/optimization/profiles/s2_staged_union.yaml`

Implemented (`s3_scale20`):

- template: `scenarios/templates/s3_scale20.yaml`
- evaluation spec: `scenarios/evaluation/s3_scale20_eval.yaml`
- raw spec: `scenarios/optimization/s3_scale20_raw.yaml`
- union spec: `scenarios/optimization/s3_scale20_union.yaml`
- llm spec: `scenarios/optimization/s3_scale20_llm.yaml`
- raw profile: `scenarios/optimization/profiles/s3_scale20_raw.yaml`
- union profile: `scenarios/optimization/profiles/s3_scale20_union.yaml`

Implemented (`s4_dense25`):

- template: `scenarios/templates/s4_dense25.yaml`
- evaluation spec: `scenarios/evaluation/s4_dense25_eval.yaml`
- raw spec: `scenarios/optimization/s4_dense25_raw.yaml`
- union spec: `scenarios/optimization/s4_dense25_union.yaml`
- llm spec: `scenarios/optimization/s4_dense25_llm.yaml`
- raw profile: `scenarios/optimization/profiles/s4_dense25_raw.yaml`
- union profile: `scenarios/optimization/profiles/s4_dense25_union.yaml`

## Module Boundaries

- `core/`: schema, geometry, generator, solver, artifact I/O, and CLI
- `evaluation/`: single-case evaluation specs, metrics, reports, and CLI
- `optimizers/`: decision encoding, repair, cheap constraints, raw/union/llm drivers, run-suite orchestration, analytics/trace subpackages, render-assets/compare-runs, and optimizer CLI
- `llm/`: OpenAI-compatible controller client boundary
- `visualization/`: figures subpackage (pareto, temperature_field, gradient_field, hypervolume, layout_evolution, operator_heatmap) and centralized baseline style
- `scenarios/`: hand-authored scenario, evaluation, and optimization inputs
- `tests/`: maintained automated verification
- `docs/`: active specs, plans, and reports

## Active Flows

Canonical object flow:

`scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle`

Derived evaluation flow:

`thermal_case + thermal_solution + evaluation_spec -> evaluation_report`

Active optimizer flow:

`paper-facing scenario case -> legality policy -> cheap constraints -> solve -> single-case evaluation_report -> Pareto search -> manifest-backed optimization bundle`

## Run Layout

Paper-facing optimization and visualization outputs now live under:

```text
scenario_runs/<scenario_id>/<MMDD_HHMM>__<mode_slug>/
```

`mode_slug` always follows the stable order `raw`, `union`, `llm`.

Representative physical-field bundles live under:

```text
<mode>/seeds/seed-<n>/representatives/<representative_id>/
```

and include:

```text
case.yaml
solution.yaml
evaluation.yaml
fields/temperature_grid.npz
fields/gradient_magnitude_grid.npz
```

Standalone solved-case bundles written by `core.cli.main solve-case` live under:

```text
scenario_runs/<scenario_id>/<case_id>/
```

and, when field exports are present, also render:

```text
figures/layout.png
figures/temperature_field.png
figures/gradient_field.png
```

Trace artifacts live at the seed run root as canonical JSONL sidecars:

```text
traces/evaluation_events.jsonl
traces/generation_summary.jsonl
traces/controller_trace.jsonl
traces/operator_trace.jsonl
traces/llm_request_trace.jsonl
traces/llm_response_trace.jsonl
run.yaml                            # per-seed manifest
```

Operator trace rows follow the §4.3 schema
(`decision_id, generation, operator_name, parents, offspring, params_digest, wall_ms`).

Central rendered assets (written by `optimizers.cli render-assets`) live
beside the traces:

- `analytics/*.csv` — hypervolume, Pareto front, progress timeline, operator usage, decision rollups
- `figures/*.png` — raster figures for quick browsing
- `figures/pdf/*.pdf` — vector companions kept in a dedicated subdirectory
- figure outputs include `pareto_front`, `hypervolume_progress`, `objective_progress`, `temperature_trace`, `gradient_trace`, `constraint_violation_progress`, `layout_initial`, `layout_final`, `layout_evolution`, `temperature_field_<repr>`, `gradient_field_<repr>`, and `operator_phase_heatmap`
- `layout_evolution` is a best-so-far spatial-milestone replay; preserved frame PNGs live under `figures/layout_evolution_frames/step_<NNN>.png`
- layout figures are publication panels: clean board on the left, compact run metadata on the right, internal component labels, and an explicit sink ribbon
- field figures keep a mandatory top title, explicit sink rendering, internal white label chips, and aligned colorbar composition
- `tables/*.csv` / `tables/*.tex` — summary statistics and representative-point tables
- baseline style centralized in `visualization/style/baseline.py`

`optimize-benchmark`, `run-llm`, and `run-benchmark-suite` auto-invoke
`render-assets` unless `--skip-render` is passed. Budget knobs
`--population-size` and `--num-generations` apply to all three commands.
When a suite run includes at least two modes, `run-benchmark-suite` also auto-writes a suite-owned `comparisons/` bundle:

- single-seed suite: `<run_root>/comparisons/`
- multi-seed suite: `<run_root>/comparisons/by_seed/seed-<n>/` plus `<run_root>/comparisons/aggregate/`

Interpretation:

- `comparisons/by_seed/seed-<n>/` = same benchmark seed across modes
- `comparisons/aggregate/` = across-seeds descriptive rollup for those same compared modes
- per-seed compare bundles should lead with `summary_overview`, `final_layout_comparison`, `temperature_field_comparison`, `gradient_field_comparison`, and `progress_dashboard`

## CLI

Run commands from WSL2 Ubuntu with the `msfenicsx` conda environment:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template \
  --template scenarios/templates/s1_typical.yaml

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case \
  --template scenarios/templates/s1_typical.yaml \
  --seed 11 \
  --output-root ./scenario_runs/generated_cases/s1_typical/seed-11

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main solve-case \
  --case ./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml \
  --output-root ./scenario_runs

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m evaluation.cli evaluate-case \
  --case ./scenario_runs/s1_typical/s1_typical-seed-0011/case.yaml \
  --solution ./scenario_runs/s1_typical/s1_typical-seed-0011/solution.yaml \
  --spec scenarios/evaluation/s1_typical_eval.yaml \
  --output ./evaluation_report.yaml \
  --bundle-root ./scenario_runs/s1_typical/s1_typical-seed-0011

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/raw-smoke

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/union-smoke

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-smoke

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-default-smoke

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --mode raw \
  --mode union \
  --mode llm \
  --benchmark-seed 11 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli replay-llm-trace \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --request-trace ./scenario_runs/s1_typical/<run_id>/llm/seeds/seed-11/traces/llm_request_trace.jsonl \
  --output ./scenario_runs/s1_typical/<run_id>/llm/reports/<summary>.json

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace ./scenario_runs/s1_typical/<run_id>/llm/seeds/seed-11/traces/controller_trace.jsonl \
  --output ./scenario_runs/s1_typical/<run_id>/llm/reports/controller_trace_summary.json

# Render analytics/tables/figures from an existing suite root, mode root, or concrete single-mode run root
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli render-assets \
  --run ./scenario_runs/s1_typical/<run_id> [--hires]

# Compare two or more concrete single-mode run roots into an external structured bundle
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli compare-runs \
  --run ./scenario_runs/s1_typical/<run_a> \
  --run ./scenario_runs/s1_typical/<run_b> \
  --output ./scenario_runs/compare_reports/<compare_id>

# 10x5 smoke harness (raw/union/llm + render-assets + compare-runs)
bash scripts/smoke_render_assets.sh
```

Budget / render overrides apply to both `optimize-benchmark` and `run-llm`:

- `--population-size <int>` — override algorithm.population_size
- `--num-generations <int>` — override algorithm.num_generations
- `--skip-render` — skip the auto-invoked `render-assets` pass

`s1_typical` is a fixed single-case benchmark. Repeat experiments by varying `algorithm.seed`, not by passing multiple `benchmark_seed` values.

The optimizer CLI uses a desktop-safe default worker budget when `--evaluation-workers` is omitted. During interactive daytime work, prefer `--evaluation-workers 2` or lower for `raw`, `union`, and later `llm` reruns.

## Environment

- canonical execution context: WSL2 Ubuntu
- preferred environment: `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
- repository text files should use UTF-8 without BOM
- default networking is direct; do not enable `HTTP(S)_PROXY` / `ALL_PROXY` globally for normal repository work
- only add proxy settings inline for explicit outbound tasks such as network search, web lookup, or access to blocked external resources like GitHub / Google / `raw.githubusercontent.com`
- keep the LLM provider base URLs declared in `.env` as-is; they are normal runtime endpoints, not shell proxy settings

The `nsga2_llm` route uses the OpenAI-compatible client in `llm/openai_compatible/` and expects:

- one of the provider profiles declared in `llm/openai_compatible/profiles.yaml`
- provider credentials from process environment or repository-root `.env`
- the active paper-facing `s1_typical_llm` spec now resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`

Edit the repository-root `.env` at `/home/hymn/msfenicsx/.env` to declare each provider once:

```env
GPT_PROXY_API_KEY=...
GPT_PROXY_BASE_URL=https://apiproxy.work/v1

CLAUDE_PROXY_API_KEY=...
CLAUDE_PROXY_BASE_URL=https://apiproxy.work/v1

QWEN_PROXY_API_KEY=...
QWEN_PROXY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

The bundled provider registry maps:

- `default -> gpt -> GPT_PROXY_* -> gpt-5.4`
- `claude -> CLAUDE_PROXY_* -> claude-sonnet-4-6`
- `qwen -> QWEN_PROXY_* -> qwen3.6-plus`
- edit `llm/openai_compatible/profiles.yaml` if you want to change the bundled default model names later

Recommended LLM benchmark invocation:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-default-smoke
```

This uses the bundled `default` profile, which points to GPT by default. To switch providers explicitly:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm \
  claude \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-claude-smoke
```

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm \
  qwen \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-qwen-smoke
```

Direct `optimize-benchmark` execution for `s1_typical_llm.yaml` still works, but only if you explicitly provide:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

If needed:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m pip install "openai>=1.70"
```

## Verification

Maintained verification areas:

- `tests/schema/`
- `tests/geometry/`
- `tests/generator/`
- `tests/solver/`
- `tests/io/`
- `tests/cli/`
- `tests/evaluation/`
- `tests/optimizers/`
- `tests/visualization/`
