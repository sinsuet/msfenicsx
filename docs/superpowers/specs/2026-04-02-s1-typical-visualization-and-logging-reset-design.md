# S1 Typical Visualization And Logging Reset Design

> Status: approved direction for replacing the current visualization and logging stack around the `s1_typical` mainline.
>
> This spec resets the active reporting surface around single-case physical-field pages, mixed-mode comparison views, and full LLM decision evidence. The previous `scenario_runs/optimizations/...` structure, template-comparison entrypoints, and retired four-component hot/cold visualization assets should be removed rather than preserved behind compatibility shims.

## 1. Goal

Define the next active logging and visualization mainline for `msfenicsx` so that:

- the only paper-facing run root is centered on `s1_typical`
- the primary viewing object is a single solved case with physical-field visualization
- mixed-mode runs can compare `raw`, `union`, and `llm` fairly under matched evaluation budgets
- `llm` runs preserve complete prompt and decision evidence, not just aggregate counts
- the same output tree can support:
  - scientific diagnosis
  - internal reporting
  - paper-figure extraction

This is a reset, not a patch on top of the current dashboard set.

## 2. Why The Current Stack Must Be Replaced

The current repository already has the right optimization and contract mainline:

- single-case `thermal_case`
- single-case `thermal_solution`
- single-case `evaluation_report`
- `s1_typical`
- `raw / union / llm`

However the current logging and visualization stack is still misaligned with that mainline because:

- experiment roots are still organized around `scenario_runs/optimizations/...`
- active dashboards are experiment-summary-first rather than single-case-first
- physical-field visualization is not yet a first-class artifact in the new workflow
- several reporting assets still bind directly to the retired four-component hot/cold benchmark
- the LLM route preserves useful traces, but does not yet expose a readable, end-to-end decision evidence surface

Therefore the active stack should be rebuilt around the new single-case `s1_typical` identity instead of being incrementally adapted.

## 3. Selected Design Direction

Three directions were considered.

### Option A: Patch the current experiment dashboards

Keep the current experiment-level dashboards as the primary entrypoint and add a few physical-field panels.

Pros:

- lowest short-term implementation cost

Cons:

- keeps the wrong primary viewing object
- keeps summary pages above solved cases
- encourages more compatibility glue around retired paths

Decision: reject.

### Option B: Rebuild around paper/report figure packs only

Prioritize export-ready report figures and keep logging secondary.

Pros:

- strong short-term reporting output

Cons:

- weak day-to-day diagnostic value
- does not solve the observability structure problem
- risks recreating another report-only pipeline

Decision: reject.

### Option C: Rebuild a single-case-first observability stack

Make solved-case physical-field pages the main entrypoint, treat mixed-mode comparison as a secondary layer, and require full LLM decision evidence.

Pros:

- matches the approved `s1_typical` mainline exactly
- supports both diagnosis and paper/report output
- gives `raw`, `union`, and `llm` one consistent run model
- makes physical fields, feasibility transitions, and controller evidence visible in one stack

Cons:

- requires coordinated path, logging, summary, and page changes
- requires deliberate removal of current dashboard assumptions

Decision: select this option.

## 4. Naming And Run Identity

The active run root should be:

```text
scenario_runs/s1_typical/<run_id>/
```

The following path families should be retired from the active workflow:

- `scenario_runs/optimizations/...`
- `scenario_runs/s1_typical/experiments/...`
- `scenario_runs/s1_typical/runs/...`

### 4.1 Run Id Format

Selected format:

```text
<MMDD_HHMM>__<mode_slug>
```

Examples:

- `0402_1530__raw`
- `0402_1530__union`
- `0402_1530__llm`
- `0402_1530__raw_union`
- `0402_1530__union_llm`
- `0402_1530__raw_union_llm`

Rules:

- time precision stops at minute resolution
- `mode_slug` must use a fixed order:
  - `raw`
  - `union`
  - `llm`
- single-mode runs contain exactly one mode directory
- mixed-mode runs contain two or three mode directories plus comparison artifacts

## 5. Run Root Structure

The active root structure should be:

```text
scenario_runs/s1_typical/<run_id>/
  manifest.json
  shared/
  comparison/          # present only when 2+ modes run together
  raw/                 # present only when raw is enabled
  union/               # present only when union is enabled
  llm/                 # present only when llm is enabled
```

### 5.1 Root Responsibilities

- `manifest.json`
  - identifies the run
  - lists enabled modes
  - records seed set, template, evaluation spec, optimization specs, timestamps, and provenance
- `shared/`
  - stores shared input snapshots and run-level indexes
  - stores benchmark-source cases and any common alignment metadata
- `comparison/`
  - stores cross-mode derived summaries, pages, and figures only
- `raw/`, `union/`, `llm/`
  - each store mode-specific logs, summaries, single-case pages, and representative artifacts

