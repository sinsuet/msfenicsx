# AGENTS.md

This file gives Codex-style agents repository-specific guidance for `msfenicsx`.

## Repository Status

- `main` already contains the clean rebuild baseline.
- The only active paper-facing mainline is `s1_typical`.
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

## Environment And Execution

- Canonical execution context is WSL2 Ubuntu.
- Even if the workspace is opened through `\\wsl$\\Ubuntu\\home\\hymn\\msfenicsx`, agents should treat the repo as Linux-first and use `/home/hymn/msfenicsx`.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer:
  - `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
- Repository text artifacts should use UTF-8 without BOM.
- Treat terminal-side mojibake from the host bridge as environment noise unless the saved file itself is corrupted.

Preferred commands:

- `conda run -n msfenicsx pytest -v`
- `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml`
- `conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s1_typical.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s1_typical/seed-11`
- `conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml --output-root ./scenario_runs`
- `conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/s1_typical/s1_typical-seed-0011/case.yaml --solution ./scenario_runs/s1_typical/s1_typical-seed-0011/solution.yaml --spec scenarios/evaluation/s1_typical_eval.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/s1_typical/s1_typical-seed-0011`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_union.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/union-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_llm.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/llm-smoke`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite --optimization-spec scenarios/optimization/s1_typical_raw.yaml --optimization-spec scenarios/optimization/s1_typical_union.yaml --optimization-spec scenarios/optimization/s1_typical_llm.yaml --mode raw --mode union --mode llm --benchmark-seed 11 --evaluation-workers 2 --scenario-runs-root ./scenario_runs`
- `conda run -n msfenicsx python -m optimizers.cli replay-llm-trace --optimization-spec scenarios/optimization/s1_typical_llm.yaml --request-trace ./scenario_runs/s1_typical/<run_id>/llm/seeds/seed-11/traces/llm_request_trace.jsonl --output ./scenario_runs/s1_typical/<run_id>/llm/reports/<summary>.json`
- `conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace --controller-trace ./scenario_runs/s1_typical/<run_id>/union/seeds/seed-11/controller_trace.json --output ./scenario_runs/s1_typical/<run_id>/union/reports/<summary>.json`
- `conda run -n msfenicsx python -m optimizers.cli render-assets --run ./scenario_runs/s1_typical/<run_id> [--hires]`
- `conda run -n msfenicsx python -m optimizers.cli compare-runs --run ./scenario_runs/s1_typical/<run_a> --run ./scenario_runs/s1_typical/<run_b> --output ./compare.json`
- `bash scripts/smoke_render_assets.sh` (10×5 local smoke harness covering raw/union/llm + render-assets + compare-runs)
- Budget / render overrides (work on `optimize-benchmark` and `run-llm`): `--population-size`, `--num-generations`, `--skip-render`
- `conda run -n msfenicsx python -m pip install "openai>=1.70"`

The active `nsga2_llm` route currently uses OpenAI-compatible provider profiles:

- `conda run -n msfenicsx python -m optimizers.cli run-llm` defaults to the bundled `default` profile, which points to GPT
- switch providers explicitly with `run-llm claude ...` or `run-llm qwen ...`
- provider profile declarations live in `llm/openai_compatible/profiles.yaml`
- bundled default models are:
  - `gpt -> gpt-5.4`
  - `claude -> claude-sonnet-4-6`
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
- `mode_slug` must use the stable order:
  - `raw`
  - `union`
  - `llm`
- Mixed-mode runs keep sibling mode directories plus optional `comparison/`.
- Representative solved-case bundles live under:
  - `<mode>/seeds/seed-<n>/representatives/<representative_id>/`
- Representative bundles must preserve:
  - `fields/*.npz`
  - `summaries/field_view.json`
  - `pages/` (reserved directory for downstream rendering; empty by default)
- Run-root dual-write policy for trace artifacts (logging/viz refactor):
  - Flat JSON at run root: `controller_trace.json`, `operator_trace.json`, `llm_metrics.json`
  - Spec-§3.1 JSONL sidecars under `traces/`:
    - `traces/evaluation_events.jsonl`
    - `traces/generation_summary.jsonl`
    - `traces/controller_trace.jsonl`
    - `traces/operator_trace.jsonl`
    - `traces/llm_request_trace.jsonl`
    - `traces/llm_response_trace.jsonl`
    - `traces/llm_reflection_trace.jsonl`
  - Operator trace rows follow §4.3 schema: `decision_id, generation, operator_name, parents, offspring, params_digest, wall_ms`
  - Per-seed `run.yaml` manifest captures mode, seeds, spec paths, population/generation size, wall-clock seconds
- Central rendered assets live beside traces (written by `render-assets`):
  - `analytics/*.csv`
  - `figures/*.png` (hi-res PDF variants when `--hires`)
- Remove temporary scripts, debug files, caches, and one-off intermediate outputs after validation when they are not intended repository state.
- Do not manually edit generated artifacts to change conclusions.

## Testing Expectations

- Maintained tests belong under `tests/`.
- Add or update focused tests for new behavior.
- Run the **focused** tests relevant to your change (specific file or subdirectory under `tests/`) before claiming completion. Escalate to the full `conda run -n msfenicsx pytest -v` only when you are genuinely uncertain about cross-module impact — e.g. editing shared contracts in `core/`, shared registries in `optimizers/`, or when focused tests pass but behavior still looks suspicious.
- When modifying optimizer or controller logic, run the specific test file first. Only run the full suite if the change clearly reaches beyond that file's scope or if you cannot convince yourself the blast radius is contained.

Current maintained test areas are:

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
  - `AGENTS.md` when repository guidance changes
- Keep active docs aligned with implemented reality.
- Treat `AGENTS.md` as the single authoritative repository guidance file.

## Useful References

- `README.md`
- `AGENTS.md`
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
- `optimizers/artifacts.py`
- `optimizers/render_assets.py`
- `optimizers/compare_runs.py`
- `optimizers/run_manifest.py`
- `optimizers/analytics/` (decisions, loaders, pareto, rollups)
- `optimizers/traces/` (jsonl_writer, operator_trace, correlation, prompt_store)
- `visualization/figures/` (pareto, temperature_field, gradient_field, hypervolume, layout_evolution, operator_heatmap)
- `visualization/style/baseline.py`
- `scripts/smoke_render_assets.sh`
- `llm/openai_compatible/client.py`
- `llm/openai_compatible/profiles.yaml`
- `tests/optimizers/test_raw_driver_matrix.py`
- `tests/optimizers/test_repair.py`
- `tests/optimizers/test_representative_layout.py`
- `tests/optimizers/test_multi_seed_layout.py`
- `tests/visualization/test_render_assets_fixtures.py`
