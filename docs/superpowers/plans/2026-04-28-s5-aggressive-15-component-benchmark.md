# S5 Aggressive 15-Component Benchmark Implementation Plan

> **For agentic workers:** This benchmark plan depends on the shared `primitive_structured` operator-pool plan. Do not edit operator implementation files here.

**Goal:** Add `s5_aggressive15` as the first aggressive 15-component benchmark using the shared `primitive_structured` pool.

**Architecture:** Create hand-authored scenario inputs under `scenarios/`, focused tests under `tests/`, and matched raw / union / llm optimization specs. Keep S5 as a single-case, 32-variable benchmark. Calibrate thermal constraints from generated seed-11 behavior rather than hardcoding a desired winner.

**Spec:** [docs/superpowers/specs/2026-04-28-s5-aggressive-15-component-benchmark-design.md](../specs/2026-04-28-s5-aggressive-15-component-benchmark-design.md)

---

## Dependency

Complete first:

- [docs/superpowers/plans/2026-04-28-primitive-structured-operator-pool.md](2026-04-28-primitive-structured-operator-pool.md)

This plan may reference `registry_profile: primitive_structured`, but it must not implement it.

---

## File Map

Create:

- `scenarios/templates/s5_aggressive15.yaml`
- `scenarios/evaluation/s5_aggressive15_eval.yaml`
- `scenarios/optimization/s5_aggressive15_raw.yaml`
- `scenarios/optimization/s5_aggressive15_union.yaml`
- `scenarios/optimization/s5_aggressive15_llm.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_raw.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_union.yaml`
- `tests/schema/test_s5_aggressive15_template.py`
- `tests/generator/test_s5_aggressive15_template.py`
- `tests/optimizers/test_s5_aggressive15_specs.py`

Modify after validation only:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md` if repository guidance needs the new benchmark listed

Do not modify:

- `optimizers/operator_pool/operators.py`
- `optimizers/operator_pool/primitive_registry.py`
- `optimizers/operator_pool/llm_controller.py`

---

## Task 1: Add Template Contract Tests

- [ ] Create `tests/schema/test_s5_aggressive15_template.py`.
- [ ] Assert the template exists and has id `s5_aggressive15`.
- [ ] Assert exactly 15 component families and 15 load rules.
- [ ] Assert families are named `c01` through `c15`.
- [ ] Assert there is one top-edge line sink.
- [ ] Assert no `operating_case_profiles` key exists.
- [ ] Assert all components have fixed count 1.
- [ ] Assert all components declare `placement_hint`, `layout_tags`, and nonzero clearance.
- [ ] Assert total power is in the `138-146 W` target band.
- [ ] Assert sink raw span is around `0.42-0.44`.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/schema/test_s5_aggressive15_template.py
```

Expected before template creation: fail because the file does not exist.

---

## Task 2: Create The S5 Template

- [ ] Start from `scenarios/templates/s2_staged.yaml` as the closest single-case 15-component reference.
- [ ] Save as `scenarios/templates/s5_aggressive15.yaml`.
- [ ] Change template id and description to S5.
- [ ] Set placement region to approximately:
  - `x_min: 0.05`
  - `x_max: 0.95`
  - `y_min: 0.04`
  - `y_max: 0.72`
- [ ] Keep the same physics model unless solver smoke proves instability.
- [ ] Set top sink raw span around `0.42-0.44`.
- [ ] Increase total power into the `138-146 W` band.
- [ ] Make the load distribution multi-bottleneck:
  - one dominant hot component
  - two or three medium-hot support components
  - lower-power routing/support modules
- [ ] Keep all 15 components named `c01..c15`.
- [ ] Preserve fixed x/y optimization and no rotation optimization.

Run the schema test again and fix YAML contract issues before continuing.

---

## Task 3: Add Generator Tests

- [ ] Create `tests/generator/test_s5_aggressive15_template.py`.
- [ ] Generate seed 11 from `s5_aggressive15.yaml`.
- [ ] Assert generated case has 15 components.
- [ ] Assert sink exists and is on the top edge.
- [ ] Assert no component overlaps or clearance violations if existing helpers are available.
- [ ] Assert decision-vector extraction for the future optimization spec will produce 32 variables after specs are added.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/generator/test_s5_aggressive15_template.py
```

---

## Task 4: Add Evaluation Spec

- [ ] Create `scenarios/evaluation/s5_aggressive15_eval.yaml`.
- [ ] Keep objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- [ ] Add radiator span budget around `0.34-0.35`.
- [ ] Add 3-5 peak constraints for hot-core and shoulder components.
- [ ] Add a spread constraint only if calibration shows it is useful.
- [ ] Do not add a long list of constraints.

Calibration rule:

- First solve generated seed 11.
- Then choose thresholds that make the baseline informative, not impossible.
- Do not tune thresholds to force a predetermined winner.

---

## Task 5: Add Optimization Specs And Profiles

- [ ] Create raw spec: `scenarios/optimization/s5_aggressive15_raw.yaml`.
- [ ] Create union spec: `scenarios/optimization/s5_aggressive15_union.yaml`.
- [ ] Create llm spec: `scenarios/optimization/s5_aggressive15_llm.yaml`.
- [ ] Create raw profile: `scenarios/optimization/profiles/s5_aggressive15_raw.yaml`.
- [ ] Create union profile: `scenarios/optimization/profiles/s5_aggressive15_union.yaml`.
- [ ] Use the same 32-variable layout:
  - `c01_x/c01_y` through `c15_x/c15_y`
  - `sink_start`
  - `sink_end`
- [ ] Raw uses native backbone only.
- [ ] Union uses:

```yaml
operator_control:
  controller: random_uniform
  registry_profile: primitive_structured
```

- [ ] LLM uses:

```yaml
operator_control:
  controller: llm
  registry_profile: primitive_structured
```

- [ ] Keep LLM provider settings aligned with current GPT route conventions.
- [ ] Use the same evaluation spec path in all three modes.

---

## Task 6: Add Optimization Spec Tests

- [ ] Create `tests/optimizers/test_s5_aggressive15_specs.py`.
- [ ] Assert all three specs load.
- [ ] Assert all three use `scenarios/evaluation/s5_aggressive15_eval.yaml`.
- [ ] Assert raw / union / llm expose the same variable ids.
- [ ] Assert union and llm both use `primitive_structured`.
- [ ] Assert raw does not declare a controller pool.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_s5_aggressive15_specs.py
```

---

## Task 7: Validate Template, Generate, Solve, Evaluate

Run focused commands:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s5_aggressive15.yaml
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s5_aggressive15.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s5_aggressive15/seed-11
```

Then solve and evaluate the generated case using the produced paths.

If the solver fails, adjust physical/template aggressiveness before touching optimizer logic.

---

## Task 8: Smoke Benchmark

After focused tests and solver/evaluation smoke pass, run a small matched smoke:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml \
  --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --mode raw --mode union --mode llm \
  --llm-profile default \
  --benchmark-seed 11 \
  --population-size 10 \
  --num-generations 5 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

Render assets and compare the run before reporting conclusions.

---

## Task 9: Calibration Decision

After the first smoke:

- [ ] If raw trivially dominates, increase multi-bottleneck pressure or adjust constraints.
- [ ] If all modes fail mostly on geometry, loosen density/clearance or constraints.
- [ ] If union is too strong through random structured moves, reduce operator strength only in the shared operator plan, not in S5.
- [ ] If llm has valid traces but poor operator use, inspect prompt metadata before changing benchmark thresholds.

Keep S5 calibration local to S5 files unless the evidence clearly shows a shared operator issue.
