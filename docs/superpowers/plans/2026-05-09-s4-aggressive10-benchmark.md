# S4 Aggressive10 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `s4_aggressive10` 场景配置，并运行 32x16 的 raw、union、llm-DeepSeek benchmark。

**Architecture:** 仅新增 hand-authored scenario/test/docs 文件，不修改 optimizer、solver 或 generator 业务逻辑。S4 复用 S4/S5/S6 的 `scenario_template -> thermal_case -> thermal_solution -> evaluation_report -> run-benchmark` 契约。

**Tech Stack:** YAML scenario specs, pytest, `conda run -n msfenicsx`, existing optimizer CLI, DeepSeek OpenAI-compatible profile.

---

### Task 1: S4 Contract Tests

**Files:**
- Create: `tests/schema/test_s4_aggressive10_template.py`
- Create: `tests/generator/test_s4_aggressive10_generator.py`
- Create: `tests/optimizers/test_s4_aggressive10_specs.py`

- [x] **Step 1: Write failing tests**  
  Tests assert 10 components, 22 variables, 32x16 budgets, DeepSeek LLM profile, top sink, load/fill bands, evaluation constraints, and seed-11 generation legality.

- [x] **Step 2: Verify RED**  
  Run:
  `conda run -n msfenicsx pytest -q tests/schema/test_s4_aggressive10_template.py tests/generator/test_s4_aggressive10_generator.py tests/optimizers/test_s4_aggressive10_specs.py`

  Expected: FAIL because S4 template/eval/optimization files do not exist.

### Task 2: S4 Scenario Files

**Files:**
- Create: `scenarios/templates/s4_aggressive10.yaml`
- Create: `scenarios/evaluation/s4_aggressive10_eval.yaml`
- Create: `scenarios/optimization/s4_aggressive10_raw.yaml`
- Create: `scenarios/optimization/s4_aggressive10_union.yaml`
- Create: `scenarios/optimization/s4_aggressive10_llm.yaml`
- Create: `scenarios/optimization/profiles/s4_aggressive10_raw.yaml`
- Create: `scenarios/optimization/profiles/s4_aggressive10_union.yaml`

- [x] **Step 1: Add S4 YAML files**  
  Add the 10-component low-dimensional aggressive scene and matched optimization ladder.

- [ ] **Step 2: Verify GREEN**  
  Run the focused S4 test command again and require all tests to pass.

### Task 3: Smoke Validation

**Files:** no code changes.

- [ ] **Step 1: Validate template**  
  Run:
  `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s4_aggressive10.yaml`

- [ ] **Step 2: Generate, solve, and evaluate seed-11**  
  Run generate-case, solve-case, and evaluate-case for S4 seed 11.

### Task 4: 32x16 Benchmark Runs

**Files:** runtime artifacts under `scenario_runs/`.

- [ ] **Step 1: Run raw**  
  `conda run -n msfenicsx python -m optimizers.cli run-benchmark --optimization-spec scenarios/optimization/s4_aggressive10_raw.yaml --mode raw --benchmark-seed 11 --algorithm-seed 1011 --population-size 32 --num-generations 16 --evaluation-workers 2 --scenario-runs-root ./scenario_runs`

- [ ] **Step 2: Run union**  
  Same command with `s4_aggressive10_union.yaml --mode union`.

- [ ] **Step 3: Run llm DeepSeek**  
  Same command with `s4_aggressive10_llm.yaml --mode llm --llm-profile deepseek_v4_flash`.

- [ ] **Step 4: Report results**  
  Inspect `run_index.csv`, run manifests, final analytics and comparison artifacts. Report real status, paths, best objective values and failures if any.
