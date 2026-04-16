# msfenicsx

`msfenicsx` is a research platform for:

- 2D thermal dataset generation
- steady conduction with nonlinear radiation-style sink boundaries
- canonical FEniCSx thermal solves
- single-case thermal-layout optimization with manifest-backed artifacts

## Active Mainline

The only active paper-facing mainline is `s1_typical`.

- one operating case
- fifteen fixed named components
- mixed-shape component families with semantic placement hints
- all fifteen components optimize `x/y` only
- no optimized rotation
- one top-edge sink window with movable `start/end`
- 32 decision variables: `c01_x/c01_y ... c15_x/c15_y + sink_start/sink_end`
- two objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard constraints:
  - geometry legality
  - `case.total_radiator_span <= radiator_span_max`
- generator uses semantic band and edge hints before falling back to generic legal placement
- template now targets `component_area_ratio ~= 0.45`, where the denominator is the official placement region rather than the full panel area
- all fifteen components generate waste heat and declare explicit localized `source_area_ratio` values
- generation, cheap constraints, and repair all enforce real minimum-clearance legality instead of overlap-only packing
- solver keeps the official top-edge `line_sink` and adds weak ambient outer-boundary cooling for background heat leakage
- cheap legality checks run before any expensive PDE solve
- repair uses projection plus local legality restoration with shape-aware overlap handling
- active optimizer modes:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`

The retired four-component hot/cold mainline is no longer part of the active repository workflow.

## Active Inputs

- template: `scenarios/templates/s1_typical.yaml`
- evaluation spec: `scenarios/evaluation/s1_typical_eval.yaml`
- raw spec: `scenarios/optimization/s1_typical_raw.yaml`
- union spec: `scenarios/optimization/s1_typical_union.yaml`
- llm spec: `scenarios/optimization/s1_typical_llm.yaml`
- raw profile: `scenarios/optimization/profiles/s1_typical_raw.yaml`
- union profile: `scenarios/optimization/profiles/s1_typical_union.yaml`

## Module Boundaries

- `core/`: schema, geometry, generator, solver, artifact I/O, and CLI
- `evaluation/`: single-case evaluation specs, metrics, reports, and CLI
- `optimizers/`: decision encoding, repair, cheap constraints, raw/union/llm drivers, run-suite orchestration, summaries, and optimizer CLI
- `llm/`: OpenAI-compatible controller client boundary
- `visualization/`: single-case pages, mode indexes, mixed-mode comparisons, and LLM reports
- `scenarios/`: hand-authored scenario, evaluation, and optimization inputs
- `tests/`: maintained automated verification
- `docs/`: active specs, plans, and reports

## Active Flows

Canonical object flow:

`scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle`

Derived evaluation flow:

`thermal_case + thermal_solution + evaluation_spec -> evaluation_report`

Active optimizer flow:

`s1_typical benchmark case -> repair -> cheap constraints -> solve -> single-case evaluation_report -> Pareto search -> manifest-backed optimization bundle`

## Run Layout

Paper-facing optimization and visualization outputs now live under:

```text
scenario_runs/s1_typical/<MMDD_HHMM>__<mode_slug>/
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
summaries/field_view.json
pages/index.html
```

Scientific figure exports under each representative, mode, and comparison page now follow these rules:

- representative layout figures render real component footprints from exported outlines instead of rectangle bounds only
- `figures/layout.svg`, `temperature-field.svg`, `temperature-contours.svg`, and `gradient-field.svg` are white-background single-case scientific figures
- `figures/mode-summary.svg` is a progress-first mode figure with evaluation-index panels for best peak, best gradient, feasible rate, and Pareto size
- `comparison/figures/progress.svg` compares the same four progress metrics across `raw`, `union`, and `llm`
- `comparison/figures/fields.svg` renders actual temperature and gradient field panels with shared color scales instead of hotspot-only surrogate charts
- long interpretation prose belongs in HTML tables and reports, not inside the SVG figure body

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
  --mode raw \
  --mode union \
  --benchmark-seed 11 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs

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
  --request-trace ./scenario_runs/s1_typical/<run_id>/llm/seeds/seed-11/llm_request_trace.jsonl \
  --output ./scenario_runs/s1_typical/<run_id>/llm/reports/<summary>.json

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace ./scenario_runs/s1_typical/<run_id>/union/seeds/seed-11/controller_trace.json \
  --output ./scenario_runs/s1_typical/<run_id>/union/reports/controller_trace_summary.json
```

`s1_typical` is a fixed single-case benchmark. Repeat experiments by varying `algorithm.seed`, not by passing multiple `benchmark_seed` values.

The optimizer CLI uses a desktop-safe default worker budget when `--evaluation-workers` is omitted. During interactive daytime work, prefer `--evaluation-workers 2` or lower for `raw`, `union`, and later `llm` reruns.

## Environment

- canonical execution context: WSL2 Ubuntu
- preferred environment: `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
- repository text files should use UTF-8 without BOM

The `nsga2_llm` route uses the OpenAI-compatible client in `llm/openai_compatible/` and expects:

- one of the provider profiles declared in `llm/openai_compatible/profiles.yaml`
- provider credentials from process environment or repository-root `.env`
- the active paper-facing `s1_typical_llm` spec now resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`

Recommended multi-provider `.env` layout:

```env
GPT_PROXY_API_KEY=...
GPT_PROXY_BASE_URL=https://gpt.example/v1

CLAUDE_PROXY_API_KEY=...
CLAUDE_PROXY_BASE_URL=https://claude.example/v1

QWEN_PROXY_API_KEY=...
QWEN_PROXY_BASE_URL=https://qwen.example/v1
```

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