## 6. Mode Structure

Each mode directory should follow the same top-level shape:

```text
<mode>/
  manifest.json
  logs/
  summaries/
  pages/
  figures/
  reports/
  seeds/
```

Each seed bundle should follow:

```text
<mode>/seeds/seed-<n>/
  optimization_result.json
  logs/
  summaries/
  representatives/
```

Representative solved-case bundles should follow:

```text
<mode>/seeds/seed-<n>/representatives/<representative_id>/
  case.yaml
  solution.yaml
  evaluation.yaml
  logs/
  fields/
  summaries/
  figures/
  pages/
```

### 6.1 Representative Scope

The first implementation should generate solved-case pages for:

- `baseline`
- `first_feasible`
- `best_peak`
- `best_gradient`
- `knee`

Additional diagnostic points may be added later, but the first version should not try to render every evaluated candidate as a page.

## 7. Logging Architecture

The active stack should separate data into four layers.

### 7.1 Canonical Snapshots

This layer contains the truth-source contracts:

- `case.yaml`
- `solution.yaml`
- `evaluation.yaml`

Rules:

- preserve canonical schema meaning
- do not reshape these files around front-end needs
- do not use page-specific field names here

### 7.2 Runtime Logs

This layer contains process evidence:

- `evaluation_events.jsonl`
- `generation_summary.jsonl`
- `controller_trace.json`
- `operator_trace.json`
- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `llm_reflection_trace.jsonl`
- `llm_metrics.json`

Rules:

- retain high-fidelity run evidence
- support post hoc diagnosis
- prefer append-like trace semantics

### 7.3 Derived Summaries

This layer contains page- and report-facing summaries:

- `mode_summary.json`
- `seed_summary.json`
- `representative_summary.json`
- `constraint_summary.json`
- `field_view.json`
- `progress_timeline__seed-<n>.jsonl`
- `milestones__seed-<n>.json`
- `llm_decision_log.jsonl`
- `llm_key_decisions.json`

Rules:

- freely rebuildable from snapshots and runtime logs
- optimized for stable page rendering and report tables
- not treated as raw evidence

### 7.4 Rendered Outputs

This layer contains human-facing outputs:

- `pages/*.html`
- `figures/*.svg`
- `figures/*.png`
- `reports/*.md`
- `reports/*.html`

Rules:

- pages should read derived summaries, not reconstruct logic from scattered logs
- export figures should be reproducible from derived summaries

## 8. Single-Case Physical-Field Pages

Single-case pages are the primary viewing object of the new stack.

Each page should answer:

- what case this is
- how the `15` components and sink window are arranged
- what the temperature field and gradient field look like
- which components are hottest or most at risk
- which constraints are active or violated
- how the solver and evaluator behaved

### 8.1 Required Single-Case Sections

Each solved-case page should include:

1. identity and feasibility summary
2. layout view
3. temperature field view
4. temperature contour overlay
5. gradient-magnitude field view
6. component-level thermal table
7. global metrics and constraint margin table
8. solver diagnostics and evaluation detail
9. links back to the mode page and comparison views

### 8.2 Failure Case Pages

Failed candidates should still receive readable pages when they are part of selected representative or diagnostic sets.

Failure classes:

- cheap-constraint failure
- solver failure
- evaluation infeasible

Rules:

- cheap-constraint failures should show legality and budget reasons even without PDE fields
- solver failures should show diagnostics and failure stage
- evaluation-infeasible cases should still show fields and constraint margins if a solution exists

## 9. Field Data Contract For Visualization

The current `solution.yaml` summary fields are necessary but not sufficient for stable page rendering.

Therefore each single-case bundle should add page-facing field artifacts such as:

- `fields/temperature_grid.npz`
- `fields/gradient_magnitude_grid.npz`
- `summaries/field_view.json`

Responsibilities:

- `solution.yaml`
  - remains the canonical thermal-solution contract
- `fields/*.npz`
  - store regular-grid sampled data used by pages and cross-mode field comparison
- `field_view.json`
  - stores visualization metadata such as:
    - axis extents
    - color limits
    - contour levels
    - hotspot markers
    - sink segment geometry
    - component rectangles and labels

Rules:

- pages should not directly render FEniCSx DOF arrays
- cross-mode comparisons should use aligned grid resolution and color scales
- field-view metadata should make deterministic figure export straightforward

## 10. Mixed-Mode Comparison Layer

When two or more modes are executed in the same run, the root should include:

```text
comparison/
  manifest.json
  summaries/
  pages/
  figures/
  reports/
```

This layer should compare modes without replacing mode-local diagnosis.

### 10.1 Comparison Responsibilities

The comparison layer should answer:

- which modes ran together and under what matched inputs
- how they progressed under the same expensive-evaluation budget
- how their representative solutions compare
- how their physical fields compare
- how `union` and `llm` differ inside the shared operator registry

### 10.2 Required Comparison Pages

The first version should generate:

- `index.html`
- `progress.html`
- `fields.html`
- `pareto.html`
- `seeds.html`
- `controller.html` when both `union` and `llm` are present

### 10.3 Comparison Metrics And Tables

The comparison layer should include:

- mode scoreboard tables
- seed-aligned delta tables
- first-feasible comparison tables
- final feasible-count and feasible-rate tables
- final Pareto-size tables
- best-objective tables
- no-feasible-seed visibility tables

### 10.4 Progress Curves

The primary fairness axis should be `evaluation_index`, not just `generation_index`.

Required progress views include:

- best `temperature_max` so far vs `evaluation_index`
- best `temperature_gradient_rms` so far vs `evaluation_index`
- cumulative feasible count vs `evaluation_index`
- feasible rate so far vs `evaluation_index`
- Pareto size so far vs `evaluation_index`
- best total constraint violation so far vs `evaluation_index`
- first-feasible evaluation by seed

`generation_index` may still appear as a secondary grouping aid, but not as the sole fairness axis.

### 10.5 Field Comparison Rules

Cross-mode field comparisons must obey:

- aligned panel coordinates
- aligned grid resolution
- shared color scale within the same comparison panel
- explicit difference-field reference semantics such as `llm - union`
- representative alignment by shared semantic role:
  - `baseline`
  - `first_feasible`
  - `best_peak`
  - `best_gradient`
  - `knee`

If one mode lacks a given representative, the comparison should show the absence explicitly rather than invent a substitute.

## 11. LLM Complete Decision Evidence

`llm` must preserve complete decision evidence, not just compact runtime summaries.

### 11.1 Required Raw LLM Evidence

Each LLM-enabled seed should preserve:

- full request prompts
- full response payloads
- final controller selections
- operator execution records
- retry and fallback traces
- guardrail metadata
- reflection traces when enabled

The active required files are:

- `controller_trace.json`
- `operator_trace.json`
- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `llm_reflection_trace.jsonl`
- `llm_metrics.json`

### 11.2 Required Request Fields

Each request row should preserve at least:

- `generation_index`
- `evaluation_index`
- `provider`
- `model`
- `candidate_operator_ids`
- `original_candidate_operator_ids`
- `policy_phase`
- `policy_reason_codes`
- `guardrail`
- `system_prompt`
- `user_prompt`
- prompt-projection metadata representing the current state

### 11.3 Required Response Fields

Each response row should preserve at least:

- `generation_index`
- `evaluation_index`
- `selected_operator_id`
- `model_phase`
- `rationale`
- `raw_payload`
- `attempt_trace`
- `attempt_count`
- `retry_count`
- `elapsed_seconds`
- `fallback_used`
- `error`
- `guardrail`
- selected-entry metadata

## 12. LLM Decision Log And Key Decisions

Beyond raw evidence, `llm` should produce readable, structured decision summaries.

### 12.1 Full Decision Log

Add:

- `summaries/llm_decision_log.jsonl`

Each row should summarize one final LLM-side decision with fields such as:

- `decision_id`
- `generation_index`
- `evaluation_index`
- `policy_phase`
- `search_phase`
- `candidate_operator_ids`
- `selected_operator_id`
- `selected_operator_family`
- `selected_operator_role`
- `rationale`
- `fallback_used`
- `guardrail_reason_codes`
- `dominant_constraint_family_before`
- `total_constraint_violation_before`
- `feasible_before`
- `best_temperature_max_before`
- `best_gradient_rms_before`
- `current_state_summary`
- `operator_context_summary`
- references back to prompt, response, controller, and operator evidence

### 12.2 Key-Decision Summary

Add:

- `summaries/llm_key_decisions.json`

This file should contain only decisions worthy of explicit highlighting.

Trigger classes should include:

- `first_feasible_trigger`
- `feasible_recovery_trigger`
- `pareto_expansion_trigger`
- `peak_drop_trigger`
- `gradient_drop_trigger`
- `violation_collapse_trigger`
- `anti_collapse_trigger`
- `fallback_rescue_trigger`
- `operator_switch_trigger`

Each key decision should include:

- current state
- problem diagnosis
- available operator set
- selected operator
- effect after execution
- why the decision matters

## 13. LLM Pages

The LLM mode should include two dedicated pages beyond the shared mode pages:

- `pages/llm_decisions.html`
- `pages/llm_key_decisions.html`

### 13.1 Full Decision Page

`llm_decisions.html` should support:

- full chronological browsing
- filtering by phase
- filtering by operator family
- filtering by fallback usage
- filtering by key-decision status
- expandable display of:
  - current state summary
  - full prompt
  - full response
  - attempt trace
  - guardrail details
  - outcome deltas

