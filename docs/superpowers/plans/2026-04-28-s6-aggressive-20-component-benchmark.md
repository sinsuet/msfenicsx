# S6 Aggressive 20-Component Benchmark Implementation Plan

> **For agentic workers:** This plan depends on the shared `primitive_structured` operator-pool plan and should start after S5 has passed its first calibration loop. Do not edit operator implementation files here.

**Goal:** Add `s6_aggressive20` as a denser 20-component aggressive benchmark using the shared `primitive_structured` pool.

**Architecture:** Create a 42-variable single-case benchmark under `scenarios/`, with matched raw / union / llm optimization specs. S6 should raise density and multi-bottleneck thermal pressure relative to S5 while preserving feasibility and the shared-pool comparison contract.

**Spec:** [docs/superpowers/specs/2026-04-28-s6-aggressive-20-component-benchmark-design.md](../specs/2026-04-28-s6-aggressive-20-component-benchmark-design.md)

---

## Dependencies

Complete first:

- [docs/superpowers/plans/2026-04-28-primitive-structured-operator-pool.md](2026-04-28-primitive-structured-operator-pool.md)
- [docs/superpowers/plans/2026-04-28-s5-aggressive-15-component-benchmark.md](2026-04-28-s5-aggressive-15-component-benchmark.md) first calibration loop

This plan should reuse the same shared pool and should not modify operator code.

---

## File Map

Create:

- `scenarios/templates/s6_aggressive20.yaml`
- `scenarios/evaluation/s6_aggressive20_eval.yaml`
- `scenarios/optimization/s6_aggressive20_raw.yaml`
- `scenarios/optimization/s6_aggressive20_union.yaml`
- `scenarios/optimization/s6_aggressive20_llm.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_raw.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_union.yaml`
- `tests/schema/test_s6_aggressive20_template.py`
- `tests/generator/test_s6_aggressive20_template.py`
- `tests/optimizers/test_s6_aggressive20_specs.py`

Modify after validation only:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md` if repository guidance should list S6

Do not modify:

- optimizer operator code
- LLM controller code
- generated run artifacts by hand

---

## Task 1: Add Template Contract Tests

- [ ] Create `tests/schema/test_s6_aggressive20_template.py`.
- [ ] Assert template id `s6_aggressive20`.
- [ ] Assert exactly 20 component families and 20 load rules.
- [ ] Assert families are named `c01` through `c20`.
- [ ] Assert single top-edge line sink.
- [ ] Assert no `operating_case_profiles`.
- [ ] Assert total power is in the `155-166 W` target band.
- [ ] Assert placement region matches the S6 scale target.
- [ ] Assert all components have placement hints, layout tags, and clearance.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/schema/test_s6_aggressive20_template.py
```

Expected before template creation: fail because the file does not exist.

---

## Task 2: Create The S6 Template

- [ ] Start from validated S5 if available; otherwise start from S2 and apply S6 changes directly.
- [ ] Save as `scenarios/templates/s6_aggressive20.yaml`.
- [ ] Set template id and description to S6.
- [ ] Set placement region approximately:
  - `x_min: 0.05`
  - `x_max: 0.95`
  - `y_min: 0.04`
  - `y_max: 0.73`
- [ ] Keep one top-edge sink.
- [ ] Set raw sink span about `0.44-0.46`.
- [ ] Target evaluation budget around `0.36` in the evaluation spec.
- [ ] Set total power to `155-166 W`.
- [ ] Use 20 fixed components named `c01..c20`.
- [ ] Structure roles as:
  - `c01-c05`: primary hot cluster and support
  - `c06-c10`: secondary hot lane and buffers
  - `c11-c15`: center/routing pressure
  - `c16-c20`: lower/edge/service modules

Avoid making all added components high-power; preserve semantic variety.

---

## Task 3: Add Generator Tests

- [ ] Create `tests/generator/test_s6_aggressive20_template.py`.
- [ ] Generate seed 11.
- [ ] Assert generated case has 20 components.
- [ ] Assert generated sink exists and has expected top-edge shape.
- [ ] Assert generated layout is legal under existing geometry checks.
- [ ] Assert total generated load matches the template target.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/generator/test_s6_aggressive20_template.py
```

---

## Task 4: Add Evaluation Spec

- [ ] Create `scenarios/evaluation/s6_aggressive20_eval.yaml`.
- [ ] Keep objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- [ ] Add radiator span budget around `0.36`.
- [ ] Add peak constraints for the main thermal core.
- [ ] Add one or two peak constraints for secondary-lane components.
- [ ] Add spread constraint only if first calibration shows thermal balance is too loose.

Do not over-constrain S6; the target is thermal layout optimization, not a constraint wall.

---

## Task 5: Add Optimization Specs And Profiles

- [ ] Create raw, union, and llm optimization specs under `scenarios/optimization/`.
- [ ] Create raw and union profiles under `scenarios/optimization/profiles/`.
- [ ] Use 42 variables:
  - `c01_x/c01_y` through `c20_x/c20_y`
  - `sink_start`
  - `sink_end`
- [ ] Ensure all three specs reference `scenarios/evaluation/s6_aggressive20_eval.yaml`.
- [ ] Union and llm both use `registry_profile: primitive_structured`.
- [ ] LLM provider settings follow current GPT route conventions.
- [ ] Budgets should initially match S5 smoke settings unless calibration proves S6 needs a larger first read.

---

## Task 6: Add Optimization Spec Tests

- [ ] Create `tests/optimizers/test_s6_aggressive20_specs.py`.
- [ ] Assert all three specs load.
- [ ] Assert variable ids match across raw / union / llm.
- [ ] Assert the variable count is 42.
- [ ] Assert union and llm use `primitive_structured`.
- [ ] Assert raw stays native-only.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_s6_aggressive20_specs.py
```

---

## Task 7: Validate, Generate, Solve, Evaluate

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s6_aggressive20.yaml
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s6_aggressive20.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s6_aggressive20/seed-11
```

Then solve/evaluate the generated case with the S6 evaluation spec.

If most problems are geometry-related, reduce density or clearance pressure before changing optimizer logic.

---

## Task 8: Smoke Benchmark

After focused validation, run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s6_aggressive20_raw.yaml \
  --optimization-spec scenarios/optimization/s6_aggressive20_union.yaml \
  --optimization-spec scenarios/optimization/s6_aggressive20_llm.yaml \
  --mode raw --mode union --mode llm \
  --llm-profile default \
  --benchmark-seed 11 \
  --population-size 10 \
  --num-generations 5 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

Render assets and create comparison output before claiming benchmark behavior.

---

## Task 9: Calibration Decision

After smoke:

- [ ] If no mode reaches feasible candidates, loosen constraints or reduce density.
- [ ] If raw still dominates too easily, increase multi-bottleneck thermal pressure or structured-move relevance.
- [ ] If union beats llm by random structured moves, inspect operator-selection traces before changing the benchmark.
- [ ] If llm collapses to one operator, inspect prompt metadata and generation-local guidance.

Keep S6 changes confined to S6 files unless the evidence proves a shared pool problem.
