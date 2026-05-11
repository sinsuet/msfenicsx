# EAAI Paper Front Matter, Introduction, Related Work Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 冻结 EAAI 论文的 front matter、Introduction 和 Related Work 写作接口，使后续正文并行写作共享同一贡献口径和文献定位。

**Architecture:** 本计划不直接写最终正文，而是先创建 planning registers，再生成并审阅 `00_abstract_highlights_brief.md`、`01_introduction_brief.md` 和 `02_related_work_brief.md`。所有引用先进入 `citation_register.md`，所有贡献和禁用口径先进入 `narrative_register.md`。

**Tech Stack:** Markdown, LaTeX/CAS, BibTeX/natbib, web/publisher/arXiv citation verification.

---

## 2026-05-09 恢复执行状态

- Status: planning artifacts generated; user review gate still open.
- Generated under ignored `paper/` tree:
  - `paper/msgalaxy/planning/narrative_register.md`
  - `paper/msgalaxy/planning/terminology_register.md`
  - `paper/msgalaxy/planning/citation_register.md`
  - `paper/msgalaxy/planning/figure_table_register.md`
  - `paper/msgalaxy/planning/chapter_briefs/00_abstract_highlights_brief.md`
  - `paper/msgalaxy/planning/chapter_briefs/01_introduction_brief.md`
  - `paper/msgalaxy/planning/chapter_briefs/02_related_work_brief.md`
- Verified during recovery: contribution wording, forbidden framing, Fig. 1/Table 1 placeholder policy, and citation admission rules are present.
- Still not complete: user has not explicitly approved the briefs; `citation_register.md` entries remain `candidate` or `screened`, so Related Work正文 must not cite them yet.
- Versioning risk: `.gitignore` ignores `paper/`; these generated planning files are not visible in normal `git status`.

## Shared Literature and Citation Rules

- All literature/source-paper PDFs, reading notes, and staged BibTeX entries belong under `paper/msgalaxy/references/`.
- `paper/msgalaxy/planning/citation_register.md` is the citation admission register;正文 may cite only entries with `Status = verified`.
- Default literature search window is 2021-2026. Older papers are allowed only for classical foundations such as NSGA-II, MOEA/D, adaptive operator selection, hyper-heuristics, and spacecraft thermal-control foundations.
- Journals should be JCR/CAS Q1 or equivalent top-field venues where possible; conferences should be CCF-A/A* or field-top venues where possible.
- arXiv-only entries require explicit justification and should not anchor a core claim if a peer-reviewed source can support it.
- Official metadata sources are preferred: DOI/publisher pages, DBLP, OpenReview, IEEE, ACM, ScienceDirect, Springer, and arXiv official pages.
- Do not expand the Elsevier sample `cas-refs.bib` as the real bibliography. Use `references/bibtex/staging.bib`, promote approved entries to `references/bibtex/verified.bib`, and later generate the final root `references.bib`.
- Fig. 1 and Table 1 remain placeholders until final assets and verified citation support are available.
- LaTeX compile hygiene: all formal or smoke manuscript compilation must run from `paper/msgalaxy` and write outputs to `paper/msgalaxy/compile/`, e.g. `latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=compile msgalaxy.tex`. Do not leave `.aux`, `.log`, `.out`, `.fls`, `.fdb_latexmk`, `.synctex.gz`, or generated PDFs in the template root or `sections/`.

## File Structure

- Create: `paper/msgalaxy/planning/narrative_register.md`
  全文叙事、三点贡献、Abstract/Introduction 分工、禁止口径。
- Create: `paper/msgalaxy/planning/terminology_register.md`
  固定方法名、baseline 名称、benchmark 说法。
- Create: `paper/msgalaxy/planning/citation_register.md`
  引用候选和核验状态。
- Create: `paper/msgalaxy/planning/figure_table_register.md`
  front matter、Fig. 1、Related Work table 的编号与 caption claim。
- Create: `paper/msgalaxy/planning/chapter_briefs/00_abstract_highlights_brief.md`
- Create: `paper/msgalaxy/planning/chapter_briefs/01_introduction_brief.md`
- Create: `paper/msgalaxy/planning/chapter_briefs/02_related_work_brief.md`
- Later after approval: `paper/msgalaxy/sections/00_abstract_highlights.tex`
- Later after approval: `paper/msgalaxy/sections/01_introduction.tex`
- Later after approval: `paper/msgalaxy/sections/02_related_work.tex`
- Later after approval: `paper/msgalaxy/references.bib`

## Task 1: Create Global Narrative and Terminology Registers

**Files:**
- Create: `paper/msgalaxy/planning/narrative_register.md`
- Create: `paper/msgalaxy/planning/terminology_register.md`

- [ ] **Step 1: Create the planning directories**

Run:

```bash
mkdir -p paper/msgalaxy/planning/chapter_briefs
```

