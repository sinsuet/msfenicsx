# CLAUDE.md

This file gives Claude Code repository-specific guidance for `msfenicsx`.

## Repository Status

- `main` already contains the clean rebuild baseline.
- The only active paper-facing mainline is `s1_typical`.
- The retired four-component hot/cold benchmark is no longer an active supported workflow.
- The active paper-facing optimizer ladder is:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`
- The current controller line uses the semantic shared operator registry implemented for `s1_typical`.
- The active platform is organized around:
  - `core/`
  - `evaluation/`
  - `optimizers/`
  - `llm/`
  - `visualization/`
  - `scenarios/`
  - `tests/`
  - `docs/`

## Current Platform Identity

`msfenicsx` is a clean research platform for:

- 2D thermal dataset generation
- steady conduction with nonlinear radiation-style sink boundaries
- canonical case generation and official FEniCSx baseline solving
- single-case thermal layout optimization

The active canonical object flow is:

`scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle`

The active derived evaluation flow is:

`thermal_case + thermal_solution + evaluation_spec -> evaluation_report`

The active optimizer mainline is:

`s1_typical case -> repair -> cheap constraints -> solve -> single-case evaluation_report -> Pareto search -> manifest-backed optimization bundle + representative solutions`

The only active paper-facing inputs are:

- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`

The fixed benchmark decisions are:

- one operating case
- fifteen named components
- all fifteen optimize `x/y` only
- no optimized rotation
- 32 decision variables
- objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard sink-budget constraint:
  - `case.total_radiator_span <= radiator_span_max`
- cheap constraints must run before PDE
- repair must use projection plus local legality restoration

Additional backbone adapters may still exist as shared optimizer infrastructure, but they must not reintroduce retired hot/cold benchmark assets, alternate paper-facing specs, or benchmark-specific controller semantics.

## Architectural Expectations

- Keep `core/` as the kernel for:
  - schema
  - geometry
  - generator
  - solver
  - artifact I/O
  - contracts
  - CLI
- Keep `evaluation/`, `optimizers/`, `llm/`, and `visualization/` as separate top-level layers that consume `core/`.
- Do not add business logic to `scenarios/`; it is for hand-authored inputs.
- Do not recreate legacy runtime folders such as `src/`, `radiation_gen/`, `examples/`, or `states/`.

## Environment And Execution

- Canonical execution context is WSL2 Ubuntu.
- Even if the workspace is opened through `\\wsl$\Ubuntu\home\hymn\msfenicsx`, treat the repo as Linux-first and use `/home/hymn/msfenicsx`.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer: `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
- Repository text artifacts should use UTF-8 without BOM.
- Treat terminal-side mojibake from the host bridge as environment noise unless the saved file itself is corrupted.

### Preferred Commands

Run tests:
```bash
conda run -n msfenicsx pytest -v
```

Run specific test file:
```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
```

Validate template:
```bash
conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml
```

Generate case:
```bash
conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s1_typical.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s1_typical/seed-11
```

Solve case:
```bash
conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml --output-root ./scenario_runs
```

Evaluate case:
```bash
conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/s1_typical/s1_typical-seed-0011/case.yaml --solution ./scenario_runs/s1_typical/s1_typical-seed-0011/solution.yaml --spec scenarios/evaluation/s1_typical_eval.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/s1_typical/s1_typical-seed-0011
```

Optimize (raw/union/llm):
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/raw-smoke
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_union.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/union-smoke
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_llm.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/llm-smoke
```

Run benchmark suite:
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite --optimization-spec scenarios/optimization/s1_typical_raw.yaml --optimization-spec scenarios/optimization/s1_typical_union.yaml --optimization-spec scenarios/optimization/s1_typical_llm.yaml --mode raw --mode union --mode llm --benchmark-seed 11 --evaluation-workers 2 --scenario-runs-root ./scenario_runs
```

Install LLM dependency:
```bash
conda run -n msfenicsx python -m pip install "openai>=1.70"
```

### LLM Configuration

The active `nsga2_llm` route uses OpenAI-compatible provider profiles:

- `conda run -n msfenicsx python -m optimizers.cli run-llm` defaults to the bundled `default` profile, which points to GPT
- switch providers explicitly with `run-llm claude ...` or `run-llm qwen ...`
- provider profile declarations live in `llm/openai_compatible/profiles.yaml`
- bundled default models are:
  - `gpt -> gpt-5.4`
  - `claude -> claude-opus-4-6`
  - `qwen -> qwen3.6-plus`
- the active `scenarios/optimization/s1_typical_llm.yaml` resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`
- repository-root `/home/hymn/msfenicsx/.env` should keep the raw provider credentials:
  - `GPT_PROXY_API_KEY`
  - `GPT_PROXY_BASE_URL=https://rust.cat/v1`
  - `CLAUDE_PROXY_API_KEY`
  - `CLAUDE_PROXY_BASE_URL=https://apiproxy.work/v1`
  - `QWEN_PROXY_API_KEY`
  - `QWEN_PROXY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`

## Engineering Guardrails

