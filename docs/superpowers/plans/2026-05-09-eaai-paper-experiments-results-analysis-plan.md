# EAAI Paper Experiments, Results, Mechanistic Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 §5 Experimental Setup、§6 Results 和 §7 Mechanistic Analysis 建立 artifact-backed 写作计划，确保所有结果 claim 都有路径、预算、seed 和 comparison scope。

**Architecture:** 本计划围绕 `evidence_register.md` 执行。先登记可用结果和待补结果，再生成实验设置、结果和机制分析 briefs。正文只允许使用 `evidence_register.md` 中状态合适的 claim。

**Tech Stack:** Markdown, CSV/JSON artifact inspection, LaTeX tables, matplotlib-generated figures, scenario run manifests.

---

## 2026-05-09 恢复执行状态

- Status: evidence register and §5-§7 briefs generated; user review gate still open.
- Generated under ignored `paper/` tree:
  - `paper/els-cas-templates/planning/evidence_register.md`
  - `paper/els-cas-templates/planning/chapter_briefs/05_experimental_setup_brief.md`
  - `paper/els-cas-templates/planning/chapter_briefs/06_results_brief.md`
  - `paper/els-cas-templates/planning/chapter_briefs/07_mechanistic_analysis_brief.md`
  - Table 4/Table 5/Fig. 4/Fig. 5/Table 6/Fig. 6/Fig. 7 entries in `figure_table_register.md`
- Verified during recovery:
  - S5 seed-11 semantic ablation artifacts exist under `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek`.
  - `summary_rows.csv`, `common_pde_cutoff.csv`, `delta_vs_raw.csv`, `operator_distribution.csv`, and `llm_decision_summary.json` match the registered S5 claim wording.
  - Strict Evidence ID check found no missing registered claim IDs in briefs or current §5-§7 draft text.
- Existing draft caveat: `paper/els-cas-templates/sections/05_experimental_setup.tex`, `06_results.tex`, and `07_mechanistic_analysis.tex` already exist, but they were produced before explicit brief approval and should remain draft material until the review gate closes.
- Still not complete: active S4/S5/S6 final-block LLM comparisons remain `pending`.
- Versioning risk: `.gitignore` ignores `paper/`; these generated planning files and draft sections are not visible in normal `git status`.

## Shared Literature and Citation Rules

- All literature/source-paper PDFs, reading notes, and staged BibTeX entries belong under `paper/els-cas-templates/references/`.
- `paper/els-cas-templates/planning/citation_register.md` is the citation admission register;正文 may cite only entries with `Status = verified`.
- Default literature search window is 2021-2026. Older papers are allowed only for classical foundations such as NSGA-II, MOEA/D, adaptive operator selection, hyper-heuristics, and spacecraft thermal-control foundations.
- Journals should be JCR/CAS Q1 or equivalent top-field venues where possible; conferences should be CCF-A/A* or field-top venues where possible.
- arXiv-only entries require explicit justification and should not anchor a core claim if a peer-reviewed source can support it.
- Official metadata sources are preferred: DOI/publisher pages, DBLP, OpenReview, IEEE, ACM, ScienceDirect, Springer, and arXiv official pages.
- Do not expand the Elsevier sample `cas-refs.bib` as the real bibliography. Use `references/bibtex/staging.bib`, promote approved entries to `references/bibtex/verified.bib`, and later generate the final root `references.bib`.
- Experimental claims are governed by `evidence_register.md`; citations can justify baselines, metrics, and software, but cannot substitute for local artifact-backed evidence.
- LaTeX compile hygiene: all formal or smoke manuscript compilation must run from `paper/els-cas-templates` and write outputs to `paper/els-cas-templates/compile/`, e.g. `latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=compile manuscript.tex`. Do not leave `.aux`, `.log`, `.out`, `.fls`, `.fdb_latexmk`, `.synctex.gz`, or generated PDFs in the template root or `sections/`.

## File Structure

- Create: `paper/els-cas-templates/planning/evidence_register.md`
- Modify: `paper/els-cas-templates/planning/figure_table_register.md`
- Create: `paper/els-cas-templates/planning/chapter_briefs/05_experimental_setup_brief.md`
- Create: `paper/els-cas-templates/planning/chapter_briefs/06_results_brief.md`
- Create: `paper/els-cas-templates/planning/chapter_briefs/07_mechanistic_analysis_brief.md`
- Later after approval: `paper/els-cas-templates/sections/05_experimental_setup.tex`
- Later after approval: `paper/els-cas-templates/sections/06_results.tex`
- Later after approval: `paper/els-cas-templates/sections/07_mechanistic_analysis.tex`

## Task 1: Create Evidence Register from Current Artifacts

**Files:**
- Create: `paper/els-cas-templates/planning/evidence_register.md`

- [ ] **Step 1: Inspect current comparison artifacts**

Run:

```bash
sed -n '1,220p' scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/s5_seed11_semantic_ablation_report.md
sed -n '1,80p' scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/summary_rows.csv
sed -n '1,80p' scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/common_pde_cutoff.csv
sed -n '1,120p' scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/operator_distribution.csv
sed -n '1,80p' scenario_runs/s5_aggressive15/0509_0130__raw_union/comparisons/aggregate/raw_vs_union/tables/aggregate_mode_summary.csv
sed -n '1,80p' scenario_runs/s6_aggressive20/0509_0130__raw_union/comparisons/by_seed/seed-11/raw_vs_union/tables/summary_table.csv
```

Expected: identify single-seed, aggregate, diagnostic, and pending evidence.

- [ ] **Step 2: Draft `evidence_register.md`**

Use:

```markdown
# Evidence Register

## Evidence Status Rules

- `single-seed`: may be reported only as single-seed evidence.
- `aggregate`: may be reported as aggregate evidence.
- `diagnostic`: may support mechanism or reliability claims, not final performance dominance.
- `hypothesis`: may not be used in Results conclusions.

## Current Claims

| Claim ID | Status | Claim Text | Artifact Path | Scenario | Seeds | Budget | Metrics | Comparison Scope |
|---|---|---|---|---|---|---|---|---|
| E-S5-SEM-001 | single-seed | Under a common PDE cutoff, the LLM semantic controller reduces gradient RMS versus native NSGA-II and operator-matched non-semantic control. | `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/common_pde_cutoff.csv` | `s5_aggressive15` | benchmark 11 / algorithm 1011 | common PDE cutoff 907 | gradient RMS 16.383 vs 14.730 vs 13.661 | raw vs neutral union vs deepseek LLM |
| E-S5-SEM-002 | single-seed | The LLM semantic controller improves final hypervolume over native NSGA-II in the current S5 seed-11 semantic ablation. | `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/delta_vs_raw.csv` | `s5_aggressive15` | benchmark 11 / algorithm 1011 | nominal 1280 proposals | +17.01% HV vs raw | raw vs neutral union vs deepseek LLM |
| E-S5-SEM-003 | diagnostic | The LLM method changes operator exposure relative to neutral union, supporting state-aware semantic operator selection rather than merely owning more operators. | `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/operator_distribution.csv` | `s5_aggressive15` | benchmark 11 / algorithm 1011 | nominal 1280 proposals | operator share | neutral union vs deepseek LLM |
| E-S5-AGG-001 | aggregate | S5 raw/union five-seed aggregate shows structured operator support changes the trade-off, improving gradient and HV mean while not uniformly improving peak temperature. | `scenario_runs/s5_aggressive15/0509_0130__raw_union/comparisons/aggregate/raw_vs_union/tables/aggregate_mode_summary.csv` | `s5_aggressive15` | 11,17,23,29,31 | formal S5 budget | mean gradient, mean HV, mean peak | raw vs hand-weighted union |
| E-S6-SEED11-001 | single-seed | S6 seed-11 raw/union comparison shows union improves peak, gradient, and HV under matched budget. | `scenario_runs/s6_aggressive20/0509_0130__raw_union/comparisons/by_seed/seed-11/raw_vs_union/tables/summary_table.csv` | `s6_aggressive20` | benchmark 11 / algorithm 1011 | formal S6 budget | peak, gradient, HV | raw vs union |
| E-MAIN-S4-S6 | hypothesis | Across the active S4/S5/S6 benchmark ladder, LLM semantic control improves Pareto quality and thermal-gradient reduction over the raw baseline. | pending final main-block comparisons | S4/S5/S6 | 5 seeds per scale | matched formal budgets | pending | raw vs DeepSeek LLM |
```

- [ ] **Step 3: Review gate**

Ask user to confirm which claims can be used in main Results and which must remain diagnostic or pending.

## Task 2: Draft Experimental Setup Brief

**Files:**
- Create: `paper/els-cas-templates/planning/chapter_briefs/05_experimental_setup_brief.md`
- Modify: `paper/els-cas-templates/planning/figure_table_register.md`

- [ ] **Step 1: Register experimental tables**

Append:

```markdown
| Table 4 | Experimental matrix | Methods are compared under matched expensive-evaluation budgets and clearly separated into native, operator-matched non-semantic, and LLM semantic-control conditions. | Experimental Setup | run_index.csv and optimization specs | planned |
| Table 5 | Metric definitions | Every reported metric maps to an artifact source and an optimization interpretation. | Experimental Setup | evaluation and comparison artifacts | planned |
```

- [ ] **Step 2: Draft `05_experimental_setup_brief.md`**

Use:

```markdown
# Chapter 05 Brief: Experimental Setup

## 1. Role in the Paper

This chapter defines fair comparison conditions: methods, budgets, metrics, seeds, and artifact sources.

## 2. Reader Takeaway

The LLM method is evaluated under matched expensive-evaluation budgets; it does not receive extra operators, solver changes, or hidden physical information.

## 3. Section Outline

1. Benchmark scale levels and formal budgets.
2. Compared methods: native NSGA-II, operator-matched non-semantic control, LLM semantic controller.
3. Metrics: peak temperature, gradient RMS, Pareto front, HV, feasible rate, first feasible PDE, cheap skips, controller diagnostics.
4. Artifact protocol: run roots, comparison bundles, traces, and generated figures.
5. Reporting rules for single-seed, aggregate, diagnostic, and pending evidence.

## 4. Required Inputs

- `evidence_register.md`
- `run_index.csv` files under `scenario_runs/`
- scenario optimization specs
- Table 4 and Table 5 from `figure_table_register.md`

## 5. Quality Gate

- No result interpretation belongs in this chapter.
- Failed and partial runs remain visible.
- Separate run roots are not compared unless common cutoff/reference point is controlled.
```