Expected: directories exist.

- [ ] **Step 2: Draft `narrative_register.md`**

Include exactly these stable decisions:

```markdown
# Narrative Register

## Core Memory Sentence

The LLM routes thermal-design operators; it does not generate layouts.

## Paper Positioning

This paper proposes LLM-guided constrained thermal-semantic operator selection for high-dimensional PDE-constrained satellite thermal layout optimization.

## Contribution Paragraph for Introduction

This paper makes three contributions. First, we introduce **LLM-guided constrained thermal-semantic operator selection**, which reframes satellite thermal layout search as state-to-operator matching over physically meaningful thermal-design actions rather than direct coordinate perturbation or layout generation. Second, we formulate an **engineering-safe LLM-in-the-loop optimization paradigm**, where the language model is confined to semantic control while deterministic optimization and physics simulation retain authority over feasibility, selection, and validation. Third, we validate the paradigm on **high-dimensional PDE-constrained satellite thermal layout optimization**, showing that semantic operator control improves Pareto-front quality, thermal-gradient reduction, and feasible-search efficiency over native NSGA-II and an operator-matched non-semantic control baseline under matched expensive-evaluation budgets.

## Abstract Policy

Abstract should not list the three contributions. It should state the core idea in one to two sentences and summarize the engineering validation in one sentence.

## Do Not Say

- LLM directly generates satellite layouts.
- LLM directly optimizes the PDE.
- S4/S5/S6 are independent physical problem distributions.
- The union baseline is a stronger baseline.
- The method is a new metaphor-based metaheuristic.
```

- [ ] **Step 3: Draft `terminology_register.md`**

Include:

```markdown
# Terminology Register

## Method Names

- Preferred full method concept: `LLM-guided constrained thermal-semantic operator selection`
- Short method phrase: `LLM semantic operator control`
- Do not use as method name: `LLM optimizer`, `LLM layout generator`, `semantic optimizer`

## Baseline Names

- `NSGA-II`: native backbone baseline.
- `NSGA-II + Union Operators`: operator-matched non-semantic control baseline.
- `NSGA-II + LLM Semantic Controller`: LLM-guided semantic control method.

## Problem Names

- Preferred: `high-dimensional PDE-constrained satellite thermal layout optimization`
- Preferred application phrase: `radiator-budget-constrained satellite panel layout`
- Avoid in contribution bullets: `S4/S5/S6 benchmark`
```

- [ ] **Step 4: Review gate**

Ask user to confirm the two registers before drafting chapter briefs. Expected: user confirms or requests wording changes.

## Task 2: Draft Abstract and Introduction Briefs

**Files:**
- Create: `paper/msgalaxy/planning/chapter_briefs/00_abstract_highlights_brief.md`
- Create: `paper/msgalaxy/planning/chapter_briefs/01_introduction_brief.md`
- Modify: `paper/msgalaxy/planning/figure_table_register.md`

- [ ] **Step 1: Register front-matter figures/tables**

Create `figure_table_register.md` with:

```markdown
# Figure and Table Register

| ID | Type | Caption Claim | Target Section | Data Source | Status |
|---|---|---|---|---|---|
| Fig. 1 | Architecture | The LLM routes thermal-design operators inside a deterministic PDE-constrained optimization loop rather than generating layouts. | Introduction | manual architecture figure from method brief | planned |
| Table 1 | Related-work matrix | Prior work lacks the combination of high-dimensional PDE thermal layout, fixed operator support, bounded LLM semantic control, and matched ablation. | Related Work | citation register | planned |
```

- [ ] **Step 2: Draft `00_abstract_highlights_brief.md`**

Use this content:

```markdown
# Chapter 00 Brief: Abstract, Highlights, Keywords

## 1. Role in the Paper

This front matter gives readers the core idea without listing the full contribution bullets.

## 2. Reader Takeaway

The LLM routes thermal-design operators; it does not generate layouts.

## 3. Required Abstract Moves

1. Define the engineering challenge: radiator-budget-constrained satellite panel layout with high-dimensional decisions and expensive PDE thermal simulation.
2. State the AI contribution: LLM-guided constrained thermal-semantic operator selection.
3. State the safety boundary: LLM routes operators while deterministic optimization and physics simulation retain feasibility, selection, and validation authority.
4. State validation at a high level without S4/S5/S6 names.

## 4. Draft Sentences Allowed

We propose an LLM-guided constrained thermal-semantic operator selection framework for high-dimensional PDE-constrained satellite thermal layout optimization. Instead of generating layouts directly, the language model routes physically meaningful thermal-design operators, while deterministic optimization and physics simulation retain control over feasibility, selection, and validation.

Experiments on radiator-budget-constrained satellite panel layouts show improved Pareto-front quality, thermal-gradient reduction, and feasible-search efficiency over native NSGA-II and operator-matched non-semantic baselines under matched expensive-evaluation budgets.

## 5. Quality Gate

- No contribution bullet list.
- No internal benchmark names in the abstract.
- No unverified final numeric claim.
```

