# msfenicsx

`msfenicsx` is a research platform for:

- 2D thermal dataset generation
- steady conduction with nonlinear radiation-style sink boundaries
- canonical FEniCSx thermal solves
- single-case thermal-layout optimization with manifest-backed artifacts

## Active Mainline

The current active paper-facing mainline is `s5_aggressive15` through `s7_aggressive25`. The primary debugging template is `s5_aggressive15`; use it for controller-sensitive smoke runs unless a scale or density check explicitly needs S6/S7. `s2_staged` is retained as a historical controller-sensitive companion, not the active mainline. S5/S6/S7 share the same aggressive `raw / union / llm` ladder. `nsga2_union` is the fixed stochastic operator-selection baseline for semantic-controller ablation: it uses the same `primitive_structured` operator substrate, NSGA-II backbone, legality policy, repair path, cheap screening, and PDE evaluation budget as `nsga2_llm`, but chooses operators through a fixed stochastic policy. `nsga2_llm` adds the representation-layer semantic controller, ranked selection, memory/reflection, and policy guidance on the same candidate support.

- one operating case
- fixed named components per benchmark
- mixed-shape component families with semantic placement hints
- all components optimize `x/y` only
- no optimized rotation
- one top-edge sink window with movable `start/end`
- scenario-specific decision dimensions:
  - S5: 32 variables, `c01_x/c01_y ... c15_x/c15_y + sink_start/sink_end`
  - S6: 42 variables, `c01_x/c01_y ... c20_x/c20_y + sink_start/sink_end`
  - S7: 52 variables, `c01_x/c01_y ... c25_x/c25_y + sink_start/sink_end`
- formal paper-facing expensive PDE evaluation budgets:
  - S5: `40 × 32 = 1280` nominal evaluations
  - S6: `56 × 36 = 2016` nominal evaluations
  - S7: `64 × 40 = 2560` nominal evaluations
- formal budgets are matched within each scenario across `raw`, `union`, `llm`, and raw-only algorithm comparisons
- two objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard constraints:
  - geometry legality
  - `case.total_radiator_span <= radiator_span_max`
- generator uses semantic band and edge hints before falling back to generic legal placement
- S5/S6/S7 form the aggressive 15/20/25-component family; compare modes within the same scenario before drawing cross-scenario conclusions
- all active components generate waste heat and declare explicit localized `source_area_ratio` values
- generation and cheap constraints enforce real minimum-clearance legality instead of overlap-only packing
- solver keeps the official top-edge `line_sink` and adds weak ambient outer-boundary cooling for background heat leakage
- cheap legality checks run before any expensive PDE solve
- paper-facing S5/S6/S7 `raw`, `union`, `llm`, and raw-only algorithm-comparison specs use `projection_plus_local_restore`
- paper-facing S5/S6/S7 `llm` specs use `semantic_ranked_pick` with the same controller parameters as the S5 debugging template
- active optimizer modes:
  - `nsga2_raw`: native-backbone baseline
  - `nsga2_union`: fixed stochastic operator-selection semantic-controller ablation
  - `nsga2_llm`: LLM semantic-controller route over the same operator support
- additional raw-only algorithm comparison specs:
  - `spea2_raw`
  - `moead_raw`

The additional algorithms are intentionally raw-only comparison baselines. Run them with
`optimize-benchmark` and compare the resulting concrete run roots with `compare-runs`;
the `run-benchmark-suite` ladder remains reserved for the `nsga2_raw / nsga2_union / nsga2_llm`
mode comparison.

## Active Inputs

Implemented (`s1_typical`):

- template: `scenarios/templates/s1_typical.yaml`
- evaluation spec: `scenarios/evaluation/s1_typical_eval.yaml`
- raw spec: `scenarios/optimization/s1_typical_raw.yaml`
- union spec: `scenarios/optimization/s1_typical_union.yaml`
- llm spec: `scenarios/optimization/s1_typical_llm.yaml`
- SPEA2 raw spec: `scenarios/optimization/s1_typical_spea2_raw.yaml`
- MOEA/D raw spec: `scenarios/optimization/s1_typical_moead_raw.yaml`
- raw profile: `scenarios/optimization/profiles/s1_typical_raw.yaml`
- union profile: `scenarios/optimization/profiles/s1_typical_union.yaml`
- SPEA2 raw profile: `scenarios/optimization/profiles/s1_typical_spea2_raw.yaml`
- MOEA/D raw profile: `scenarios/optimization/profiles/s1_typical_moead_raw.yaml`

