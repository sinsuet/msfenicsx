# EAAI Paper Problem and Method Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 §3 Problem Formulation and Benchmark 与 §4 Semantic Operator Control Method 形成可审阅 chapter briefs，冻结问题定义、符号、方法名、operator taxonomy 和伪代码边界。

**Architecture:** 本计划依赖 front matter plan 中的 `narrative_register.md` 和 `terminology_register.md`。它把问题定义和方法细节分开：§3 解释高维 PDE 约束卫星热布局是什么，§4 解释 LLM 如何作为 operator router 嵌入优化闭环。

**Tech Stack:** Markdown, LaTeX equations, algorithm pseudocode, YAML scenario specs, Python code-path inspection.

---

## 2026-05-09 恢复执行状态

- Status: problem/method briefs generated; user review gate still open.
- Generated under ignored `paper/` tree:
  - `paper/msgalaxy/planning/chapter_briefs/03_problem_benchmark_brief.md`
  - `paper/msgalaxy/planning/chapter_briefs/04_method_brief.md`
  - corresponding Fig. 2/Table 2/Fig. 3/Table 3/Algorithm 1/Algorithm 2 entries in `figure_table_register.md`
- Verified during recovery:
  - S4/S5/S6 are fixed single-case scale labels with 22/32/42 decision variables from component `x/y` variables plus `sink_start/sink_end`.
  - Source optimization YAMLs may carry smoke/default settings; the formal paper-facing budgets remain S4 `32 x 16 = 512`, S5 `40 x 32 = 1280`, and S6 `56 x 36 = 2016`.
  - `projection_plus_local_restore`, cheap constraints, and `semantic_ranked_pick` descriptions match the current code path.
- Still not complete: user has not explicitly approved equations, operator table wording, or pseudocode abstraction level.
- Versioning risk: `.gitignore` ignores `paper/`; these generated planning files are not visible in normal `git status`.

## Shared Literature and Citation Rules

- All literature/source-paper PDFs, reading notes, and staged BibTeX entries belong under `paper/msgalaxy/references/`.
- `paper/msgalaxy/planning/citation_register.md` is the citation admission register;正文 may cite only entries with `Status = verified`.
- Default literature search window is 2021-2026. Older papers are allowed only for classical foundations such as NSGA-II, MOEA/D, adaptive operator selection, hyper-heuristics, and spacecraft thermal-control foundations.
- Journals should be JCR/CAS Q1 or equivalent top-field venues where possible; conferences should be CCF-A/A* or field-top venues where possible.
- arXiv-only entries require explicit justification and should not anchor a core claim if a peer-reviewed source can support it.
- Official metadata sources are preferred: DOI/publisher pages, DBLP, OpenReview, IEEE, ACM, ScienceDirect, Springer, and arXiv official pages.
- Do not expand the Elsevier sample `cas-refs.bib` as the real bibliography. Use `references/bibtex/staging.bib`, promote approved entries to `references/bibtex/verified.bib`, and later generate the final root `references.bib`.
- Problem/method citations must support definitions, benchmark context, or algorithm lineage; they must not be used to smuggle in unverified performance claims.
- LaTeX compile hygiene: all formal or smoke manuscript compilation must run from `paper/msgalaxy` and write outputs to `paper/msgalaxy/compile/`, e.g. `latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=compile msgalaxy.tex`. Do not leave `.aux`, `.log`, `.out`, `.fls`, `.fdb_latexmk`, `.synctex.gz`, or generated PDFs in the template root or `sections/`.

## File Structure

- Modify: `paper/msgalaxy/planning/terminology_register.md`
- Modify: `paper/msgalaxy/planning/figure_table_register.md`
- Create: `paper/msgalaxy/planning/chapter_briefs/03_problem_benchmark_brief.md`
- Create: `paper/msgalaxy/planning/chapter_briefs/04_method_brief.md`
- Later after approval: `paper/msgalaxy/sections/03_problem_benchmark.tex`
- Later after approval: `paper/msgalaxy/sections/04_method.tex`

## Task 1: Freeze Problem Formulation Brief