### 13.2 Key-Decision Page

`llm_key_decisions.html` should render readable cards with these fixed sections:

1. current situation
2. why this was a problem
3. available operators and selected operator
4. effect after the decision
5. why this is an important improvement or risk event

Each key-decision card should link to:

- the associated single-case page
- the associated comparison progress point
- the raw request/response evidence

## 14. LLM Experiment Summary Document

Each LLM mode run should also generate a formal experiment summary document.

Required outputs:

- `reports/llm_experiment_summary.md`
- `reports/llm_experiment_summary.html`

When the run also includes comparison mode outputs, add:

- `comparison/reports/llm_vs_union_vs_raw_summary.md`

### 14.1 Required LLM Summary Sections

The LLM experiment summary should include:

- experiment overview
- core conclusions
- key improvement points
- key risk points
- overall LLM strategy pattern observed in the run
- important tables
- figure and page references
- risks and next-step recommendations

### 14.2 Required Tables

The LLM summary should include at least:

- experiment overview table
- three-mode result comparison table
- seed-aligned first-feasible table
- LLM runtime table
- LLM operator-selection table
- key-improvement table
- risk table

### 14.3 Generation Strategy

The first version should generate this summary from deterministic templates plus derived summaries.

Rules:

- do not rely on unconstrained free-form model narration for the primary report
- every claim should be traceable to saved summary data
- clearly distinguish:
  - validated conclusion
  - current limitation
  - next-step hypothesis

## 15. Comparison-Side LLM Positioning

Inside mixed-mode reporting, `llm` should be framed as:

- the same shared union action registry
- the same repaired single-case problem
- the same matched evaluation budget
- a different controller

Therefore:

- `raw / union / llm` comparison should focus on search outcomes and progress
- `union / llm` comparison should focus on controller behavior and decision value
- the controller-specific explanation page should center on `union vs llm`, not `raw vs llm`

## 16. CLI And Execution Model

Single-mode and mixed-mode execution should follow one run model.

Selected direction:

- one run id per invocation
- one shared run root under `scenario_runs/s1_typical/<run_id>/`
- one or more enabled modes inside that run
- one comparison layer only when 2+ modes are present

Optimization specs should remain mode-local:

- `s1_typical_raw.yaml`
- `s1_typical_union.yaml`
- `s1_typical_llm.yaml`

The runner should coordinate them into a single run root rather than forcing one spec to represent every mode.

## 17. Cleanup And Removal Rules

The reset should remove, not preserve, the current retired path assumptions.

Remove:

- `scenario_runs/optimizations/...`
- current `template_comparison` entrypoints
- current experiment-root assumptions tied to one mode per container
- retired four-component hot/cold figure-pack code and fixtures
- any dashboards that remain primary-entrypoint-first rather than single-case-first

Allowed reuse:

- compact telemetry logic that already captures valid evidence
- reusable plotting primitives
- summary-building logic after it is redirected into the new run structure

Not allowed:

- compatibility wrappers that keep the old tree alive as an active supported workflow
- hidden mirroring into old directories just to avoid migration

## 18. Testing Expectations

The reset should add or update focused tests for:

- run-id generation and mode-slug ordering
- single-mode root layout
- mixed-mode root layout
- representative bundle generation
- field-view derived summaries
- single-case page generation
- mixed-mode comparison page generation
- progress-summary generation
- LLM request/response field completeness
- LLM decision-log generation
- LLM key-decision trigger detection
- LLM experiment-summary document generation
- regression protection against re-creating old paths

## 19. First-Version Scope Control

The first version should deliver:

- the new run-root naming model
- unified single-mode and mixed-mode run orchestration
- single-case physical-field pages
- comparison pages:
  - `index`
  - `progress`
  - `fields`
  - `pareto`
  - `controller` when applicable
- full LLM decision evidence
- readable LLM decision pages
- the LLM experiment summary document
- removal of current obsolete path and dashboard assumptions

The first version should not attempt:

- all-candidate page generation
- complex browser-side editing
- animation-heavy field viewers
- unconstrained free-form auto-written reports as the primary evidence output

## 20. Expected Outcome

After this reset, the active visualization and logging identity of `msfenicsx` should be:

- one run root per execution
- solved-case pages as the primary view
- mixed-mode comparison as the secondary comparison layer
- physical fields visible and aligned with optimization outcomes
- LLM decisions fully inspectable from prompt to effect
- report-ready tables and figures produced from the same evidence tree

This should become the only supported paper-facing visualization and logging workflow for the `s1_typical` mainline.

## 21. Review Note

This spec was reviewed in the main session rather than through a separate spec-review subagent because the current session did not have explicit user authorization to spawn subagents. The intended substitute here is a deliberate self-review plus user review gate before implementation planning.