Implemented (`s2_staged`):

- template: `scenarios/templates/s2_staged.yaml`
- evaluation spec: `scenarios/evaluation/s2_staged_eval.yaml`
- raw spec: `scenarios/optimization/s2_staged_raw.yaml`
- union spec: `scenarios/optimization/s2_staged_union.yaml`
- llm spec: `scenarios/optimization/s2_staged_llm.yaml`
- SPEA2 raw spec: `scenarios/optimization/s2_staged_spea2_raw.yaml`
- MOEA/D raw spec: `scenarios/optimization/s2_staged_moead_raw.yaml`
- raw profile: `scenarios/optimization/profiles/s2_staged_raw.yaml`
- union profile: `scenarios/optimization/profiles/s2_staged_union.yaml`
- SPEA2 raw profile: `scenarios/optimization/profiles/s2_staged_spea2_raw.yaml`
- MOEA/D raw profile: `scenarios/optimization/profiles/s2_staged_moead_raw.yaml`

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

Implemented (`s5_aggressive15`):

- template: `scenarios/templates/s5_aggressive15.yaml`
- evaluation spec: `scenarios/evaluation/s5_aggressive15_eval.yaml`
- raw spec: `scenarios/optimization/s5_aggressive15_raw.yaml`
- union spec: `scenarios/optimization/s5_aggressive15_union.yaml`
- llm spec: `scenarios/optimization/s5_aggressive15_llm.yaml`
- SPEA2 raw spec: `scenarios/optimization/s5_aggressive15_spea2_raw.yaml`
- MOEA/D raw spec: `scenarios/optimization/s5_aggressive15_moead_raw.yaml`
- raw profile: `scenarios/optimization/profiles/s5_aggressive15_raw.yaml`
- union profile: `scenarios/optimization/profiles/s5_aggressive15_union.yaml`
- SPEA2 raw profile: `scenarios/optimization/profiles/s5_aggressive15_spea2_raw.yaml`
- MOEA/D raw profile: `scenarios/optimization/profiles/s5_aggressive15_moead_raw.yaml`

Implemented (`s6_aggressive20`):

- template: `scenarios/templates/s6_aggressive20.yaml`
- evaluation spec: `scenarios/evaluation/s6_aggressive20_eval.yaml`
- raw spec: `scenarios/optimization/s6_aggressive20_raw.yaml`
- union spec: `scenarios/optimization/s6_aggressive20_union.yaml`
- llm spec: `scenarios/optimization/s6_aggressive20_llm.yaml`
- SPEA2 raw spec: `scenarios/optimization/s6_aggressive20_spea2_raw.yaml`
- MOEA/D raw spec: `scenarios/optimization/s6_aggressive20_moead_raw.yaml`
- raw profile: `scenarios/optimization/profiles/s6_aggressive20_raw.yaml`
- union profile: `scenarios/optimization/profiles/s6_aggressive20_union.yaml`
- SPEA2 raw profile: `scenarios/optimization/profiles/s6_aggressive20_spea2_raw.yaml`
- MOEA/D raw profile: `scenarios/optimization/profiles/s6_aggressive20_moead_raw.yaml`

Implemented (`s7_aggressive25`):

- template: `scenarios/templates/s7_aggressive25.yaml`
- evaluation spec: `scenarios/evaluation/s7_aggressive25_eval.yaml`
- raw spec: `scenarios/optimization/s7_aggressive25_raw.yaml`
- union spec: `scenarios/optimization/s7_aggressive25_union.yaml`
- llm spec: `scenarios/optimization/s7_aggressive25_llm.yaml`
- SPEA2 raw spec: `scenarios/optimization/s7_aggressive25_spea2_raw.yaml`
- MOEA/D raw spec: `scenarios/optimization/s7_aggressive25_moead_raw.yaml`
- raw profile: `scenarios/optimization/profiles/s7_aggressive25_raw.yaml`
- union profile: `scenarios/optimization/profiles/s7_aggressive25_union.yaml`
- SPEA2 raw profile: `scenarios/optimization/profiles/s7_aggressive25_spea2_raw.yaml`
- MOEA/D raw profile: `scenarios/optimization/profiles/s7_aggressive25_moead_raw.yaml`

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

