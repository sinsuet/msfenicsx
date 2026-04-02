# 2026-04-01 Beamer Figure Pack Design

Date: 2026-04-01

> Status: approved execution design for a report-facing figure pack used by the four Chinese progress reports and the follow-up LaTeX Beamer deck.

## 1. Goal

Generate a compact, presentation-first figure pack for the current paper-facing `NSGA-II` thermal optimization mainline.

This pack is not meant to be a full experiment dashboard. It is meant to give the later Beamer deck a small set of high-signal figures that can explain:

1. the benchmark scene,
2. the eight-variable decision encoding,
3. the `raw / union-uniform / llm-union` method ladder,
4. one representative seed-23 comparison,
5. one best-result seed-17 snapshot.

## 2. Evidence Boundary

All figures must stay inside the already approved reporting boundary:

- benchmark template:
  - `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- evaluation spec:
  - `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
- paper-facing raw baseline:
  - `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- representative seed for the main comparison:
  - `seed-23`
- best absolute-result snapshot:
  - `seed-17`

The figures must not silently mix unrelated experiment classes, retired baselines, or unmatched budgets.

## 3. Figure Pack

The approved first-wave pack contains eight figures:

1. `01_benchmark_layout_overview`
2. `02_design_variables_schematic`
3. `03_raw_union_llm_architecture`
4. `04_seed23_initial_and_final_layouts`
5. `05_seed23_metrics_comparison`
6. `06_seed23_representative_objectives`
7. `07_seed23_operator_mix`
8. `08_seed17_best_snapshot`

## 4. Main Figure Intent

### 4.1 Benchmark Understanding

`01_benchmark_layout_overview` must explain the panel domain, the placement region, the keep-out strip, the four component families, and the top-edge radiator boundary feature.

`02_design_variables_schematic` must explain that the optimization stays in the same 8D decision space and that `union` changes proposal/control behavior rather than the decision encoding itself.

### 4.2 Method Understanding

`03_raw_union_llm_architecture` must show the shared pipeline and the single changed layer:

- `raw`: native `SBX + PM`
- `union-uniform`: shared mixed action registry + random/uniform controller
- `llm-union`: shared mixed action registry + `LLM` controller

### 4.3 Result Understanding

`04` to `08` must give a report-friendly comparison based on approved artifacts.

`seed-23` is the main narrative example because it visibly separates the three modes.

`seed-17` is used as the best-result snapshot because it provides a stronger final feasible configuration for the later “best case” slide.

## 5. Data Sources

### 5.1 Seed-23 Main Comparison

- raw:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-23-real-test/optimization_result.json`
- union-uniform:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-23-real-test/optimization_result.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-23-real-test/operator_trace.json`
- llm-union:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/optimization_result.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/operator_trace.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/controller_trace.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/llm_metrics.json`

### 5.2 Seed-17 Best Snapshot

- raw:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-17-real-test/optimization_result.json`
- union-uniform:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-17-real-test/optimization_result.json`
- llm-union:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/optimization_result.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/operator_trace.json`
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/llm_metrics.json`

## 6. Visual Rules

The figures should be Beamer-first rather than paper-maximal:

- Chinese labels are preferred.
- Each figure should be readable when scaled to one Beamer slide.
- The pack should use one stable color mapping:
  - `raw`
  - `union-uniform`
  - `llm-union`
- The panel layout figures should use the real benchmark geometry for the selected seed, not arbitrary placeholder sizes.
- Comparison figures should prefer a few interpretable metrics over crowded dashboards.

## 7. Output Contract

The generated files should live under:

- `docs/reports/figures/2026-04-01-beamer-pack/`

Preferred outputs:

- `PNG` for easy preview and quick Beamer use
- `PDF` when practical for vector-friendly inclusion

## 8. Success Criteria

This figure pack is successful if:

1. all eight approved figures are generated,
2. the filenames are stable and directly referenceable from LaTeX,
3. the layouts and metrics correspond to the approved seed-23 and seed-17 evidence,
4. a later Beamer author can insert these figures without re-running or manually redrawing them.
