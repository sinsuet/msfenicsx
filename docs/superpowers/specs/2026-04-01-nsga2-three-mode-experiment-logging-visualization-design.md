# NSGA-II Three-Mode Experiment Logging and Visualization Design

> Status: approved design direction for the paper-facing `NSGA-II` three-mode experiment system.
>
> This spec supersedes the earlier assumption that `L1` remained a future-only extension point. As of 2026-04-01, the repository already contains a working `union-llm` controller path with OpenAI-compatible transport, controller-side state building, diagnostics, and live run artifacts. The logging and visualization system must therefore be designed for three active modes:
>
> - `nsga2_raw`
> - `nsga2_union`
> - `nsga2_llm`

## 1. Goal

Define a clean experiment logging and visualization system for the paper-facing `NSGA-II` line so that:

- each experiment directory represents exactly one mode
- all three active modes use a shared experiment backbone where appropriate
- `union` and `llm` share one controller-guided mechanism layer
- `llm` adds only the controller-source and runtime layer on top of the shared union mechanism layer
- logs, summaries, dashboards, and comparisons align with the paper ladder:
  - raw `NSGA-II`
  - union-uniform `NSGA-II`
  - union-`LLM` `NSGA-II`

## 2. Current Repository Reality

The current repository state now matters for this design.

### 2.1 Raw Mode Is Stable

The paper-facing classical baseline remains plain native `NSGA-II` under:

- `algorithm.mode: raw`
- no `operator_control`

This path already writes:

- `optimization_result.json`
- `pareto_front.json`
- representative bundles

### 2.2 Union Mode Is Stable

The paper-facing non-`LLM` hybrid rung remains:

- `algorithm.mode: union`
- `operator_control.controller: random_uniform`

This path already writes canonical mechanism traces:

- `controller_trace.json`
- `operator_trace.json`

### 2.3 LLM Mode Is Already Implemented

The paper-facing `L1` path is no longer a placeholder. The repository already contains:

- an OpenAI-compatible client layer
- `responses_native` and `chat_compatible_json` transport support
- an `LLMOperatorController`
- domain-grounded controller-state construction
- a reusable policy-kernel layer with pre-feasible guardrails and reset logic
- replay and controller-trace diagnostics tooling
- live and smoke optimization specs for multiple providers/models
- run artifacts that already include:
  - `llm_request_trace.jsonl`
  - `llm_response_trace.jsonl`
  - `llm_metrics.json`
  - `controller_trace_summary.json` in diagnostic workflows

Therefore the design must treat `nsga2_llm` as a first-class mode rather than as a later add-on.

## 3. Canonical Mode Identity

The experiment system should use exactly three paper-facing mode ids:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

These are experiment-system identities, not replacements for the technical optimizer contract.

Technical mapping:

- `nsga2_raw`
  - `algorithm.mode = raw`
- `nsga2_union`
  - `algorithm.mode = union`
  - `operator_control.controller = random_uniform`
- `nsga2_llm`
  - `algorithm.mode = union`
  - `operator_control.controller = llm`

## 4. Experiment Directory Model

### 4.1 Template-First Layout

The runtime root remains `scenario_runs/`.

The paper-facing experiment structure should become:

```text
scenario_runs/
  <scenario_template_id>/
    experiments/
      nsga2_raw__MMDD_HHMM/
      nsga2_union__MMDD_HHMM/
      nsga2_llm__MMDD_HHMM/
```

If multiple experiments of the same mode start within the same minute, append a sequence suffix:

```text
nsga2_union__0401_1430__01
nsga2_union__0401_1430__02
```

### 4.2 Single-Mode Container Rule

Each experiment directory contains exactly one mode.

This is intentional.

- raw, union, and llm experiments remain physically separate
- later comparisons are generated from multiple single-mode experiment directories
- `nsga2_llm` can retain extra provider/runtime artifacts without contaminating `nsga2_raw`

### 4.3 Experiment Interior

Each single-mode experiment directory should use:

```text
<experiment_dir>/
  manifest.json
  spec_snapshot/
  runs/
    seed-11/
    seed-17/
    seed-23/
  summaries/
  figures/
  dashboards/
  logs/
  representatives/
```