**Files:**
- Create: `paper/msgalaxy/planning/chapter_briefs/03_problem_benchmark_brief.md`
- Modify: `paper/msgalaxy/planning/figure_table_register.md`

- [ ] **Step 1: Inspect required source files**

Read:

```bash
sed -n '1,220p' scenarios/templates/s5_aggressive15.yaml
sed -n '1,220p' scenarios/templates/s6_aggressive20.yaml
sed -n '1,220p' scenarios/templates/s4_aggressive10.yaml
sed -n '1,180p' scenarios/evaluation/s5_aggressive15_eval.yaml
sed -n '1,240p' optimizers/problem.py
sed -n '1,220p' optimizers/repair.py
sed -n '1,180p' optimizers/cheap_constraints.py
```

Expected: identify decision dimensions, objectives, hard constraints, and legality policy.

- [ ] **Step 2: Register benchmark figure and table**

Append to `figure_table_register.md`:

```markdown
| Fig. 2 | Benchmark layouts | The benchmark family scales satellite panel thermal layout from 10 to 20 components while preserving the same radiator-budget-constrained PDE evaluation contract. | Problem Formulation | scenario templates and rendered layouts | planned |
| Table 2 | Benchmark specification | The validation tasks are high-dimensional PDE-constrained satellite panel layouts with matched expensive-evaluation budgets. | Problem Formulation | scenario and optimization specs | planned |
```

- [ ] **Step 3: Draft `03_problem_benchmark_brief.md`**

Use:

```markdown
# Chapter 03 Brief: Problem Formulation and Benchmark

## 1. Role in the Paper

This chapter formalizes high-dimensional PDE-constrained satellite thermal layout optimization and defines the benchmark family used for validation.

## 2. Reader Takeaway

The application is not a toy heat-source placement task; it is a radiator-budget-constrained satellite panel layout problem with expensive PDE-based thermal evaluation and tens of continuous layout variables.

## 3. Section Outline

1. Thermal case and PDE evaluation contract.
2. Decision vector, component placement variables, radiator window variables, and no optimized rotation.
3. Objectives: `summary.temperature_max` and `summary.temperature_gradient_rms`.
4. Constraints: geometry legality, spacing, radiator span budget, and cheap screening before PDE.
5. Benchmark scale levels: describe them as 10/15/20-component high-dimensional validation tasks; use S4/S5/S6 only as internal identifiers.

## 4. Required Inputs

- `scenarios/templates/s4_aggressive10.yaml`
- `scenarios/templates/s5_aggressive15.yaml`
- `scenarios/templates/s6_aggressive20.yaml`
- `scenarios/evaluation/s5_aggressive15_eval.yaml`
- `optimizers/problem.py`
- `optimizers/repair.py`
- `optimizers/cheap_constraints.py`
- Fig. 2 and Table 2 from `figure_table_register.md`

## 5. Outputs to Other Chapters

- Symbols for decision vector, objective vector, feasible set, and PDE evaluator.
- Benchmark dimensions and budgets for Experimental Setup.
- Wording that S4/S5/S6 are fixed benchmark scale levels, not independent physical problem distributions.

## 6. Quality Gate

- No optimizer-method claims appear in this chapter.
- All dimensions and budgets are sourced from scenario/optimization specs.
- The problem is described as high-dimensional and PDE-constrained in reader-facing terms.
```

- [ ] **Step 4: Review gate**

Ask user to confirm the problem framing before drafting equations or LaTeX.

## Task 2: Freeze Method Brief

**Files:**
- Create: `paper/msgalaxy/planning/chapter_briefs/04_method_brief.md`
- Modify: `paper/msgalaxy/planning/figure_table_register.md`
- Modify: `paper/msgalaxy/planning/terminology_register.md`

- [ ] **Step 1: Inspect method source files**

Read:

```bash
sed -n '1,260p' optimizers/operator_pool/operators.py
sed -n '1,240p' optimizers/operator_pool/primitive_registry.py
sed -n '1,220p' optimizers/operator_pool/semantic_tasks.py
sed -n '1,260p' optimizers/operator_pool/state_builder.py
sed -n '1,280p' optimizers/operator_pool/llm_controller.py
sed -n '1,240p' optimizers/operator_pool/policy_kernel.py
sed -n '1,180p' llm/openai_compatible/schemas.py
```

