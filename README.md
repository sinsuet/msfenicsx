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
- cheap legality checks run before any expensive PDE solve
- repair uses projection plus local legality restoration
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
  --output-root ./scenario_runs/s1_typical/raw-smoke

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --mode raw \
  --mode union \
  --benchmark-seed 11 \
  --benchmark-seed 17 \
  --benchmark-seed 23 \
  --scenario-runs-root ./scenario_runs

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli replay-llm-trace \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --request-trace ./scenario_runs/s1_typical/<run_id>/llm/seeds/seed-11/llm_request_trace.jsonl \
  --output ./scenario_runs/s1_typical/<run_id>/llm/reports/<summary>.json

/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace ./scenario_runs/s1_typical/<run_id>/union/seeds/seed-11/controller_trace.json \
  --output ./scenario_runs/s1_typical/<run_id>/union/reports/controller_trace_summary.json
```

## Environment

- canonical execution context: WSL2 Ubuntu
- preferred environment: `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
- repository text files should use UTF-8 without BOM

The `nsga2_llm` route uses the OpenAI-compatible client in `llm/openai_compatible/` and expects:

- `OPENAI_API_KEY` from process environment or repository-root `.env`
- `model=gpt-5.4`

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