Interpretation:

- `manifest.json`
  - mode-level entrypoint
- `spec_snapshot/`
  - frozen template/spec/profile inputs used by this experiment
- `runs/`
  - atomic seed runs
- `summaries/`
  - multi-seed compact summaries for dashboards and paper tables
- `figures/`
  - exported plots and figure assets
- `dashboards/`
  - HTML analysis pages
- `logs/`
  - experiment-level indexing and analysis helpers
- `representatives/`
  - experiment-level representative solution bundles if needed

## 5. Run-Level Artifact Contract

### 5.1 Shared Run-Level Files For All Three Modes

Every seed run should expose the same shared experiment backbone:

- `manifest.json`
- `optimization_result.json`
- `pareto_front.json`
- `evaluation_events.jsonl`
- `generation_summary.jsonl`
- `representatives/`

The shared run-level contract must remain valid for:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

### 5.2 Why New Shared Sidecars Are Still Needed

Even though `optimization_result.json` already contains `history`, it is too heavy and too coupled to serve as the main dashboard data source.

The new shared sidecars should provide:

- compact, stable, dashboard-oriented summaries
- a common event vocabulary across all three modes
- direct compatibility with multi-seed aggregation

### 5.3 `evaluation_events.jsonl`

This file is the canonical compact evaluation-level telemetry for all modes.

Each row should include at least:

- `run_id`
- `mode_id`
- `seed`
- `generation_index`
- `evaluation_index`
- `source`
- `decision_vector`
- `objective_values`
- `constraint_values`
- `feasible`
- `total_constraint_violation`
- `dominant_violation_constraint_id`
- `dominant_violation_constraint_family`
- `violation_count`
- `entered_feasible_region`
- `preserved_feasibility`
- `pareto_membership_after_eval`
- `failure_reason`

This file does not replace `optimization_result.json`.
It is the compact experimental event stream derived from it.

### 5.4 `generation_summary.jsonl`

This file is the canonical generation-level compact summary for all modes.

Each row should include at least:

- `run_id`
- `mode_id`
- `seed`
- `generation_index`
- `num_evaluations_so_far`
- `feasible_fraction`
- `best_total_constraint_violation`
- `best_hot_pa_peak`
- `best_cold_battery_min`
- `best_radiator_resource`
- `pareto_size`
- `new_feasible_entries`
- `new_pareto_entries`

## 6. Controller-Guided Mechanism Layer

### 6.1 Canonical Raw Mechanism Logs

The repository already has working mechanism trace names:

- `controller_trace.json`
- `operator_trace.json`

These should remain the canonical raw mechanism logs for controller-guided union runs.

Do not replace them with a second parallel raw naming system such as:

- `decision_events.jsonl`
- `proposal_events.jsonl`

The repository should instead formalize the existing traces as the raw mechanism contract and build compact summaries above them.

### 6.2 Which Modes Use This Layer

This mechanism layer applies to:

- `nsga2_union`
- `nsga2_llm`

It does not apply to `nsga2_raw`, because raw mode does not have controller-mediated action selection semantics.

### 6.3 Trace Semantics

`controller_trace.json` is the canonical record of:

- candidate action set
- selected operator id
- controller id
- phase
- rationale
- guardrail metadata
- fallback metadata
- provider/model metadata when applicable

`operator_trace.json` is the canonical record of:

- operator id
- parent vectors
- proposal vector
- repaired vector in metadata
- decision index
- sibling structure for native multi-child events

### 6.4 Required Compact Summaries Above The Mechanism Layer

The experiment system should build:

- `summaries/controller_trace_summary.json`
- `summaries/operator_summary.json`
- `summaries/regime_operator_summary.json`

These files are derived summaries, not replacements for the raw traces.

## 7. LLM-Specific Layer

### 7.1 Canonical LLM Raw Logs

`nsga2_llm` should retain the current raw LLM-sidecar files:

- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `llm_metrics.json`

These are the correct raw evidence boundary for:

- prompt content
- candidate-set shaping
- model/provider identity
- runtime behavior
- fallback behavior

### 7.2 Current Reflection Status

The current codebase already exposes:

- `reflection_trace`
- `llm_reflection_trace.jsonl`
- memory-related configuration fields such as `reflection_interval`

However the reflection path is not yet fully producing stable persisted reflection rows in the same way that request/response traces already do.

Therefore:

- `llm_reflection_trace.jsonl` should remain an optional artifact for now
- the experiment system must not assume it always exists
- visualization and summaries must treat it as conditional until reflection persistence is fully stabilized

### 7.3 LLM Compact Summaries To Add

The formal experiment layer should add:

- `summaries/llm_runtime_summary.json`
- `summaries/llm_decision_summary.json`
- `summaries/llm_prompt_summary.json`

Later, once reflection rows are stable:

- `summaries/llm_reflection_summary.json`

### 7.4 Metrics That Must Be Strengthened

`llm_metrics.json` currently captures only a small runtime core.

The experiment system should expand the LLM compact metric surface to include:

- `request_count`
- `response_count`
- `fallback_count`
- `retry_count`
- `invalid_response_count`
- `schema_invalid_count`
- `semantic_invalid_count`
- `elapsed_seconds_total`
- `elapsed_seconds_avg`
- `elapsed_seconds_max`
- `provider`
- `model`
- `capability_profile`
- `performance_profile`
- token or usage fields when the transport exposes them
- estimated cost fields when the transport exposes them

## 8. Experiment-Level Summary Contract

### 8.1 Shared Summaries For All Modes

Every single-mode experiment directory should contain:

- `summaries/run_index.json`
- `summaries/aggregate_summary.json`
- `summaries/constraint_summary.json`
- `summaries/generation_summary.json`

### 8.2 `run_index.json`

This file indexes all seed runs in the experiment.

Each row should include:

- `seed`
- `run_dir`
- `run_id`
- `mode_id`
- `num_evaluations`
- `feasible_rate`
- `first_feasible_eval`
- `pareto_size`
- `best_hot_pa_peak`
- `best_cold_battery_min`
- `best_radiator_resource`
- `best_total_cv_among_infeasible`
- booleans for presence of:
  - `controller_trace`
  - `operator_trace`
  - `llm_request_trace`
  - `llm_response_trace`

### 8.3 `aggregate_summary.json`

This file stores experiment-level multi-seed aggregation:

- number of runs
- list of seeds
- mean / median / std / min / max for core paper metrics
- failed runs
- no-feasible-solution runs

### 8.4 `constraint_summary.json`

This file stores experiment-level constraint behavior:

- per-constraint activation frequency
- per-constraint mean violation
- dominant-constraint frequency
- dominant-constraint family distribution
- pre-feasible versus post-feasible constraint pressure split

### 8.5 `generation_summary.json`

This file stores experiment-level aggregated generation curves:

- mean feasible fraction by generation
- mean best total CV by generation
- mean best objective values by generation
- mean Pareto size by generation

### 8.6 Mechanism Summaries For `nsga2_union` And `nsga2_llm`

These modes should additionally build:

- `summaries/operator_summary.json`
- `summaries/regime_operator_summary.json`
- `summaries/controller_trace_summary.json`

### 8.7 Additional LLM Summaries For `nsga2_llm`

This mode should additionally build:

- `summaries/llm_runtime_summary.json`
- `summaries/llm_decision_summary.json`
- `summaries/llm_prompt_summary.json`
- optional `summaries/llm_reflection_summary.json`

## 9. Visualization Contract

### 9.1 Shared Overview Page

Every mode should produce:

- `dashboards/overview.html`

This page should display:

- experiment metadata
- seed index table
- feasible rate by seed
- first feasible evaluation by seed
- Pareto size by seed
- best total CV by seed
- generation curves
- constraint summary blocks

### 9.2 Shared Mechanism Page For Controller-Guided Modes

`nsga2_union` and `nsga2_llm` should both produce:

- `dashboards/mechanism.html`

This page should display:

- operator counts
- operator mean total violation delta
- feasible-entry and feasible-preservation counts
- Pareto-hit behavior
- regime versus operator heatmaps
- repair impact summaries

This page is shared because both modes operate on the same fixed union action registry.

### 9.3 LLM-Specific Page

`nsga2_llm` should additionally produce:

- `dashboards/llm.html`

