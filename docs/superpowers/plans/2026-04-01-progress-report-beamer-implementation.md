# Progress Report Beamer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Chinese LaTeX Beamer deck of about 30 slides for the current `msfenicsx` progress report, using the four approved reports plus the approved figure pack and extra architecture figures, and compile it with the local Windows-side TeX Live toolchain.

**Architecture:** Create one report-local Beamer project under `docs/reports/beamer/2026-04-01-progress-report/`, keep the deck modular with a main file plus section slide files, centralize theme and macro settings in a small preamble file, and compile the deck with Windows `latexmk/xelatex` against the repo’s existing figure assets. Verification will include successful compilation and visual page rendering checks on the produced PDF.

**Tech Stack:** LaTeX Beamer, XeLaTeX, Windows-side TeX Live, repository Markdown reports, existing PNG/PDF figures, `pdftoppm` if available for rendered-page inspection

---

## Target File Map

- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/main.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/preamble.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/01_opening.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/02_problem.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/03_framework.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/04_llm_method.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/05_experiments.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/06_conclusion.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/07_backup.tex`

## Task 1: Confirm Build Context And Deck Skeleton

**Files:**
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/main.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/preamble.tex`

- [ ] **Step 1: Confirm the local Windows-side TeX executables and compilation entry point**

Expected tools:

- `xelatex.exe`
- `latexmk.exe`

Preferred compile command:

```powershell
& 'D:\MSCode\texlive\2025\bin\windows\latexmk.exe' -xelatex -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```

- [ ] **Step 2: Write a minimal Beamer skeleton**

Include:

- Chinese-capable XeLaTeX setup
- title metadata for `李昭城`
- institution `中科院微小卫星创新院`
- stable color mapping for `raw / union / llm`
- `\graphicspath` entries for the approved figure directories

- [ ] **Step 3: Compile the minimal skeleton and verify it produces a PDF**

Expected: successful compile with a placeholder title page.

## Task 2: Fill The 30-Slide Main Narrative

**Files:**
- Modify: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/main.tex`
- Modify: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/preamble.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/01_opening.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/02_problem.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/03_framework.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/04_llm_method.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/05_experiments.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/06_conclusion.tex`

- [ ] **Step 1: Write the opening and problem-definition slides**

Cover:

- title
- agenda
- three questions of the talk
- benchmark problem statement
- benchmark scene and 8D decision variables
- objectives, constraints, and modeling chain

- [ ] **Step 2: Write the shared-framework slides**

Cover:

- three-method ladder
- shared pipeline
- fair-comparison boundary
- `raw` and `union-uniform` explanations

- [ ] **Step 3: Write the `LLM-union` method slides**

Cover:

- overall `LLM-union` architecture
- fixed action registry
- controller state
- policy kernel
- guardrails and trace artifacts

- [ ] **Step 4: Write the experiment and results slides**

Cover:

- matched protocol
- why `seed-23` and `seed-17`
- seed-23 layouts
- seed-23 metrics
- seed-23 objectives
- seed-23 operator mix
- seed-23 mechanism interpretation
- seed-17 best snapshot

- [ ] **Step 5: Write the conclusion slides**

Cover:

- what we can claim now
- what we cannot claim yet
- next steps
- summary and Q&A

## Task 3: Add Backup Slides And Polish Layout

**Files:**
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/slides/07_backup.tex`
- Modify: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/preamble.tex`

- [ ] **Step 1: Add 4 backup slides**

Recommended backup pages:

- detailed objective/constraint table
- seed-23 margin table
- LLM runtime statistics
- nine-operator semantic table

- [ ] **Step 2: Tune typography, spacing, and figure scale**

Check:

- slide titles do not wrap awkwardly
- figures are large enough for projection
- tables remain readable
- no slide is text-heavy beyond the chosen presentation style

## Task 4: Compile, Render, And Fix

**Files:**
- Modify: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/main.tex`
- Modify: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-01-progress-report/preamble.tex`
- Modify: slide files as needed

- [ ] **Step 1: Run a full Beamer compile with Windows TeX Live**

Run:

```powershell
Set-Location '\\wsl$\Ubuntu\home\hymn\msfenicsx\docs\reports\beamer\2026-04-01-progress-report'
& 'D:\MSCode\texlive\2025\bin\windows\latexmk.exe' -xelatex -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```

- [ ] **Step 2: Render the produced PDF pages to PNGs for visual inspection**

Preferred command:

```bash
pdftoppm -png build/main.pdf tmp/rendered/page
```

- [ ] **Step 3: Inspect rendered pages and fix any defects**

Look for:

- clipped text
- broken Chinese glyphs
- oversized tables
- figures too small
- poor page breaks

- [ ] **Step 4: Recompile until the deck is clean**

Expected: stable PDF with no LaTeX errors and no obvious layout defects in rendered previews.
