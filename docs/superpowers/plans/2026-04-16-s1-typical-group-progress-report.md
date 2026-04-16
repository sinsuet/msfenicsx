# S1 Typical Group Progress Report Docs And Beamer Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the four progress-report Markdown documents so they describe the current `s1_typical` 15-component single-case benchmark and then build a Chinese Beamer deck of about 20 slides for an internal group progress report.

**Architecture:** Keep the existing four-report split because it maps cleanly onto the group-report narrative, but fully replace the old benchmark framing with the current `s1_typical` mainline. Use one budget-matched representative experiment (`20x10`, `201 eval`, `benchmark_seed=11`, `algorithm.seed=7`) and present `raw`, `union`, and the completed `llm-L6` `20x10` run as the current comparison boundary, while explicitly labeling the objective-balance LLM route as ongoing work rather than finished evidence.

**Tech Stack:** Markdown, LaTeX Beamer, XeLaTeX, repository docs, JSON summaries under `scenario_runs/`, Windows-side TeX Live toolchain

---

## Target File Map

- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-01-problem-definition.md`
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-02-mainline-architecture.md`
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-03-llm-union-method.md`
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-04-representative-experiment.md`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/main.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/preamble.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/01_opening.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/02_problem.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/03_architecture.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/04_llm_method.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/05_experiment.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/06_close.tex`

## Evidence Inputs To Reuse

- Benchmark identity and object flow:
  - `/home/hymn/msfenicsx/AGENTS.md`
  - `/home/hymn/msfenicsx/docs/reports/2026-04-10-s1-typical-end-to-end-flow-and-seed11-walkthrough.md`
- Current paper-facing inputs:
  - `/home/hymn/msfenicsx/scenarios/templates/s1_typical.yaml`
  - `/home/hymn/msfenicsx/scenarios/evaluation/s1_typical_eval.yaml`
  - `/home/hymn/msfenicsx/scenarios/optimization/s1_typical_raw.yaml`
  - `/home/hymn/msfenicsx/scenarios/optimization/s1_typical_union.yaml`
  - `/home/hymn/msfenicsx/scenarios/optimization/s1_typical_llm.yaml`
- Completed `20x10` comparison evidence:
  - `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_2352__raw_union/`
  - `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/l6-mid-20x10/`
- LLM method and current-next-step context:
  - `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-15-l6-expand-saturation-governor-results.md`
  - `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-15-objective-balance-signal-design.md`

## Task 1: Freeze Report Boundary And Source Of Truth

**Files:**
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-01-problem-definition.md`
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-02-mainline-architecture.md`
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-03-llm-union-method.md`
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-04-representative-experiment.md`

- [ ] **Step 1: Re-read the current benchmark identity and run evidence**

Run:

```bash
cd /home/hymn/msfenicsx
sed -n '1,220p' AGENTS.md
sed -n '1,220p' docs/reports/2026-04-10-s1-typical-end-to-end-flow-and-seed11-walkthrough.md
```

Expected: clear confirmation that the active paper-facing line is `s1_typical`, single-case, 15 components, 32 decision variables.

- [ ] **Step 2: Freeze the matched-budget experiment boundary**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
root = Path('/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_2352__raw_union/comparison/summaries/seed_delta_table.json')
print(root.read_text())
PY
```

Expected: `raw` and `union` rows for `seed-11` with `201`-evaluation-equivalent summaries.

- [ ] **Step 3: Freeze the current LLM comparison label**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
path = Path('/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/l6-mid-20x10/optimization_result.json')
data = json.loads(path.read_text())
print(data['run_meta'])
print('history_len=', len(data['history']))
PY
```

Expected: completed `llm-L6` `20x10` evidence with `benchmark_seed=11`, `algorithm_seed=7`, and `history_len=201`.

- [ ] **Step 4: Write down the hard exclusions before editing**

All four reports and the Beamer deck must exclude:

- any old four-component benchmark content
- any transition section explaining why the project moved away from the old benchmark
- any old `hot/cold` benchmark variables, seeds, or figures

- [ ] **Step 5: Reserve the ongoing-work wording**

Use this narrative rule everywhere:

- completed evidence:
  - `raw 20x10`
  - `union 20x10`
  - `llm-L6 20x10`
- ongoing work:
  - objective-balance LLM route

## Task 2: Rewrite Report 01 As The Canonical Problem Definition

**Files:**
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-01-problem-definition.md`

- [ ] **Step 1: Replace the old opening and report purpose**

Write an opening that frames this as an internal progress report on the current `s1_typical` mainline only.

- [ ] **Step 2: Write a one-sentence problem definition that is impossible to misread**

The sentence must explicitly state:

- 2D thermal layout optimization
- fixed single benchmark case
- 15 named components
- one top-edge sink interval
- 32 decision variables
- two objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`

- [ ] **Step 3: Add the benchmark identity section**

Cover:

- panel domain and placement region
- 15 components and their role grouping
- single `line_sink`
- single operating case
- fixed `benchmark_seed=11` for the representative report

- [ ] **Step 4: Add the optimization formulation section**

Cover:

- design variables:
  - 15 component `x/y`
  - `sink_start`
  - `sink_end`
- hard constraints
- cheap-constraint-before-PDE rule
- repair semantics:
  - projection plus local legality restoration

- [ ] **Step 5: Add the canonical object flow and artifact flow**

Use the exact current object flow:

```text
scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle
thermal_case + thermal_solution + evaluation_spec -> evaluation_report
```

- [ ] **Step 6: Add the group-report experiment scope**

State that this report set uses the `20x10` matched-budget case as the current evidence anchor.

- [ ] **Step 7: Verify the report contains no old benchmark language**

Run:

```bash
rg -n '四组件|four-component|panel_four|hot/cold|multicase|seed-23|seed-17|8 维' \
  /home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-01-problem-definition.md
```

Expected: no matches.

## Task 3: Rewrite Report 02 As The Fair-Comparison Architecture Story

**Files:**
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-02-mainline-architecture.md`

- [ ] **Step 1: Replace the method ladder with the current paper-facing ladder**

Write:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

and remove old route names entirely.

- [ ] **Step 2: Rewrite the top-level module boundary table**

Use:

- `core/`
- `evaluation/`
- `optimizers/`
- `llm/`
- `visualization/`
- `scenarios/`

- [ ] **Step 3: Add the shared comparison boundary**

State explicitly that all three modes share:

- the same `s1_typical` template
- the same evaluation spec
- the same repair semantics
- the same cheap constraints
- the same PDE solve path
- the same objective/constraint extraction

- [ ] **Step 4: Add the one-line difference for each mode**

Write concise sections for:

- `raw`: native `NSGA-II`
- `union`: same `NSGA-II` plus mixed operator registry plus `random_uniform`
- `llm`: same `NSGA-II`, same registry, controller switched to `llm`

- [ ] **Step 5: Add the proposal-time insertion diagram**

Use a text diagram or simple code block that makes clear:

```text
population -> proposal -> repair -> solve -> evaluate -> survival
```

and highlight that only the proposal/control layer changes across modes.

- [ ] **Step 6: Add the artifact and trace section**

Mention:

- `controller_trace.json`
- `operator_trace.json`
- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- comparison summaries under `scenario_runs/s1_typical/<run_id>/comparison/`

- [ ] **Step 7: Verify the report contains no old benchmark language**

Run:

```bash
rg -n '四组件|four-component|panel_four|hot/cold|multicase|seed-23|seed-17|8 维' \
  /home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-02-mainline-architecture.md
```

Expected: no matches.

## Task 4: Rewrite Report 03 As The Current LLM-Controller Method Story

**Files:**
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-03-llm-union-method.md`

- [ ] **Step 1: Rewrite the method positioning paragraph**

Describe the method as:

- an LLM-guided controller
- operating on the shared union operator registry
- not directly outputting the final layout vector
- not modifying repair, evaluation, or survival semantics

- [ ] **Step 2: Replace the old operator list with the current shared registry**

Document the active operator pool from the current `s1_typical_union` / `s1_typical_llm` specs.

- [ ] **Step 3: Add the controller-state summary**

Explain the current role of:

- run state
- progress state
- archive state
- domain regime
- operator summary
- recent decisions

- [ ] **Step 4: Add the policy-kernel and guardrail explanation**

Keep this section group-report friendly:

- what the controller sees
- what gets filtered or shaped before the LLM chooses
- how traces keep the run auditable

- [ ] **Step 5: Add the current recovery-line narrative**

State:

- completed comparison evidence is `llm-L6 20x10`
- objective-balance is the current improvement direction
- do not present objective-balance as finished evidence yet

- [ ] **Step 6: Add a short “what the LLM does not do” section**

Include:

- does not change the physics
- does not change the benchmark
- does not bypass repair
- does not bypass constraints
- does not replace `NSGA-II` survival

- [ ] **Step 7: Verify the report contains no old benchmark language**

Run:

```bash
rg -n '四组件|four-component|panel_four|hot/cold|multicase|seed-23|seed-17|8 维' \
  /home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-03-llm-union-method.md
```

Expected: no matches.

## Task 5: Rewrite Report 04 Around The 20x10 Representative Experiment

**Files:**
- Modify: `/home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-04-representative-experiment.md`

- [ ] **Step 1: Rewrite the experiment scope**

The report must say the representative case is:

- `benchmark_seed=11`
- `algorithm.seed=7`
- `population_size=20`
- `num_generations=10`
- `201 eval`

- [ ] **Step 2: Add the completed evidence boundary**

Use:

- `raw`: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_2352__raw_union/raw/`
- `union`: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_2352__raw_union/union/`
- `llm`: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/l6-mid-20x10/`