This page should display:

- provider / model / capability profile
- request count / response count / fallback count / retry count
- elapsed time summaries
- selected operator timeline with controller-phase context
- prompt-state summary blocks
- replay and diagnostics summary blocks when present
- optional reflection blocks when reflection traces exist

### 9.4 Comparison Pages

Comparisons should not live inside single-mode experiment directories.

Template-level comparison outputs should instead be generated under the template root, for example:

```text
scenario_runs/<scenario_template_id>/comparisons/
  raw-vs-union/
  union-vs-llm/
  raw-vs-union-vs-llm/
```

This preserves the single-mode experiment-container rule while still supporting:

- `raw` vs `union`
- `union` vs `llm`
- three-mode paper overviews

## 10. Required Changes Relative To Current LLM Implementation

### 10.1 Promote Existing Trace Files To Official Contracts

Current raw mechanism and LLM trace files should be explicitly recognized as official experiment artifacts:

- `controller_trace.json`
- `operator_trace.json`
- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `llm_metrics.json`

### 10.2 Add Shared Compact Event Layers

All three modes still need:

- `evaluation_events.jsonl`
- `generation_summary.jsonl`

These remain necessary even though union/llm already have richer mechanism traces.

### 10.3 Add Formal Multi-Seed Experiment Summaries

The current repository has ad hoc comparison summaries and diagnostics, but it does not yet have a canonical experiment-summary layer under a single-mode experiment container.

That layer must now be built.

### 10.4 Strengthen LLM Runtime Metrics

The current `llm_metrics.json` is too small for the intended analysis.

It must be expanded or supplemented so dashboards and paper tables can use stable, compact metrics without reparsing raw traces.

### 10.5 Normalize Phase And Rationale Analysis

The current LLM path technically supports:

- `phase`
- `rationale`

but real traces still often contain empty model-provided values.

The experiment system should therefore treat:

- policy-kernel phase
- controller-returned phase
- trace-derived analysis phase

as related but distinct concepts, and summaries must normalize them explicitly rather than assuming the raw model text is always complete.

### 10.6 Keep Reflection Optional Until It Is Truly Stable

Reflection should remain visible in the design, but the formal system should not pretend that reflection logging is already at the same stability level as request/response traces.

## 11. Non-Goals

This design does not require:

- changing the optimizer-layer fairness contract between the three paper-facing modes
- changing the fixed union action registry
- replacing `controller_trace.json` or `operator_trace.json` with a second parallel raw-trace format
- forcing `nsga2_raw` to carry fake controller semantics
- claiming that reflection is already a fully stable required artifact
- broadening this paper-facing design to the exploratory multi-backbone matrix track

## 12. Acceptance Criteria

This design is acceptable only if:

1. the experiment system has exactly three official paper-facing mode ids:
   - `nsga2_raw`
   - `nsga2_union`
   - `nsga2_llm`
2. the directory model is template-first and single-mode-per-experiment
3. all three modes expose the same shared run-level experiment backbone
4. `nsga2_union` and `nsga2_llm` share the same canonical raw mechanism logs:
   - `controller_trace.json`
   - `operator_trace.json`
5. `nsga2_llm` keeps its own raw controller-source artifacts:
   - `llm_request_trace.jsonl`
   - `llm_response_trace.jsonl`
   - `llm_metrics.json`
6. the experiment layer adds compact shared summaries and dashboards rather than relying directly on heavy raw files
7. `overview.html` exists for all three modes
8. `mechanism.html` exists for `nsga2_union` and `nsga2_llm`
9. `llm.html` exists for `nsga2_llm`
10. template-level comparison outputs can compare:
    - `raw` vs `union`
    - `union` vs `llm`
    - all three together

## 13. User Review Note

This spec reflects the updated repository reality after the `L1` controller implementation landed. It is intentionally written so the next implementation plan can focus on:

- formalizing the experiment container layout
- upgrading existing artifacts into a stable experiment schema
- building the first real three-mode dashboards

The spec-document review subagent loop described by the superpowers workflow was not used here because this session is operating under tool constraints that disallow unrequested delegation. The document should therefore be treated as main-thread reviewed and ready for user review before implementation planning.