- Read the exact source before editing and preserve precise edit context.
- If a write looks risky because of locking, permissions, or unclear ownership, stop and notify first.
- Never hardcode API keys, tokens, or private credentials.
- Do not silently change important runtime or solver defaults without documenting the change.
- Fix root causes with physically and architecturally defensible changes instead of fake passes or invalid shortcuts.
- Do not repair controller behavior by hardcoding benchmark seeds, scenario IDs, or operator names as one-off policy exceptions.
- Prefer portable optimizer-layer policy mechanisms over benchmark-specific prompt hacks.
- Always run `conda run -n msfenicsx pytest -v` to verify changes before claiming completion.
- When modifying optimizer or controller logic, run the specific test file first, then the full suite.

## Data And Artifact Rules

- Treat `scenario_template`, `thermal_case`, and `thermal_solution` as the active canonical contracts.
- `s1_typical` is single-case only and must not define `operating_case_profiles`.
- `s1_typical` is a fixed single-case benchmark; do not use multiple benchmark seeds to simulate multiple problem instances.
- Conservative daytime optimizer reruns should prefer `--evaluation-workers 2` or lower, including future `llm` runs.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding optimizer metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files.
- Repository-wide backbone defaults belong in `optimizers/algorithm_config.py`.
- Benchmark-specific tuning belongs in `scenarios/optimization/profiles/` and `algorithm.parameters`.
- Active runtime outputs should go to `scenario_runs/`, not source folders.
- Active optimizer runs should write under `scenario_runs/s1_typical/<run_id>/`.
- The canonical paper-facing run layout is:
  - `scenario_runs/s1_typical/<MMDD_HHMM>__<mode_slug>/`
- `mode_slug` must use the stable order: `raw`, `union`, `llm`.
- Mixed-mode runs keep sibling mode directories plus optional `comparison/`.
- Representative solved-case bundles live under:
  - `<mode>/seeds/seed-<n>/representatives/<representative_id>/`
- Representative bundles must preserve:
  - `fields/*.npz`
  - `summaries/field_view.json`
  - `pages/index.html`
- Keep controller-guided raw traces:
  - `controller_trace.json`
  - `operator_trace.json`
  - `llm_request_trace.jsonl`
  - `llm_response_trace.jsonl`
- Keep shared compact sidecars:
  - `evaluation_events.jsonl`
  - `generation_summary.jsonl`
- Remove temporary scripts, debug files, caches, and one-off intermediate outputs after validation when they are not intended repository state.
- Do not manually edit generated artifacts to change conclusions.

## Testing Expectations

- Maintained tests belong under `tests/`.
- Add or update focused tests for new behavior.
- Run fresh relevant verification before claiming completion.

Current maintained test areas:

- `tests/schema/`
- `tests/geometry/`
- `tests/generator/`
- `tests/solver/`
- `tests/io/`
- `tests/cli/`
- `tests/evaluation/`
- `tests/optimizers/`
- `tests/visualization/`

## Evidence And Reporting Expectations

- Scientific or performance claims must identify the relevant template, case, solver profile, seed, and runtime path or artifact bundle.
- For optimization claims, identify whether evidence comes from one representative point or the Pareto set.
- Keep the decision encoding, evaluation spec, repair, and expensive-evaluation budget matched across comparisons unless a document explicitly defines a different experiment class.
- Describe `nsga2_union` and `nsga2_llm` as using the same mixed action registry with only the controller changed.
- If something is not validated yet, label it as a hypothesis rather than a confirmed result.
- Keep infeasible cases, failed solves, regressions, and anomalies visible in analysis.
- Failure reasons and dominant violations are valid evidence and should remain visible in artifacts when relevant.
- Cheap local `controller_trace` diagnostics are valid pre-live evidence before any new live rerun.

## Documentation Expectations

- For major contract or workflow changes, update:
  - `README.md`
  - relevant docs under `docs/`
  - `CLAUDE.md` when repository guidance changes
  - `AGENTS.md` to keep it in sync
- Keep active docs aligned with implemented reality.
- Treat `CLAUDE.md` as authoritative repository guidance for Claude Code sessions.
- Treat `AGENTS.md` as authoritative repository guidance for Codex sessions.

## Useful References

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`
- `docs/superpowers/plans/2026-03-26-msfenicsx-clean-rebuild-phase1.md`
- `docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md`
- `docs/superpowers/plans/2026-04-02-s1-typical-mainline-reset.md`
- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/profiles/s1_typical_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_union.yaml`
- `optimizers/algorithm_config.py`
- `optimizers/drivers/raw_driver.py`
- `optimizers/drivers/union_driver.py`
- `optimizers/problem.py`
- `optimizers/repair.py`
- `optimizers/cheap_constraints.py`
- `optimizers/operator_pool/operators.py`
- `optimizers/operator_pool/domain_state.py`
- `llm/openai_compatible/client.py`
- `llm/openai_compatible/profiles.yaml`
- `tests/optimizers/test_raw_driver_matrix.py`
- `tests/optimizers/test_repair.py`