- [ ] **Step 3: Write the main comparison table**

Include at minimum:

- `first_feasible_eval`
- `optimizer_feasible_rate`
- `pareto_size`
- `best_temperature_max`
- `best_gradient_rms`

- [ ] **Step 4: Write the interpretation section in group-report tone**

Recommended interpretation:

- `raw`: stronger gradient than `union`, decent matched-budget baseline
- `union`: best `T_max` among completed `20x10` modes, but weaker gradient
- `llm-L6`: strongest gradient and good pareto behavior, but `T_max` stagnation remains

- [ ] **Step 5: Add the mechanism observation section**

Cover:

- `union` controller/operator trace as the non-LLM controller reference
- `llm-L6` stagnation diagnosis from the `2026-04-15` specs
- objective-balance as the next targeted fix

- [ ] **Step 6: Add the “what we can say now / what is still ongoing” section**

This section must clearly separate:

- completed `20x10` evidence
- unfinished objective-balance LLM rerun

- [ ] **Step 7: Verify the report contains no old benchmark language**

Run:

```bash
rg -n '四组件|four-component|panel_four|hot/cold|multicase|seed-23|seed-17|8 维' \
  /home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-04-representative-experiment.md
```

Expected: no matches.

## Task 6: Build The 20-Slide Group-Report Beamer Deck

**Files:**
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/main.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/preamble.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/01_opening.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/02_problem.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/03_architecture.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/04_llm_method.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/05_experiment.tex`
- Create: `/home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report/slides/06_close.tex`

- [ ] **Step 1: Create the deck skeleton and XeLaTeX preamble**

Use a Chinese-capable Beamer setup with stable color mapping for:

- `raw`
- `union`
- `llm`

- [ ] **Step 2: Allocate exactly about 20 main slides**

Recommended split:

- opening: 2 slides
- problem definition: 5 slides
- architecture: 4 slides
- LLM method: 4 slides
- experiment/results: 4 slides
- close: 1 slide

- [ ] **Step 3: Write the opening slides**

Cover:

- title
- agenda

- [ ] **Step 4: Write the problem slides**

Cover:

- benchmark identity
- 15 components + top sink
- 32 decision variables
- two objectives and constraints
- canonical object flow

- [ ] **Step 5: Write the architecture slides**

Cover:

- `raw / union / llm` ladder
- top-level module boundary
- fair-comparison boundary
- proposal-time insertion point

- [ ] **Step 6: Write the LLM method slides**

Cover:

- shared operator registry
- controller state
- policy kernel / guardrails
- completed `L6` vs ongoing objective-balance direction

- [ ] **Step 7: Write the experiment slides**

Cover:

- `20x10` setup
- main metric table
- representative comparison figure/table
- current takeaways

- [ ] **Step 8: Write the closing slide**

Cover:

- current claims
- open work
- next steps

## Task 7: Verify Consistency Across Reports And Deck

**Files:**
- Modify: all files above as needed

- [ ] **Step 1: Run a terminology check across all written materials**

Run:

```bash
rg -n '四组件|four-component|panel_four|hot/cold|multicase|seed-23|seed-17|8 维' \
  /home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-0*.md \
  /home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report
```

Expected: no matches.

- [ ] **Step 2: Run a completed-evidence wording check**

Run:

```bash
rg -n 'objective-balance.*(完成|finished|verified)|latest llm 20x10|新版 llm 20x10 已完成' \
  /home/hymn/msfenicsx/docs/reports/2026-04-01-progress-report-0*.md \
  /home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report
```

Expected: no misleading claims that the objective-balance run is already complete.

- [ ] **Step 3: Compile the Beamer deck**

Run:

```powershell
Set-Location '\\wsl$\Ubuntu\home\hymn\msfenicsx\docs\reports\beamer\2026-04-16-s1-typical-progress-report'
& 'D:\MSCode\texlive\2025\bin\windows\latexmk.exe' -xelatex -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```

Expected: clean compile and a readable PDF.

- [ ] **Step 4: Render the PDF pages for visual inspection**

Run:

```bash
cd /home/hymn/msfenicsx/docs/reports/beamer/2026-04-16-s1-typical-progress-report
pdftoppm -png build/main.pdf build/rendered/page
```

Expected: around 20 main slides with readable tables and no clipped Chinese text.

- [ ] **Step 5: Do a final narrative spot-check**

Confirm:

- the deck reads as a group progress report, not a final paper-defense talk
- the problem definition is the clearest part of the deck
- no slide spends time explaining old benchmark history
- the representative experiment is explicitly labeled as a `20x10` matched-budget comparison