`optimize-benchmark`, `run-llm`, and `run-benchmark-suite` runs are not
complete until `render-assets` has been executed on the final run root.
`--skip-render` is for temporary debugging only; if used, run
`render-assets` immediately before analysis or reporting. Budget knobs
`--population-size` and `--num-generations` apply to all three commands.
When a suite run includes at least two modes, `run-benchmark-suite` also
auto-writes a suite-owned `comparisons/` bundle that should be rendered as
part of the same run workflow:

- single-seed suite: `<run_root>/comparisons/`
- multi-seed suite: `<run_root>/comparisons/by_seed/seed-<n>/` plus `<run_root>/comparisons/aggregate/`

Interpretation:

- `comparisons/by_seed/seed-<n>/` = same benchmark seed across modes
- `comparisons/aggregate/` = across-seeds descriptive rollup for those same compared modes
- per-seed compare bundles should lead with `summary_overview`, `final_layout_comparison`, `temperature_field_comparison`, `gradient_field_comparison`, and `progress_dashboard`

## CLI

Run commands from WSL2 Ubuntu with the `msfenicsx` conda environment:

```bash
conda run -n msfenicsx python -m core.cli.main validate-scenario-template \
  --template scenarios/templates/s5_aggressive15.yaml

conda run -n msfenicsx python -m core.cli.main generate-case \
  --template scenarios/templates/s5_aggressive15.yaml \
  --seed 11 \
  --output-root ./scenario_runs/generated_cases/s5_aggressive15/seed-11

conda run -n msfenicsx python -m core.cli.main solve-case \
  --case ./scenario_runs/generated_cases/s5_aggressive15/seed-11/s5_aggressive15-seed-0011.yaml \
  --output-root ./scenario_runs

conda run -n msfenicsx python -m evaluation.cli evaluate-case \
  --case ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/case.yaml \
  --solution ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/solution.yaml \
  --spec scenarios/evaluation/s5_aggressive15_eval.yaml \
  --output ./evaluation_report.yaml \
  --bundle-root ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011

conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/raw-smoke

conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/union-smoke

conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-smoke

conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_spea2_raw.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/spea2-raw-smoke

conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_moead_raw.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/moead-raw-smoke

conda run -n msfenicsx python -m optimizers.cli run-llm \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-default-smoke

conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml \
  --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --mode raw \
  --mode union \
  --mode llm \
  --llm-profile default \
  --benchmark-seed 11 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs

# Parallel suite: S5 raw+union, 5 seeds, formal budget
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml \
  --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml \
  --mode raw --mode union \
  --benchmark-seed 11 --benchmark-seed 17 --benchmark-seed 23 --benchmark-seed 29 --benchmark-seed 31 \
  --population-size 40 --num-generations 32 \
  --parallel --max-concurrent-leaves 13 \
  --leaf-evaluation-workers 1 \
  --scenario-runs-root ./scenario_runs

conda run -n msfenicsx python -m optimizers.cli replay-llm-trace \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --request-trace ./scenario_runs/s5_aggressive15/<run_id>/llm/seeds/seed-11/traces/llm_request_trace.jsonl \
  --output ./scenario_runs/s5_aggressive15/<run_id>/llm/reports/<summary>.json

conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace ./scenario_runs/s5_aggressive15/<run_id>/llm/seeds/seed-11/traces/controller_trace.jsonl \
  --output ./scenario_runs/s5_aggressive15/<run_id>/llm/reports/controller_trace_summary.json

# Render analytics/tables/figures from an existing suite root, mode root, or concrete single-mode run root
conda run -n msfenicsx python -m optimizers.cli render-assets \
  --run ./scenario_runs/s5_aggressive15/<run_id> [--hires]

# Compare two or more concrete single-mode run roots into an external structured bundle
conda run -n msfenicsx python -m optimizers.cli compare-runs \
  --run ./scenario_runs/s5_aggressive15/<run_a> \
  --run ./scenario_runs/s5_aggressive15/<run_b> \
  --output ./scenario_runs/compare_reports/<compare_id>

# 10x5 smoke harness (raw/union/llm + render-assets + compare-runs)
bash scripts/smoke_render_assets.sh
```

Budget / render overrides apply to `optimize-benchmark`, `run-llm`, and `run-benchmark-suite`:

- `--population-size <int>` — override algorithm.population_size
- `--num-generations <int>` — override algorithm.num_generations
- `--skip-render` — temporary debug-only render skip; follow immediately with `render-assets` on the produced run root before analysis or reporting

