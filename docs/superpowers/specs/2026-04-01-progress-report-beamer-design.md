# 2026-04-01 Progress Report Beamer Design

Date: 2026-04-01

> Status: user-approved Beamer deck design for the current four-report progress package and figure pack.

## 1. Goal

Build a Chinese LaTeX Beamer deck of about 30 pages for the current `msfenicsx` paper-facing mainline.

The deck should not be a literal reformat of the four reports. It should reorganize the report material into a presentation-first narrative that is easier to follow in a live technical talk.

The deck should answer three top-level questions:

1. What problem are we solving?
2. Why is the `raw / union / llm-union` comparison meaningful and fair?
3. What evidence do we currently have for the value and limitations of `LLM-union`?

## 2. Presenter Metadata

- Presenter:
  - `李昭城`
- Institution:
  - `中科院微小卫星创新院`
- Language:
  - Chinese

These fields should appear on the title slide and in the Beamer metadata.

## 3. Source Boundary

The deck must stay inside the already approved evidence boundary:

- report source:
  - `docs/reports/2026-04-01-progress-report-01-problem-definition.md`
  - `docs/reports/2026-04-01-progress-report-02-mainline-architecture.md`
  - `docs/reports/2026-04-01-progress-report-03-llm-union-method.md`
  - `docs/reports/2026-04-01-progress-report-04-representative-experiment.md`
- figure pack:
  - `docs/reports/figures/2026-04-01-beamer-pack/`
- extra architecture figures:
  - `docs/reports/figures/llm-union.png`
  - `docs/reports/figures/raw_UNION_LLM.png`

The deck must not mix in retired legacy routes, unmatched experiment classes, or claims beyond the validated current mainline.

## 4. Recommended Deck Strategy

Three candidate organizations were considered:

1. four-report parallel layout
2. mainline narrative layout
3. results-first layout

The approved recommendation is the **mainline narrative layout**.

This means the deck should not allocate one quarter of the slides to each report mechanically. Instead, it should compress the four reports into a five-part talk:

1. problem definition and modeling
2. shared architecture and fair comparison boundary
3. `LLM-union` method details
4. representative experiment evidence
5. conclusions, limitations, and next steps

## 5. Page Budget

The main deck target is about **30 slides**, plus **4 backup slides** if needed.

Recommended timing assumption:

- 25 to 30 minutes
- internal technical progress report
- audience is technically mature, but may not know this exact benchmark and controller line

## 6. Recommended Main Deck Structure

### Part A: Opening and Problem Setup

1. title page
2. agenda / talk map
3. three questions of this talk
4. background and task definition
5. benchmark scene overview
6. 8D decision variables
7. objectives and constraints
8. modeling chain from template to optimization result
9. why this is a hard multicase constrained expensive MOO problem

### Part B: Fair Comparison Framework

10. three-method top-level overview
11. detailed shared pipeline and proposal-time insertion
12. why the comparison is fair
13. `raw` baseline
14. `union-uniform` baseline

### Part C: LLM-union Method

15. `LLM-union` overall architecture
16. fixed mixed action registry
17. controller state and policy kernel
18. guardrail, anti-collapse, and trace artifacts

### Part D: Experimental Evidence

19. experiment setting and matched protocol
20. why `seed-23` is the main case and `seed-17` is the best snapshot
21. seed-23 shared initial layout and three end states
22. seed-23 aggregate metrics comparison
23. seed-23 representative objective comparison
24. seed-23 operator mix comparison
25. seed-23 mechanism interpretation
26. seed-17 best snapshot

### Part E: Conclusions

27. what we can claim now
28. what we cannot claim yet
29. next-step research plan
30. summary and Q&A

## 7. Mandatory Figure Placement

The following figures must be used in the main deck:

1. `docs/reports/figures/2026-04-01-beamer-pack/01_benchmark_layout_overview.png`
2. `docs/reports/figures/2026-04-01-beamer-pack/02_design_variables_schematic.png`
3. `docs/reports/figures/2026-04-01-beamer-pack/03_raw_union_llm_architecture.png`
4. `docs/reports/figures/raw_UNION_LLM.png`
5. `docs/reports/figures/llm-union.png`
6. `docs/reports/figures/2026-04-01-beamer-pack/04_seed23_initial_and_final_layouts.png`
7. `docs/reports/figures/2026-04-01-beamer-pack/05_seed23_metrics_comparison.png`
8. `docs/reports/figures/2026-04-01-beamer-pack/06_seed23_representative_objectives.png`
9. `docs/reports/figures/2026-04-01-beamer-pack/07_seed23_operator_mix.png`
10. `docs/reports/figures/2026-04-01-beamer-pack/08_seed17_best_snapshot.png`

Recommended placement:

- `03_raw_union_llm_architecture.png`:
  - first high-level Chinese overview page for the method ladder
- `raw_UNION_LLM.png`:
  - detailed shared pipeline page
- `llm-union.png`:
  - dedicated `LLM-union` architecture page

This creates a deliberate three-level method explanation:

1. high-level comparison
2. detailed shared system pipeline
3. dedicated `LLM-union` controller view

## 8. Slide Design Principles

The deck should feel like a serious internal research talk rather than a marketing presentation.

### 8.1 Visual Style

- clean academic Beamer style
- stable method colors:
  - `raw = blue`
  - `union = orange`
  - `llm = green`
- avoid decorative overload
- prioritize readability on a projected screen

### 8.2 Text Density

- one main idea per slide
- avoid long paragraphs on slides
- use short bullets, equations, tables, and figures
- let the spoken narration carry detail that is already in the four reports

### 8.3 Results Slides

- prefer one main chart per slide
- do not tile too many small plots onto one slide
- each result slide should make one clear claim

## 9. Claim Discipline

The deck must preserve the same evidence discipline as the four reports:

1. do not say `LLM-union` is universally better
2. do not present a single seed as proof of a unified framework result
3. do not describe action-space expansion as decision-space expansion
4. distinguish clearly between:
   - current positive evidence
   - current limitations
   - next-stage hypotheses

## 10. Backup Slides

Recommended backup pages:

1. full objective and constraint table
2. seed-23 constraint margin table
3. LLM runtime statistics
4. nine-operator semantic table

## 11. Implementation Expectations

When the deck is implemented, it should produce:

- one main Beamer `.tex` file
- supporting style and figure references as needed
- local-compilable PDF output

The content should be sourced from the four reports, but rewritten for slides rather than pasted verbatim.
