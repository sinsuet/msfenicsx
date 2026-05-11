# EAAI Paper Discussion, Conclusion, Appendix, Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 §8 Discussion and Limitations、§9 Conclusion、Appendix 和最终全文集成建立计划，保证结论不超出 evidence register，限制和失败结果保持可见。

**Architecture:** 本计划在前三个章节组 brief 完成后执行。它不新增核心贡献，而是检查全文一致性、整理限制、补充材料、LaTeX 集成和编译审查。

**Tech Stack:** Markdown, LaTeX/CAS, BibTeX/natbib, PDF compilation, artifact cross-checks.

---

## 2026-05-09 恢复执行状态

- Status: §8, §9, and appendix briefs generated; final integration not started.
- Generated under ignored `paper/` tree:
  - `paper/msgalaxy/planning/chapter_briefs/08_discussion_brief.md`
  - `paper/msgalaxy/planning/chapter_briefs/09_conclusion_brief.md`
  - `paper/msgalaxy/planning/chapter_briefs/appendix_brief.md`
  - Appendix Table A1 / Appendix Table B1 / Appendix Fig. B1 entries in `figure_table_register.md`
- Verified during recovery:
  - Discussion, Conclusion, and Appendix briefs preserve the `single-seed` / `aggregate` / `diagnostic` / `pending` / `hypothesis` evidence boundaries.
  - Full S4/S5/S6 LLM dominance remains a future evidence target, not a confirmed conclusion.
  - Appendix checklist includes claim/evidence, method-boundary, citation, figure/table, artifact, and LaTeX integration gates.
- Still not complete: user has not selected main-text limitation strength or appendix scope; no formal `08_discussion.tex`, `09_conclusion.tex`, appendix TeX, or `manuscript.tex` should be generated before review approval.
- Versioning risk: `.gitignore` ignores `paper/`; these generated planning files are not visible in normal `git status`.

## Shared Literature and Citation Rules

- All literature/source-paper PDFs, reading notes, and staged BibTeX entries belong under `paper/msgalaxy/references/`.
- `paper/msgalaxy/planning/citation_register.md` is the citation admission register;正文 may cite only entries with `Status = verified`.
- Default literature search window is 2021-2026. Older papers are allowed only for classical foundations such as NSGA-II, MOEA/D, adaptive operator selection, hyper-heuristics, and spacecraft thermal-control foundations.
- Journals should be JCR/CAS Q1 or equivalent top-field venues where possible; conferences should be CCF-A/A* or field-top venues where possible.
- arXiv-only entries require explicit justification and should not anchor a core claim if a peer-reviewed source can support it.
- Official metadata sources are preferred: DOI/publisher pages, DBLP, OpenReview, IEEE, ACM, ScienceDirect, Springer, and arXiv official pages.
- Do not expand the Elsevier sample `cas-refs.bib` as the real bibliography. Use `references/bibtex/staging.bib`, promote approved entries to `references/bibtex/verified.bib`, and later generate the final root `references.bib`.
- Integration must check that every `\citep{...}` / `\citet{...}` key exists in `verified.bib` and is marked `verified` in `citation_register.md`.
- LaTeX compile hygiene: all formal or smoke manuscript compilation must run from `paper/msgalaxy` and write outputs to `paper/msgalaxy/compile/`, e.g. `latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=compile msgalaxy.tex`. Do not leave `.aux`, `.log`, `.out`, `.fls`, `.fdb_latexmk`, `.synctex.gz`, or generated PDFs in the template root or `sections/`.

## File Structure

- Create: `paper/msgalaxy/planning/chapter_briefs/08_discussion_brief.md`
- Create: `paper/msgalaxy/planning/chapter_briefs/09_conclusion_brief.md`
- Create: `paper/msgalaxy/planning/chapter_briefs/appendix_brief.md`
- Later after approval: `paper/msgalaxy/sections/08_discussion.tex`
- Later after approval: `paper/msgalaxy/sections/09_conclusion.tex`
- Later after approval: `paper/msgalaxy/sections/appendix_a_contracts.tex`
- Later after approval: `paper/msgalaxy/sections/appendix_b_additional_results.tex`
- Later after approval: `paper/msgalaxy/msgalaxy.tex`

## Task 1: Draft Discussion Brief

**Files:**
- Create: `paper/msgalaxy/planning/chapter_briefs/08_discussion_brief.md`

- [ ] **Step 1: Read upstream briefs and registers**

Run:

```bash
sed -n '1,220p' paper/msgalaxy/planning/narrative_register.md
sed -n '1,220p' paper/msgalaxy/planning/evidence_register.md
sed -n '1,220p' paper/msgalaxy/planning/chapter_briefs/06_results_brief.md
sed -n '1,220p' paper/msgalaxy/planning/chapter_briefs/07_mechanistic_analysis_brief.md
```

Expected: identify confirmed claims, diagnostic claims, pending claims, and limitations.

- [ ] **Step 2: Draft `08_discussion_brief.md`**

Use:

```markdown
# Chapter 08 Brief: Discussion and Limitations

## 1. Role in the Paper

This chapter explains the implications and boundaries of LLM-guided semantic operator control without adding new results.

## 2. Reader Takeaway

Engineering-safe LLM control is useful because it narrows LLM authority to semantic routing, but it remains sensitive to profiles, scale, and evidence completeness.

## 3. Section Outline

1. What the LLM contributes: semantic state-to-operator routing.
2. What remains deterministic: feasibility, multi-objective selection, and physical validation.
3. Evidence limitations: single-seed versus aggregate, incomplete active final-block comparisons, failed/partial legacy runs.
4. Practical implications for expensive PDE-constrained optimization.
5. Future work: contextual bandit/AOS over LLM priors, broader geometry, surrogate-assisted PDE budgets.

## 4. Required Inputs

- `evidence_register.md`
- `07_mechanistic_analysis_brief.md`
- failed/partial run notes from `run_index.csv`

## 5. Quality Gate

- No new quantitative result appears here.
- Limitations are specific, not generic.
- Negative or partial evidence is not hidden.
```

- [ ] **Step 3: Review gate**

Ask user to confirm which limitations to include in main text.

## Task 2: Draft Conclusion Brief

**Files:**
- Create: `paper/msgalaxy/planning/chapter_briefs/09_conclusion_brief.md`

- [ ] **Step 1: Draft `09_conclusion_brief.md`**

Use:

```markdown
# Chapter 09 Brief: Conclusion

## 1. Role in the Paper

The conclusion restates the method and evidence without introducing new claims.

## 2. Reader Takeaway

The paper shows a practical way to use LLMs in engineering optimization: route bounded thermal-design operators, keep physics and feasibility deterministic.

## 3. Section Outline

1. Recap the problem: high-dimensional PDE-constrained satellite thermal layout optimization.
2. Recap the method: LLM-guided constrained thermal-semantic operator selection.
3. Recap evidence using only confirmed `aggregate` or approved `single-seed` wording.
4. Close with future work.

## 4. Required Inputs

- `narrative_register.md`
- `evidence_register.md`
- final Results wording

## 5. Quality Gate

- Conclusion matches Abstract and Introduction contributions.
- No new number appears only in Conclusion.
- If full S4/S5/S6 final-block evidence is not complete, the conclusion remains appropriately qualified.
```

- [ ] **Step 2: Review gate**

Ask user to approve conclusion strength after final Results are frozen.

## Task 3: Draft Appendix Brief

**Files:**
- Create: `paper/msgalaxy/planning/chapter_briefs/appendix_brief.md`
- Modify: `paper/msgalaxy/planning/figure_table_register.md`

- [ ] **Step 1: Register appendix tables and figures**

Append:

```markdown
| Appendix Table A1 | Artifact contract | The optimization bundle records enough metadata to audit controller, operator, screening, and PDE evaluation behavior. | Appendix | run manifests and traces | planned |
| Appendix Table B1 | Per-seed results | Full seed-level results remain visible beyond main-text summaries. | Appendix | comparison CSVs | planned |
| Appendix Fig. B1 | Additional fields/layouts | Representative layouts and thermal fields support qualitative inspection. | Appendix | representative bundles | planned |
```

- [ ] **Step 2: Draft `appendix_brief.md`**

Use:

```markdown
# Appendix Brief

## 1. Role in the Paper

Appendices provide reproducibility details, additional per-seed results, and supplementary figures without interrupting the main story.

## 2. Required Appendix Content

1. Artifact contracts and trace schemas.
2. Additional seed-level result tables.
3. LLM prompt/state projection examples with sensitive fields removed.
4. Solver and visualization details.

## 3. Quality Gate

- No private API keys, endpoint URLs, or raw sensitive prompts.
- Generated artifacts are not manually edited.
- Appendix tables are sourced from CSV/JSON artifacts.
```

- [ ] **Step 3: Review gate**

Ask user to decide which appendix material is required for first complete draft.

## Task 4: Final Integration Checklist
