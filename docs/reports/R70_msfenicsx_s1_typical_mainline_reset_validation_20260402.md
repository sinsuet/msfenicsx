# R70 msfenicsx S1 Typical Mainline Reset Validation

Date: 2026-04-02

## Scope

This report records the validation evidence for the `s1_typical` mainline reset implemented from:

- `docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md`
- `docs/superpowers/plans/2026-04-02-s1-typical-mainline-reset.md`

The repository is now validated against the approved active mainline:

- template id: `s1_typical`
- one operating case
- `15` components
- `x/y`-only decision control
- no optimized rotation
- `32` decision variables
- objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard sink-budget constraint:
  - `case.total_radiator_span <= radiator_span_max`
- cheap legality checks before PDE
- projection plus local legality restoration repair
- semantic shared operator registry for `nsga2_union` and `nsga2_llm`

## Repository Cleanup Outcome

The reset removed the retired four-component hot/cold paper-facing assets from active repository use:

- deleted retired `panel_four_component_hot_cold*` scenario template, evaluation spec, optimization specs, and profiles
- deleted retired hot/cold mainline specs and plans under `docs/superpowers/`
- rewrote `README.md` and `AGENTS.md` so `s1_typical` is the only active paper-facing mainline
- rewrote legacy tests that still enforced the paired hot/cold path
- removed the legacy `operating_case_profiles` contract from active single-case schema usage

## Verification Evidence

### 1. Main Test Suite

Command:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema \
  tests/generator \
  tests/solver \
  tests/evaluation \
  tests/optimizers -v
```

Result:

- exit code `0`
- `129 passed in 47.79s`

### 2. Template Validation

Command:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template \
  --template scenarios/templates/s1_typical.yaml
```

Result:

- exit code `0`

Validated input:

- `scenarios/templates/s1_typical.yaml`

### 3. Single-Case Generation

Command:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case \
  --template scenarios/templates/s1_typical.yaml \
  --seed 11 \
  --output-root ./scenario_runs/generated_cases/s1_typical/seed-11
```

Result:

- exit code `0`

Generated artifact:

- `scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml`

### 4. Raw Optimization Smoke

Command:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --output-root ./scenario_runs/optimizations/s1_typical/raw-smoke
```

Result:

- exit code `0`

Manifest-backed bundle:

- root: `scenario_runs/optimizations/s1_typical/raw-smoke/`
- manifest: `scenario_runs/optimizations/s1_typical/raw-smoke/manifest.json`
- optimization result: `scenario_runs/optimizations/s1_typical/raw-smoke/optimization_result.json`
- Pareto front: `scenario_runs/optimizations/s1_typical/raw-smoke/pareto_front.json`
- evaluation sidecar: `scenario_runs/optimizations/s1_typical/raw-smoke/evaluation_events.jsonl`
- generation sidecar: `scenario_runs/optimizations/s1_typical/raw-smoke/generation_summary.jsonl`

Representative bundles written:

- `scenario_runs/optimizations/s1_typical/raw-smoke/representatives/knee-candidate/`
- `scenario_runs/optimizations/s1_typical/raw-smoke/representatives/min-peak-temperature/`
- `scenario_runs/optimizations/s1_typical/raw-smoke/representatives/min-temperature-gradient-rms/`

Manifest metadata observed:

- `run_id = s1_typical_nsga2_raw-b11-a7-run`
- `optimization_spec_id = s1_typical_nsga2_raw`
- `evaluation_spec_id = s1_typical_eval`
- `mode_id = nsga2_raw`
- `benchmark_seed = 11`

### 5. Diff Hygiene

Command:

```bash
git diff --check
```

Result:

- exit code `0`
- no whitespace or patch-format errors reported

## Active Mainline Inputs After Reset

- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/profiles/s1_typical_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_union.yaml`

## Conclusion

The repository now has fresh evidence for:

- single-case `s1_typical` template validation
- deterministic single-case generation on seed `11`
- solver/evaluation/optimizer test coverage aligned with the new contract
- end-to-end `nsga2_raw` smoke execution writing manifest-backed artifacts
- removal of the retired paper-facing hot/cold mainline inputs from active repository use