- [ ] **Step 3: Review gate**

Ask user to confirm baseline names and reporting rules.

## Task 3: Draft Results Brief

**Files:**
- Create: `paper/els-cas-templates/planning/chapter_briefs/06_results_brief.md`
- Modify: `paper/els-cas-templates/planning/figure_table_register.md`

- [ ] **Step 1: Register result figures and tables**

Append:

```markdown
| Fig. 4 | Semantic ablation summary | Under matched S5 seed-11 conditions, LLM semantic control improves thermal-gradient reduction and HV relative to native and non-semantic baselines. | Results | `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/figures/summary_metrics.pdf` | available |
| Fig. 5 | Pareto overlay | The LLM controller changes the Pareto trade-off under matched operator support. | Results | `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/figures/pareto_overlay.pdf` | available |
| Table 6 | Main result table | Performance claims are separated by evidence status: single-seed, aggregate, and pending. | Results | `evidence_register.md` and comparison CSVs | planned |
```

- [ ] **Step 2: Draft `06_results_brief.md`**

Use:

```markdown
# Chapter 06 Brief: Results

## 1. Role in the Paper

This chapter reports artifact-backed performance evidence without overstating unfinished campaign results.

## 2. Reader Takeaway

Current evidence supports the semantic-control story most cleanly through the S5 seed-11 operator-matched ablation, while broader S4/S5/S6 final-block claims remain pending until matched campaign comparisons are complete.

## 3. Section Outline

1. S5 seed-11 semantic ablation: raw vs neutral union vs LLM semantic controller.
2. Common PDE cutoff comparison for fairness.
3. Aggregate and scale-up evidence that is available but not yet final for the full LLM claim.
4. Pending result slots for the S4/S5/S6 main block, S4 semantic ablation, S5 mechanism ablation, S5 model sensitivity, and S5 raw-only algorithm baseline.

## 4. Required Inputs

- `evidence_register.md`
- `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/*.csv`
- Fig. 4, Fig. 5, Table 6 from `figure_table_register.md`

## 5. Quality Gate

- Single-seed evidence is labeled single-seed.
- Hypothesis claims do not appear as confirmed results.
- Internal S4/S5/S6 labels are explained only after reader-facing problem description.
```

- [ ] **Step 3: Review gate**

Ask user to approve what goes into main Results versus appendix.

## Task 4: Draft Mechanistic Analysis Brief

**Files:**
- Create: `paper/els-cas-templates/planning/chapter_briefs/07_mechanistic_analysis_brief.md`
- Modify: `paper/els-cas-templates/planning/figure_table_register.md`

- [ ] **Step 1: Register mechanism figures**

Append:

```markdown
| Fig. 6 | Operator distribution | LLM semantic control changes operator exposure relative to non-semantic control under the same operator support. | Mechanistic Analysis | `operator_distribution.csv` and `.pdf` | available |
| Fig. 7 | Controller diagnostics | Valid ranked responses and semantic-task diversity support the engineering-safe controller claim. | Mechanistic Analysis | `llm_decision_summary.json` | planned |
```

- [ ] **Step 2: Draft `07_mechanistic_analysis_brief.md`**

Use:

```markdown
# Chapter 07 Brief: Mechanistic Analysis

## 1. Role in the Paper

This chapter explains why performance differences can be attributed to semantic operator selection rather than additional operators or extra budget.

## 2. Reader Takeaway

The LLM changes when operators are used, not what operators exist.

## 3. Section Outline

1. Operator-matched ablation logic.
2. Operator exposure: neutral union versus LLM semantic controller.
3. Controller validity and fallback behavior.
4. Failure modes and profile sensitivity.

## 4. Required Inputs

- `evidence_register.md`
- `operator_distribution.csv`
- `llm_decision_summary.json` from completed LLM runs
- Fig. 6 and Fig. 7 from `figure_table_register.md`

## 5. Quality Gate

- Mechanistic claims use traces and operator distributions, not subjective LLM rationales.
- Negative or partial results remain visible.
- The chapter reinforces `LLM routes operators; it does not generate layouts`.
```

- [ ] **Step 3: Review gate**

Ask user to confirm whether mechanism analysis belongs in main text or partly in appendix.

## Self-Review Checklist

- [ ] Every result claim has an `Evidence Register` row.
- [ ] Figure/table entries exist before briefs reference them.
- [ ] Pending S4/S5/S6 final-block claims remain `hypothesis` or `pending`.
- [ ] Common cutoff and reference point caveats are explicit.

## Execution Handoff

Execute this plan only after problem/method briefs have frozen benchmark and method terminology.