`s5_aggressive15` is the primary fixed single-case debugging template. Repeat experiments by varying `algorithm.seed`, not by passing multiple `benchmark_seed` values.

The optimizer CLI uses a desktop-safe default worker budget when `--evaluation-workers` is omitted. During interactive daytime work, prefer `--evaluation-workers 2` or lower for `raw`, `union`, and later `llm` reruns.

## Environment

- canonical execution context: WSL2 Ubuntu
- preferred environment: `conda run -n msfenicsx ...`
- repository text files should use UTF-8 without BOM
- default networking is direct; do not enable `HTTP(S)_PROXY` / `ALL_PROXY` globally for normal repository work
- only add proxy settings inline for explicit outbound tasks such as network search, web lookup, or access to blocked external resources like GitHub / Google / `raw.githubusercontent.com`
- keep the LLM provider base URLs declared in `.env` as-is; they are normal runtime endpoints, not shell proxy settings

The `nsga2_llm` route uses the OpenAI-compatible client in `llm/openai_compatible/` and expects:

- one of the model profiles declared in `llm/openai_compatible/profiles.yaml`
- provider credentials from process environment or repository-root `.env`
- the active paper-facing `s5_aggressive15_llm` spec resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`

Edit the repository-root `.env` at `./.env` to declare each runtime route once:

```env
GPT_PROXY_API_KEY=...
GPT_PROXY_BASE_URL=...

QWEN_PROXY_API_KEY=...
QWEN_PROXY_BASE_URL=https://coding.dashscope.aliyuncs.com/v1

DEEPSEEK_PROXY_API_KEY=...
DEEPSEEK_PROXY_BASE_URL=https://llmapi.paratera.com/v1

GEMMA4_API_KEY=dummy
GEMMA4_BASE_URL=http://10.40.1.22:11434/v1

MIMO_API_KEY=...
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
```

The bundled model registry maps:

- `default -> GPT_PROXY_* -> gpt-5.4`
- `gpt -> GPT_PROXY_* -> gpt-5.4`
- `qwen3_6_plus -> QWEN_PROXY_* -> qwen3.6-plus`
- `glm_5 -> QWEN_PROXY_* -> glm-5`
- `minimax_m2_5 -> QWEN_PROXY_* -> MiniMax-M2.5`
- `deepseek_v4_flash -> DEEPSEEK_PROXY_* -> deepseek-v4-flash` with `extra_body.thinking.type=disabled` and `max_output_tokens=1024`
- `gemma4 -> GEMMA4_* -> gemma4:31b-it-q8_0` through the HPC Ollama/OpenAI-compatible endpoint, with `max_output_tokens=2048`
- `mimo_v2_5 -> MIMO_* -> mimo-v2.5` with `extra_body.chat_template_kwargs.enable_thinking=false` and `max_output_tokens=1024`

Recommended direct LLM benchmark invocation:

```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-gemma4-smoke
```

The checked-in `*_llm.yaml` specs declare `provider_profile: gemma4`, so `optimize-benchmark` auto-loads `GEMMA4_API_KEY / GEMMA4_BASE_URL` into `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL` when those runtime variables are missing. To switch models explicitly for one run, use `run-llm <profile>`:

```bash
conda run -n msfenicsx python -m optimizers.cli run-llm \
  gpt \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-gpt-smoke
```

```bash
conda run -n msfenicsx python -m optimizers.cli run-llm \
  qwen3_6_plus \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-qwen36-smoke
```

```bash
conda run -n msfenicsx python -m optimizers.cli run-llm \
  glm_5 \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-glm5-smoke
```

```bash
conda run -n msfenicsx python -m optimizers.cli run-llm \
  minimax_m2_5 \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-minimax-m25-smoke
```

```bash
conda run -n msfenicsx python -m optimizers.cli run-llm \
  deepseek_v4_flash \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-deepseek-v4-flash-smoke
```

```bash
conda run -n msfenicsx python -m optimizers.cli run-llm \
  gemma4 \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-gemma4-smoke
```

```bash
conda run -n msfenicsx python -m optimizers.cli run-llm \
  mimo_v2_5 \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s5_aggressive15/llm-mimo-v25-smoke
```

`run-benchmark-suite` keeps explicit suite control: use `--llm-profile <profile>` to choose the LLM route for suite LLM mode; if omitted, it uses `default`.

If needed:

```bash
conda run -n msfenicsx python -m pip install "openai>=1.70"
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
