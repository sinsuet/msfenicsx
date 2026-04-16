# s1_typical Multi-Scenario Validation Design

> Status: approved design for extending `s1_typical` from a fixed single-case benchmark into a multi-scenario × multi-optimizer-seed validation matrix.

## 1. Context

The active paper-facing mainline on `main` is `s1_typical` with three optimizer modes:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

A pilot run at [scenario_runs/s1_typical/0416_0224__llm](../../../scenario_runs/s1_typical/0416_0224__llm) showed `nsga2_llm` beating `nsga2_raw` and `nsga2_union` on a single scenario (benchmark_seed=11, algorithm.seed=7). The goal now is to validate that this advantage is not a single-run artifact, across different initial component layouts and different optimizer search seeds, while keeping the physics (15 components, per-component power, geometry, boundary conditions) fixed.

Two independent seed concepts exist in the codebase:

- **Scenario seed** (`benchmark_source.seed`) — passed to `core.generator.pipeline.generate_case`, drives `place_components()` in [core/generator/layout_engine.py:55](../../../core/generator/layout_engine.py#L55). In the `s1_typical` template this degenerates to affecting only the initial component `(x, y)` positions because all other sampled fields (count, geometry, power, rotation, sink parameters) have `min == max` ranges.
- **Optimizer seed** (`algorithm.seed`) — passed to `pymoo.minimize`, drives initial population sampling, SBX crossover RNG, and PM mutation RNG. Does not touch the case YAML.

A critical observation underpins this design: the NSGA-II backbone at [optimizers/raw_backbones/nsga2.py:19-23](../../../optimizers/raw_backbones/nsga2.py#L19-L23) constructs `NSGA2(pop_size=..., crossover=..., mutation=...)` without a `sampling=` argument, so pymoo uses the default `FloatRandomSampling`. The initial case layout positions are consumed only by `evaluate_baseline()` in [optimizers/problem.py:78-81](../../../optimizers/problem.py#L78-L81) as a single reference evaluation — they are **not** injected into the NSGA-II initial population. Consequently, varying `benchmark_source.seed` alone in `s1_typical` today produces optimization problems that are effectively identical in the search space seen by the optimizer; only the baseline reference value differs. A meaningful multi-scenario experiment therefore requires injecting each scenario's layout into the initial population.

## 2. Problem Statement

Validate the following claims on `s1_typical` with a 3 × 3 × 3 experimental matrix of scenarios × optimizer seeds × modes, while keeping the benchmark's physical identity fixed:

1. `nsga2_llm` has higher mean Hypervolume (HV) than `nsga2_raw` and `nsga2_union` across different initial layouts (cross-layout robustness).
2. `nsga2_llm` achieves this at HV variance comparable to or lower than the other two modes across different NSGA-II search seeds (search stability).
3. `nsga2_llm` produces equal-or-better single-objective extreme points (best `summary.temperature_max`, best `summary.temperature_gradient_rms`) on the majority of scenarios.

## 3. Design Goals

- Keep the paper-facing benchmark identity of `s1_typical` intact: 15 components, fixed per-component power, fixed geometry, fixed boundary conditions.
- Make the only cross-scenario difference be the initial component layout.
- Ensure that initial layout variation actually reaches the optimizer by injecting the layout into the NSGA-II initial population.
- Apply the injection uniformly to all three modes so the comparison stays fair.
- Produce a single unified run directory containing all 27 runs plus a cross-mode / cross-scenario comparison artifact tree.
- Keep credentials and provider identity orthogonal to this design — the accompanying provider-profile-switching work handles model selection at the CLI layer.

## 4. Non-Goals

- No changes to component count, per-component power, geometry, or boundary conditions.
- No new benchmark identifier; `s1_typical` is extended in place.
- No changes to LLM controller semantics, operator pool, repair, or cheap constraints.
- No larger-budget ablation in this design (pop=32/gen=16 stays a pilot artifact).
- No per-provider optimization specs; provider identity is resolved at CLI invocation via the provider-profile-switching CLI.
- No alternate paper-facing spec names such as `s1_typical_multi_*`.
- No revival of retired hot/cold benchmark assets.

## 5. Experimental Matrix

| Dimension           | Values            | Notes                                                                                                               |
|---------------------|-------------------|---------------------------------------------------------------------------------------------------------------------|
| Scenario seed       | `{11, 42, 123}`   | `11` carries over from the `0416_0224__llm` pilot; `42` and `123` are standard diversified seeds.                   |
| Optimizer seed      | `{7, 13, 29}`     | `7` carries over from current specs; `13` and `29` are added.                                                       |
| Mode                | `{raw, union, llm}` | Uses the three paper-facing optimization specs.                                                                   |
| Total runs          | 3 × 3 × 3 = 27    |                                                                                                                     |
| Population size     | 20                | Permanent default for `s1_typical`, down from 32.                                                                   |
| Number of generations | 10              | Permanent default for `s1_typical`, down from 16.                                                                   |
| Evaluation workers  | 2                 | Conservative daytime concurrency per CLAUDE.md guidance.                                                            |
| Execution entry point | single `run-benchmark-suite` invocation | Produces one unified run directory.                                                                |

The budget reduction to `pop=20 × gen=10` is a permanent change to the paper-facing `s1_typical` identity. Absolute HV values will be lower than the pilot run; this is accepted because `nsga2_llm`'s expected advantage is sample efficiency, which shows more clearly at smaller budgets. All three modes share the budget change, so inter-mode comparisons remain fair.

The `0416_0224__llm` pilot is preserved as-is for reference but is not numerically compared against new runs; only the qualitative claim (`llm` beats `raw`/`union` on one scenario at a larger budget) carries over as prior evidence.

## 6. Initial Layout Injection

### 6.1 Strategy

Each scenario's generated `case.yaml` produces a decision vector `v_seed = extract_decision_vector(base_case, optimization_spec)` of length 32. The NSGA-II initial population (size `pop_size = 20`) is constructed as:

- Sample index `0`: exactly `v_seed` (unperturbed).
- Sample indices `1..pop_size-1`: `v_seed + N(0, jitter_scale × span)`, clipped to `[problem.xl, problem.xu]`.

Here `span = problem.xu - problem.xl` is the per-variable bound width, and `jitter_scale` is a repo-wide scalar.

### 6.2 Default and configuration

- `jitter_scale` default: `0.05` (5% of per-variable bound width). This value is small enough that the initial population stays in the neighbourhood of `v_seed`, so cross-scenario differences survive, and large enough that NSGA-II's first generations see real diversity.
- Stored under `optimizers/algorithm_config.py` as a repo-wide default; not repeated in paper-facing specs.
- Overridable through `algorithm.parameters.initial_population.jitter_scale` for future exploratory runs; this experiment uses the default only.

### 6.3 Sampling RNG

A new `InjectedLayoutSampling` subclass of `pymoo.core.sampling.Sampling` performs the construction above. Its own RNG is derived deterministically from the optimizer seed and scenario seed as `rng_seed = algorithm.seed * 7919 + scenario_seed`, so the sampled population is reproducible given `(algorithm.seed, scenario_seed)` even though it is independent of pymoo's internal RNG.

### 6.4 Mode coverage

`InjectedLayoutSampling` is attached to the NSGA-II algorithm object in both `optimizers/drivers/raw_driver.py` and `optimizers/drivers/union_driver.py`. Because `llm` reuses `union_driver`, all three modes share the same initial population construction. Operator pool actions and the LLM controller act only on generations `>= 1`, so initial-population construction is strictly upstream of mode-specific behavior.

### 6.5 Constraint handling

Jittered samples may violate the hard `case.total_radiator_span <= radiator_span_max` constraint or component clearance. The existing repair path in `optimizers/repair.py` applies inside `problem._evaluate` before each evaluation and projects vectors back to legality; no change is required there. The `generation_summary.jsonl` already records `n_infeasible_after_repair`, which is the observability hook for diagnosing excessive infeasibility in generation 0.

### 6.6 Tests

A new test module `tests/optimizers/test_initial_population.py` covers:

- Reproducibility: same `(base_case, algorithm.seed, scenario_seed)` yields identical samples.
- Anchor invariant: sample `0` equals `extract_decision_vector(base_case, spec)` exactly.
- Boundedness: every sample satisfies `xl <= x <= xu`.
- Jitter statistics: empirical standard deviation across many samples is within a tolerance of `jitter_scale × span`.

## 7. Infrastructure Changes

### 7.1 CLI and suite driver

`optimizers/cli.py`: `run-benchmark-suite` gains a repeatable flag `--algorithm-seeds`. If omitted, the single `algorithm.seed` from each spec is used, preserving backward compatibility.

`optimizers/run_suite.py`:

- Add parameter `algorithm_seeds: list[int]` to `run_benchmark_suite`.
- Remove the `s1_typical`-specific branch of `_validate_benchmark_seed_policy` that forbids more than one `benchmark_seed`. Leave other neutral validation (uniqueness, non-empty) intact.
- Add inner loop `for aseed in (algorithm_seeds or [spec.algorithm.seed]):` nested under the existing scenario-seed loop.
- For each `(mode, benchmark_seed, algorithm_seed)` combination, apply a helper analogous to the existing `_with_benchmark_seed` that also overrides `algorithm.seed` on the copied spec.
- Artifact write path changes from `.../<mode>/seeds/seed-<N>/...` to `.../<mode>/seeds/seed-<N>/opt-<M>/...`. Every downstream artifact (case.yaml, solution.yaml, optimization_result.json, pareto_front.json, generation_summary.jsonl, evaluation_events.jsonl, controller_trace.json, operator_trace.json, llm_request_trace.jsonl, llm_response_trace.jsonl, llm_metrics.json, representatives/) sits inside `opt-<M>/`.

Consumers of `seeds/seed-<N>/` need to be updated for the new layer. Identified consumers:

- `optimizers/artifacts.py`
- `optimizers/run_layout.py`
- Anything under `visualization/` that walks representative bundles.

A new test module `tests/optimizers/test_run_suite_multi_seed.py` exercises a small matrix (2 scenario × 2 optimizer seed × 2 mode) and asserts directory layout, manifest shape, and that every run directory contains the expected artifact set.

### 7.2 Run identifier

The run slug follows the existing convention in CLAUDE.md: `<MMDD_HHMM>__raw__union__llm` with modes in the fixed order `raw, union, llm`. No new naming surface.

### 7.3 Permanent defaults

The three paper-facing optimization specs at `scenarios/optimization/s1_typical_{raw,union,llm}.yaml` are updated:

- `algorithm.population_size: 20`
- `algorithm.num_generations: 10`

Profile files under `scenarios/optimization/profiles/s1_typical_{raw,union}.yaml` are scanned for any `pop_size` / `num_generations` override that would conflict and aligned if needed.

## 8. Comparison Methodology

### 8.1 Metrics

- **Primary**: Hypervolume (HV), computed on each run's final Pareto front using a single globally-shared reference point.
- **Secondary**: best `summary.temperature_max` and best `summary.temperature_gradient_rms` on the final Pareto front (per-run scalars).
- **Tertiary**: Pareto dominance count between `llm` and each other mode within the same `(scenario_seed, algorithm_seed)` cell.

### 8.2 HV reference point

The reference point is derived from the 3 scenarios' baseline evaluations (the initial `case.yaml` layout evaluated once per scenario via `evaluate_baseline`) as

```
hv_reference_point = (max_scenarios(T_max_baseline) × 1.10, max_scenarios(grad_rms_baseline) × 1.10)
```

Rationale: a single global reference point makes HV values comparable across all 27 cells. The 10% margin guards against Pareto points lying slightly above the baseline for pathological initial layouts. The computed tuple is written to `comparison/summary.json` under `hv_reference_point` for reproducibility.

### 8.3 Comparison artifacts

All under `<run_id>/comparison/`:

| File                          | Content                                                                                                            |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `summary.json`                | 27 rows, fields: `mode, scenario_seed, opt_seed, HV, best_T_max, best_grad_rms, n_pareto_points, converged_at_gen`, plus the `hv_reference_point` tuple. |
| `per_mode_aggregate.json`     | For each mode (n=9 samples): HV mean, median, std; best `T_max` mean and std; best `grad_rms` mean and std; paired Wilcoxon signed-rank p-value for `llm` vs `raw` and `llm` vs `union` (informational). |
| `per_scenario_table.md`       | 3 × 3 markdown table. Rows = scenario seed, columns = mode, cell = `HV mean ± std` over the 3 optimizer seeds.     |
| `win_rate_table.md`           | Count of `(scenario, opt_seed)` cells where `llm` beats each opponent on HV, best `T_max`, best `grad_rms` (9 cells per opponent per metric). |
| `figures/hv_bar.svg`          | 3 subplots (one per scenario seed), each with 3 bars and error bars (std across optimizer seeds).                  |
| `figures/pareto_overlay.svg`  | 3 subplots, each overlaying the 3 modes' Pareto fronts for that scenario, pooling the 3 optimizer-seed runs per mode. |
| `pages/index.html`            | HTML stitching together the tables and figures.                                                                    |

### 8.4 Statistical framing

With `n = 9` samples per mode, frequentist significance is weak. The Wilcoxon signed-rank test on the 9 paired HV differences is reported as an informational statistic, not a claim-critical test. The paper-facing claims rely on mean, win rate, and per-scenario breakdown. The written report must call out any case in which one of the four validation claims (cross-layout mean, cross-layout win count, per-cell win rate, single-objective extreme) fails, rather than cherry-picking the successful axes.

### 8.5 Implementation boundary

A new `optimizers/comparison/` package ingests the per-run artifacts produced by `run_benchmark_suite` and writes the `comparison/` tree. HV computation uses `pymoo.indicators.hv.Hypervolume` to avoid depending on the `logging-visualization-refactor` branch's analytics module, which is still in progress on a worktree. If that refactor lands later, the comparison layer can be re-pointed at its analytics API without changing the artifact contract.

Tests: `tests/optimizers/test_comparison_summary.py` constructs a synthetic mini-matrix of results, runs the comparison builder, and asserts schema correctness and numeric invariants (HV non-negative, `n_pareto_points > 0`, monotone agreement of win rate and per-scenario table).

## 9. Artifact Layout

```
scenario_runs/s1_typical/<MMDD_HHMM>__raw__union__llm/
├── manifest.json
├── shared/
│   ├── scenario_template.yaml
│   ├── evaluation_spec.yaml
│   ├── optimization_spec_raw.yaml
│   ├── optimization_spec_union.yaml
│   └── optimization_spec_llm.yaml
├── raw/
│   ├── manifest.json
│   └── seeds/
│       ├── seed-11/opt-7/...
│       ├── seed-11/opt-13/...
│       ├── seed-11/opt-29/...
│       ├── seed-42/opt-7/...
│       ├── seed-42/opt-13/...
│       ├── seed-42/opt-29/...
│       ├── seed-123/opt-7/...
│       ├── seed-123/opt-13/...
│       └── seed-123/opt-29/...
├── union/
│   └── seeds/ (same 9 subdirectories)
├── llm/
│   └── seeds/ (same 9 subdirectories, each also containing llm_request_trace.jsonl, llm_response_trace.jsonl, llm_metrics.json)
└── comparison/
    ├── summary.json
    ├── per_mode_aggregate.json
    ├── per_scenario_table.md
    ├── win_rate_table.md
    ├── figures/
    │   ├── hv_bar.svg
    │   └── pareto_overlay.svg
    └── pages/
        └── index.html
```

The only breaking change relative to today's layout is the additional `opt-<M>/` directory below each `seed-<N>/`. Per-run artifact file names are unchanged.

## 10. Policy and Documentation Updates

| File                                                            | Change                                                                                                                                                                                                                                                      |
|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CLAUDE.md`                                                     | Replace the `s1_typical is a fixed single-case benchmark; do not use multiple benchmark seeds to simulate multiple problem instances` guidance with: `s1_typical has fixed physics (15 components, per-component power, geometry, boundary conditions); multiple benchmark_seeds are permitted specifically to produce different initial layouts for cross-layout robustness validation`. Update the artifact path section to include the `seed-<N>/opt-<M>/` sublayer. |
| `AGENTS.md`                                                     | Mirror the two CLAUDE.md updates above so the Codex and Claude Code guidance stay in sync.                                                                                                                                                                  |
| `README.md`                                                     | If any section describes `s1_typical` as single-seed, tighten wording to match the updated policy.                                                                                                                                                          |
| `optimizers/algorithm_config.py`                                | Add `initial_population.jitter_scale: 0.05` as a repo-wide default.                                                                                                                                                                                          |
| `scenarios/optimization/s1_typical_{raw,union,llm}.yaml`        | Set `algorithm.population_size: 20` and `algorithm.num_generations: 10`.                                                                                                                                                                                     |
| `scenarios/optimization/profiles/s1_typical_{raw,union}.yaml`   | If any `pop_size` / `num_generations` override exists, align to the new defaults.                                                                                                                                                                            |
| `optimizers/run_suite.py`                                       | Remove the `s1_typical` branch of `_validate_benchmark_seed_policy`; add `algorithm_seeds` parameter; add inner loop; update artifact paths.                                                                                                                 |
| `optimizers/cli.py`                                             | Add repeatable `--algorithm-seeds` flag on `run-benchmark-suite`.                                                                                                                                                                                            |
| `optimizers/drivers/raw_driver.py`, `optimizers/drivers/union_driver.py` | Construct `InjectedLayoutSampling` and pass as `sampling=` to the NSGA-II algorithm.                                                                                                                                                                  |
| `optimizers/initial_population.py` (new)                        | Implement `InjectedLayoutSampling`.                                                                                                                                                                                                                          |
| `optimizers/comparison/` (new package)                          | Implement the comparison builder that consumes per-run artifacts and writes `comparison/*`.                                                                                                                                                                  |
| `optimizers/artifacts.py`, `optimizers/run_layout.py`, `visualization/*` | Update all consumers of the `seeds/seed-<N>/` path to the new `seeds/seed-<N>/opt-<M>/` layout.                                                                                                                                                    |

## 11. Risks and Mitigations

| Risk                                                                                     | Impact                                                                 | Mitigation                                                                                                                        |
|------------------------------------------------------------------------------------------|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| R1. Injection protocol shifts absolute HV for all modes.                                 | New runs not directly comparable to the `0416_0224__llm` pilot.        | Mark the pilot as reference only; the new run's inter-mode comparison is fair because all three modes share the same sampling.    |
| R2. `jitter_scale = 0.05` is empirical; may be too tight or too loose.                   | Cross-scenario signal could be diluted or lost.                        | Sanity-check: after first run, inspect initial-population overlap across scenarios; the default is parameterized for easy tuning. |
| R3. Jittered samples violate the `radiator_span` hard constraint, forcing many repairs.  | Effective diversity in generation 0 may drop.                          | `generation_summary.jsonl` already records `n_infeasible_after_repair`; if spikes, restrict jitter to component `x, y` variables and leave `sink_start, sink_end` unperturbed. |
| R4. The new `opt-<M>/` sublayer can break visualization and representative scanners.     | Report generation fails on existing tooling.                           | Enumerate consumers (`optimizers/artifacts.py`, `optimizers/run_layout.py`, `visualization/`) and update them under PR-A; add directory-layout tests.                                        |
| R5. `.claude/worktrees/logging-viz-refactor/` modifies `analytics/pareto.py`.            | Merge conflicts with comparison layer.                                 | Keep comparison self-contained on `pymoo.indicators.hv`; once the refactor lands, re-point the comparison layer to its analytics API without changing the artifact contract. |
| R6. 27 runs exceed 6 hours because of LLM API variability.                               | Overnight execution; mid-run failure is hard to recover from.          | `run-benchmark-suite` writes each `(mode, bseed, aseed)` to an independent directory, so resuming is straightforward; run `raw` and `union` first, then `llm`, so API-independent work is safe early. |
| R7. Sampling RNG independent from pymoo RNG may introduce reproducibility drift.         | Same `algorithm.seed` no longer fully determines the trajectory.       | Derive sampling `rng_seed = algorithm.seed * 7919 + scenario_seed` deterministically; both seeds are recorded in per-run manifest. |
| R8. Future provider-profile-switching will change LLM results.                           | Cross-provider comparisons won't align with this run.                  | Record the exact `model` id in each run's manifest; the provider-profile-switching design already lists multi-model reruns as a follow-up.              |

## 12. Execution Plan

Implementation lands in three reviewable pull requests so each step has a focused change set and an independent test surface.

### 12.1 PR-A — Suite driver and documentation

- `optimizers/cli.py`: add `--algorithm-seeds`.
- `optimizers/run_suite.py`: drop the `s1_typical` single-seed guardrail; add `algorithm_seeds` parameter; add inner optimizer-seed loop; adopt the `seeds/seed-<N>/opt-<M>/` layout.
- `optimizers/artifacts.py`, `optimizers/run_layout.py`, and `visualization/*` consumers: updated to the new path.
- `CLAUDE.md`, `AGENTS.md`, and `README.md`: synchronized policy text.
- New test: `tests/optimizers/test_run_suite_multi_seed.py`.

### 12.2 PR-B — Initial layout injection and budget update

- `optimizers/initial_population.py`: new `InjectedLayoutSampling`.
- `optimizers/drivers/raw_driver.py` and `optimizers/drivers/union_driver.py`: wire the sampling in.
- `optimizers/algorithm_config.py`: default `initial_population.jitter_scale = 0.05`.
- `scenarios/optimization/s1_typical_{raw,union,llm}.yaml`: budget reduced to `pop=20`, `gen=10`.
- `scenarios/optimization/profiles/s1_typical_{raw,union}.yaml`: aligned if needed.
- New test: `tests/optimizers/test_initial_population.py`.

### 12.3 PR-C — Comparison artifacts

- `optimizers/comparison/` package: `summary.json` builder, `per_mode_aggregate.json`, `per_scenario_table.md`, `win_rate_table.md`, HV figures, HTML index.
- `run_benchmark_suite` end-of-run hook that invokes the comparison builder.
- New test: `tests/optimizers/test_comparison_summary.py`.

### 12.4 Smoke and full run

After PR-A and PR-B land on `main`, run a 5-minute smoke with 3 scenarios × 2 optimizer seeds × `raw` only to verify the new layout and injection behaviour end-to-end. Once PR-C lands, execute the full 27-run suite:

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --mode raw --mode union --mode llm \
  --benchmark-seed 11 --benchmark-seed 42 --benchmark-seed 123 \
  --algorithm-seeds 7 --algorithm-seeds 13 --algorithm-seeds 29 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

The accompanying provider-profile-switching work is expected to land first; the full LLM run uses the default `gpt` profile.

## 13. Validation

The four binary pass/fail thresholds below are a refinement of the paper claims in §2. Claims 1 and 4 of §2 map to thresholds 1, 2, 3, and 4 below. Claim 2 of §2 (HV variance stability) is treated as a descriptive statistic rather than a binary threshold because variance comparison lacks a natural pass/fail cut at `n = 3` samples per scenario; its numeric value is reported in `per_mode_aggregate.json` (std field) and in `per_scenario_table.md` (the `± std` in each cell).

The experiment's own success criteria are evaluated post-run from `comparison/`:

- **Claim 1 (cross-layout mean)**: `llm` HV mean > `raw` and > `union` across all 9 samples.
- **Claim 2 (cross-layout win count)**: `llm` HV mean > opponent mean in at least 2 of 3 scenarios.
- **Claim 3 (per-cell win rate)**: `llm` wins in at least 5 of 9 `(scenario, opt_seed)` cells on HV against each opponent.
- **Claim 4 (single-objective extremes)**: best `T_max` and best `grad_rms` on `llm` Pareto fronts at least tie per scenario on 2 of 3 scenarios.

If any claim fails, the progress report documents the failure explicitly with per-scenario breakdown rather than aggregating it away.

## 14. Useful References

- [CLAUDE.md](../../../CLAUDE.md)
- [AGENTS.md](../../../AGENTS.md)
- [README.md](../../../README.md)
- [docs/superpowers/specs/2026-04-15-openai-compatible-provider-profile-switching-design.md](2026-04-15-openai-compatible-provider-profile-switching-design.md)
- [scenarios/templates/s1_typical.yaml](../../../scenarios/templates/s1_typical.yaml)
- [scenarios/evaluation/s1_typical_eval.yaml](../../../scenarios/evaluation/s1_typical_eval.yaml)
- [scenarios/optimization/s1_typical_raw.yaml](../../../scenarios/optimization/s1_typical_raw.yaml)
- [scenarios/optimization/s1_typical_union.yaml](../../../scenarios/optimization/s1_typical_union.yaml)
- [scenarios/optimization/s1_typical_llm.yaml](../../../scenarios/optimization/s1_typical_llm.yaml)
- [optimizers/run_suite.py](../../../optimizers/run_suite.py)
- [optimizers/drivers/raw_driver.py](../../../optimizers/drivers/raw_driver.py)
- [optimizers/drivers/union_driver.py](../../../optimizers/drivers/union_driver.py)
- [optimizers/raw_backbones/nsga2.py](../../../optimizers/raw_backbones/nsga2.py)
- [optimizers/problem.py](../../../optimizers/problem.py)
- [core/generator/layout_engine.py](../../../core/generator/layout_engine.py)
- [core/generator/pipeline.py](../../../core/generator/pipeline.py)
- [scenario_runs/s1_typical/0416_0224__llm/](../../../scenario_runs/s1_typical/0416_0224__llm/)
