# S7 Aggressive 25-Component Benchmark Implementation Plan

> **For agentic workers:** This plan depends on the shared `primitive_structured` operator-pool plan and should start after S5/S6 are stable enough to distinguish density issues from shared-pool issues. Do not edit operator implementation files here.

**Goal:** Add `s7_aggressive25` as the 25-component dense aggressive benchmark using the shared `primitive_structured` pool.

**Architecture:** Create a 52-variable single-case benchmark with matched raw / union / llm optimization specs. S7 should stress scalability and density while keeping thermal objectives, not geometry failure, as the main signal.

**Spec:** [docs/superpowers/specs/2026-04-28-s7-aggressive-25-component-benchmark-design.md](../specs/2026-04-28-s7-aggressive-25-component-benchmark-design.md)

---

## Dependencies

Complete first:

- [docs/superpowers/plans/2026-04-28-primitive-structured-operator-pool.md](2026-04-28-primitive-structured-operator-pool.md)
- [docs/superpowers/plans/2026-04-28-s5-aggressive-15-component-benchmark.md](2026-04-28-s5-aggressive-15-component-benchmark.md)
- [docs/superpowers/plans/2026-04-28-s6-aggressive-20-component-benchmark.md](2026-04-28-s6-aggressive-20-component-benchmark.md)

This plan should not implement or tune the shared operator pool.

---

## File Map

Create:

- `scenarios/templates/s7_aggressive25.yaml`
- `scenarios/evaluation/s7_aggressive25_eval.yaml`
- `scenarios/optimization/s7_aggressive25_raw.yaml`
- `scenarios/optimization/s7_aggressive25_union.yaml`
- `scenarios/optimization/s7_aggressive25_llm.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_raw.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_union.yaml`
- `tests/schema/test_s7_aggressive25_template.py`
- `tests/generator/test_s7_aggressive25_template.py`
- `tests/optimizers/test_s7_aggressive25_specs.py`

Modify after validation only:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md` if repository guidance should list S7

Do not modify:

- optimizer operator code
- LLM controller code
- run artifacts by hand

---

## Task 1: Add Template Contract Tests

- [ ] Create `tests/schema/test_s7_aggressive25_template.py`.
- [ ] Assert template id `s7_aggressive25`.
- [ ] Assert exactly 25 component families and 25 load rules.
- [ ] Assert families are named `c01` through `c25`.
- [ ] Assert one top-edge line sink.
- [ ] Assert no `operating_case_profiles`.
- [ ] Assert total power is in the `176-190 W` target band.
- [ ] Assert placement region matches the dense S7 target.
- [ ] Assert components include multiple placement regimes through `placement_hint` and `layout_tags`.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/schema/test_s7_aggressive25_template.py
```

Expected before template creation: fail because the file does not exist.

---

## Task 2: Create The S7 Template

- [ ] Start from validated S6 if available; otherwise use S5/S2 patterns and add five extra components carefully.
- [ ] Save as `scenarios/templates/s7_aggressive25.yaml`.
- [ ] Set placement region approximately:
  - `x_min: 0.04`
  - `x_max: 0.96`
  - `y_min: 0.04`
  - `y_max: 0.74`
- [ ] Keep one top-edge sink.
- [ ] Set raw sink span about `0.46-0.48`.
- [ ] Target evaluation budget around `0.37-0.38`.
- [ ] Set total power to `176-190 W`.
- [ ] Use 25 fixed components named `c01..c25`.
- [ ] Structure roles as:
  - `c01-c06`: primary hot core and shields
  - `c07-c12`: secondary hot lane
  - `c13-c18`: center/service shoulder
  - `c19-c25`: edge, bus, service, lower-band modules

Do not make every added component high-power. Preserve a mix of hot, medium, and support modules.

---

## Task 3: Add Generator Tests

- [ ] Create `tests/generator/test_s7_aggressive25_template.py`.
- [ ] Generate seed 11.
- [ ] Assert generated case has 25 components.
- [ ] Assert generated layout is legal or explainable under existing geometry checks.
- [ ] Assert top sink and total load match the design shape.
- [ ] Assert the generated case is not dominated by malformed geometry before optimization.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/generator/test_s7_aggressive25_template.py
```

---

## Task 4: Add Evaluation Spec

- [ ] Create `scenarios/evaluation/s7_aggressive25_eval.yaml`.
- [ ] Keep objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- [ ] Add radiator span budget around `0.37-0.38`.
- [ ] Add peak constraints for primary core modules.
- [ ] Add one or two peak constraints for secondary-lane modules.
- [ ] Add spread constraint only if calibration shows it improves the signal.

Avoid a long list of component constraints. The benchmark should still expose optimizer behavior rather than only pass/fail filtering.

---

## Task 5: Add Optimization Specs And Profiles

- [ ] Create raw, union, and llm specs under `scenarios/optimization/`.
- [ ] Create raw and union profiles under `scenarios/optimization/profiles/`.
- [ ] Use 52 variables:
  - `c01_x/c01_y` through `c25_x/c25_y`
  - `sink_start`
  - `sink_end`
- [ ] Ensure all three specs reference `scenarios/evaluation/s7_aggressive25_eval.yaml`.
- [ ] Union and llm both use `registry_profile: primitive_structured`.
- [ ] Raw remains native-only.
- [ ] LLM provider settings follow current GPT route conventions.

---

## Task 6: Add Optimization Spec Tests

- [ ] Create `tests/optimizers/test_s7_aggressive25_specs.py`.
- [ ] Assert all three specs load.
- [ ] Assert variable ids match across raw / union / llm.
- [ ] Assert the variable count is 52.
- [ ] Assert union and llm use `primitive_structured`.
- [ ] Assert raw stays native-only.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_s7_aggressive25_specs.py
```

---

## Task 7: Validate, Generate, Solve, Evaluate

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s7_aggressive25.yaml
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s7_aggressive25.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s7_aggressive25/seed-11
```

Then solve/evaluate the generated case with S7 evaluation spec.

If the generator struggles, reduce clearance or footprint pressure before changing solver or optimizer logic.

---

## Task 8: Smoke Benchmark

After focused validation, run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s7_aggressive25_raw.yaml \
  --optimization-spec scenarios/optimization/s7_aggressive25_union.yaml \
  --optimization-spec scenarios/optimization/s7_aggressive25_llm.yaml \
  --mode raw --mode union --mode llm \
  --llm-profile default \
  --benchmark-seed 11 \
  --population-size 10 \
  --num-generations 5 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

A 10x5 S7 run is only a sanity check. Do not overinterpret performance until a larger calibrated budget is available.

---

## Task 9: Calibration Decision

After smoke:

- [ ] If cheap geometry failures dominate, loosen density or clearances.
- [ ] If PDE solves are unstable, reduce power or source concentration.
- [ ] If no mode reaches feasible layouts, relax thermal constraints or sink budget tension.
- [ ] If raw dominates trivially, increase multi-bottleneck structure without adding controller hacks.
- [ ] If llm fails through operator collapse, inspect traces before changing the template.

Keep S7 calibration in S7 files unless a shared operator issue is proven by S5/S6 as well.