- [ ] **Step 3: Draft `01_introduction_brief.md`**

Use this outline:

```markdown
# Chapter 01 Brief: Introduction

## 1. Role in the Paper

The Introduction motivates why high-dimensional satellite thermal layout optimization needs semantic operator control, then states the three contributions.

## 2. Reader Takeaway

LLMs are useful here because they can route thermal-design operators from search context, not because they can generate engineering layouts.

## 3. Section Outline

1. Satellite thermal layout is constrained by radiator budget, component coupling, and thermal gradients.
2. Native coordinate perturbation cannot distinguish thermal design situations such as sink misalignment, local crowding, and frontier stagnation.
3. Direct LLM layout generation is unsuitable for engineering optimization because feasibility and physics validation must remain controlled.
4. Our idea: LLM-guided constrained thermal-semantic operator selection.
5. Contributions: use the exact three-contribution paragraph from `narrative_register.md`.

## 4. Required Inputs

- `docs/ss.txt`
- `README.md`
- `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/s5_seed11_semantic_ablation_report.md`
- Fig. 1 from `figure_table_register.md`

## 5. Quality Gate

- Contribution bullets do not mention S4/S5/S6.
- Raw/union/llm appears only as evaluation logic, not as a contribution.
- Method details are not over-expanded in the Introduction.
```

- [ ] **Step 4: Review gate**

Ask user to review both briefs before writing `00_abstract_highlights.tex` or `01_introduction.tex`.

## Task 3: Draft Related Work Brief and Citation Register

**Files:**
- Create: `paper/msgalaxy/planning/chapter_briefs/02_related_work_brief.md`
- Modify: `paper/msgalaxy/planning/citation_register.md`

- [ ] **Step 1: Create citation register skeleton**

Use:

```markdown
# Citation Register

| Key | Status | Target Section | Why Cited | Source URL / DOI |
|---|---|---|---|---|
| gilmore2002spacecraft | candidate | Introduction / Related Work | spacecraft thermal control and radiator motivation | DOI to verify |
| fakoor2016scale | candidate | Related Work | spacecraft component layout optimization | DOI 10.1016/j.asr.2016.07.020 |
| deb2002nsga2 | candidate | Related Work / Experiments | native NSGA-II baseline | DOI 10.1109/4235.996017 |
| zhang2007moead | candidate | Related Work / Experiments | raw-only MOEA/D baseline | DOI 10.1109/TEVC.2007.892759 |
| blank2020pymoo | candidate | Experiments | optimizer implementation | DOI 10.1109/ACCESS.2020.2990567 |
| yang2023opro | candidate | Related Work | contrast with direct LLM optimization | arXiv 2309.03409 |
| aos_fialho | candidate | Related Work | adaptive operator selection lineage | verify exact publication |
| hyperheuristic_burke | candidate | Related Work | hyper-heuristic selection lineage | verify exact publication |
```

- [ ] **Step 2: Draft `02_related_work_brief.md`**

Use:

```markdown
# Chapter 02 Brief: Related Work

## 1. Role in the Paper

Related Work positions the paper between spacecraft thermal/component layout, expensive multi-objective engineering optimization, adaptive operator selection/hyper-heuristics, and LLM-assisted optimization.

## 2. Reader Takeaway

Prior work either optimizes layouts without bounded LLM semantic control, studies operator selection without this PDE thermal-layout setting, or uses LLMs more directly than engineering-safe operator routing.

## 3. Section Outline

1. Spacecraft and thermal layout optimization: motivate application and gap.
2. Expensive PDE-constrained multi-objective optimization: motivate matched budgets and native MOEA baselines.
3. Adaptive operator selection and hyper-heuristics: position the operator-routing lineage.
4. LLMs for optimization: contrast with direct LLM candidate generation.

## 4. Required Inputs

- `citation_register.md`
- `figure_table_register.md` Table 1
- EAAI guide note that the paper must distinguish AI contribution and engineering application.

## 5. Quality Gate

- Every citation used in draft must be `verified`.
- Related Work must synthesize categories rather than list papers.
- The contrast must support the phrase `LLM routes operators; it does not generate layouts`.
```

- [ ] **Step 3: Review gate**

Ask user to confirm the Related Work categories before full literature search and BibTeX insertion.

## Self-Review Checklist

- [ ] The three-contribution paragraph appears only through `narrative_register.md`.
- [ ] No S4/S5/S6 names appear in the contribution bullets.
- [ ] Related Work search is constrained by the frozen method framing.
- [ ] Fig. 1 and Table 1 are registered before any section references them.

## Execution Handoff

After this plan is approved, execute Tasks 1-3 first. Do not write final LaTeX sections until the user approves the corresponding chapter briefs.