Expected: identify operator pool, semantic tasks, controller state inputs, LLM output contract, and deterministic ranked-pick behavior.

- [ ] **Step 2: Register method figure, operator table, and algorithms**

Append to `figure_table_register.md`:

```markdown
| Fig. 3 | Method flow | The LLM ranks allowed thermal-design operators, and deterministic optimization components execute, repair, screen, and evaluate candidates. | Method | code-path inspection | planned |
| Table 3 | Thermal-semantic operator vocabulary | The method uses a fixed operator vocabulary shared by the non-semantic and LLM controllers. | Method | `optimizers/operator_pool/*` | planned |
| Algorithm 1 | Guarded semantic operator-controlled NSGA-II | The full optimization loop keeps LLM control at the semantic operator-routing layer. | Method | optimizer drivers and controller code | planned |
| Algorithm 2 | Deterministic semantic-ranked pick | Final operator choice is a deterministic selection over LLM rankings and exposure constraints. | Method | `llm_controller.py`, `policy_kernel.py` | planned |
```

- [ ] **Step 3: Extend terminology register**

Ensure `terminology_register.md` includes:

```markdown
## Operator-Control Terms

- `thermal-semantic operator vocabulary`: fixed set of physically meaningful thermal-design actions.
- `state-to-operator matching`: mapping current search and thermal context to an operator choice.
- `semantic decision layer`: the only layer where the LLM acts.
- `deterministic execution layer`: optimization, legality, screening, and PDE evaluation components.
```

- [ ] **Step 4: Draft `04_method_brief.md`**

Use:

```markdown
# Chapter 04 Brief: Semantic Operator Control Method

## 1. Role in the Paper

This chapter explains the central method: LLM-guided constrained thermal-semantic operator selection.

## 2. Reader Takeaway

The LLM is an operator router over a fixed thermal-design vocabulary, while deterministic optimization and simulation components retain execution authority.

## 3. Section Outline

1. From coordinate perturbation to thermal-semantic operator selection.
2. Fixed thermal-design operator vocabulary shared by non-semantic and LLM controllers.
3. Controller state: search phase, feasibility pressure, objective trade-off, spatial thermal cues, recent operator history.
4. LLM semantic ranking: rank operators, do not generate decision vectors.
5. Deterministic execution layer: selected operator proposes candidate, then optimization framework handles legality, screening, and physical evaluation.
6. Pseudocode for the full loop and ranked-pick step.

## 4. Required Inputs

- `optimizers/operator_pool/operators.py`
- `optimizers/operator_pool/primitive_registry.py`
- `optimizers/operator_pool/semantic_tasks.py`
- `optimizers/operator_pool/state_builder.py`
- `optimizers/operator_pool/llm_controller.py`
- `optimizers/operator_pool/policy_kernel.py`
- `llm/openai_compatible/schemas.py`
- Fig. 3, Table 3, Algorithm 1, Algorithm 2 from `figure_table_register.md`

## 5. Outputs to Other Chapters

- Method terminology for Related Work and Discussion.
- Operator taxonomy for Mechanistic Analysis.
- Pseudocode references for Experimental Setup.

## 6. Quality Gate

- The method chapter never says the LLM generates layouts.
- Guardrail, repair, cheap constraints, and PDE are explained at mechanism level here, not in contribution bullets.
- The non-semantic union baseline is described as sharing operator support, not as a stronger or weaker strawman.
```

- [ ] **Step 5: Review gate**

Ask user to confirm the method abstraction level before drafting `04_method.tex`.

## Self-Review Checklist

- [ ] §3 defines the problem without leaking method claims.
- [ ] §4 explains mechanism without overloading the Introduction contribution bullets.
- [ ] Figure/table/algorithm entries are registered before use.
- [ ] S4/S5/S6 appear as internal scale labels only after reader-facing benchmark description.

## Execution Handoff

Execute this plan after the front matter plan has produced and confirmed `narrative_register.md` and `terminology_register.md`.
