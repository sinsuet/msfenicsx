# S1 Typical LLM Controller Recovery Handoff

## 1. Purpose

This document is a Claude-facing handoff for the current `s1_typical` `nsga2_llm` recovery line in `msfenicsx`.

It records:

- the active paper boundary
- the exact problem background
- the repair sequence already completed
- the current measured results
- the remaining bottleneck
- the recommended next optimization direction
- the key files, docs, commands, and artifact paths needed to continue work

This handoff is written for continuation inside the same worktree:

- repo root: `/home/hymn/msfenicsx`
- active worktree: `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery`

---

## 2. Repository And Experiment Boundary

The active repository guidance is in:

- `AGENTS.md`

The most important constraints from `AGENTS.md` for this line are:

- the only active paper-facing benchmark is `s1_typical`
- the paper ladder is:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`
- `union` and `llm` must stay on the same problem, same operator pool, same repair, same solver, same evaluation chain
- the only controller difference between `union` and `llm` should be the controller itself
- active canonical inputs are:
  - `scenarios/templates/s1_typical.yaml`
  - `scenarios/evaluation/s1_typical_eval.yaml`
  - `scenarios/optimization/s1_typical_raw.yaml`
  - `scenarios/optimization/s1_typical_union.yaml`
  - `scenarios/optimization/s1_typical_llm.yaml`
- canonical environment is:
  - WSL2 Ubuntu
  - `conda run -n msfenicsx ...`
- active output layout is:
  - `scenario_runs/s1_typical/<MMDD_HHMM>__<mode_slug>/`

This means the controller recovery work must remain paper-safe:

- no change to the benchmark problem
- no change to repair
- no change to cheap constraints
- no change to PDE solve
- no change to evaluation spec
- no benchmark-specific prompt hacks
- no operator-pool mismatch between `union` and `llm`

---

## 3. Problem Background

### 3.1 Benchmark Identity

`s1_typical` is the current single-case paper benchmark:

- one operating case
- fifteen fixed named components
- optimize only `x/y` for all fifteen components
- no optimized rotation
- `32` decision variables
- two objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- one hard sink-span budget:
  - `case.total_radiator_span <= radiator_span_max`

### 3.2 Paper Narrative

The intended paper narrative is:

- `raw` is the matched native baseline
- `union` adds the shared mixed action registry on the same problem
- `llm` uses the same mixed action registry as `union`
- the only extra ingredient in `llm` is the LLM-guided controller policy

The core comparison story is therefore:

- same problem
- same operator pool
- same expensive evaluation chain
- only controller policy changes

### 3.3 LLM Route Context

The current live `llm` spec is:

- `scenarios/optimization/s1_typical_llm.yaml`

Key current controller config in that spec:

- provider: `openai-compatible`
- model: `gpt-5.4`
- base URL: `https://rust.cat/v1`
- capability profile: `chat_compatible_json`
- performance profile: `balanced`
- `memory.recent_window = 32`
- `retry.timeout_seconds = 45`

The earlier transport debugging already established that the present issue is no longer API transport instability. The main remaining issue is controller policy quality.

---

## 4. Relevant Existing Reports And Docs

These are the most useful documents to read before continuing:

- `AGENTS.md`
  - authoritative repo and experiment boundary
- `docs/superpowers/plans/2026-04-15-s1-typical-llm-l5-full-recovery.md`
  - the L5 recovery plan that this work followed
- `docs/reports/2026-04-01-progress-report-03-llm-union-method.md`
  - earlier LLM/union method framing
- `docs/reports/2026-04-10-s1-typical-end-to-end-flow-and-seed11-walkthrough.md`
  - end-to-end benchmark and artifact flow
- `docs/reports/R68_msfenicsx_nsga2_union_mechanism_analysis_20260328.md`
  - union mechanism interpretation
- `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`
  - literature and novelty framing for the LLM controller line
- `docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md`
  - benchmark mainline reset design
- `docs/superpowers/plans/2026-04-02-s1-typical-mainline-reset.md`
  - active benchmark workflow plan

---

## 5. Baseline Results Before This Recovery Line

These runs are the core baseline references.

### 5.1 Raw Full

Artifact:

- `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/raw/seeds/seed-11/optimization_result.json`

Metrics:

- feasible rate: `0.763671875`
- pareto size: `5`
- first feasible eval: `3`
- best peak on Pareto: `304.4342415107047`
- best gradient on Pareto: `9.659754416176332`

### 5.2 Union Full

Artifact:

- `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/union/seeds/seed-11/optimization_result.json`

Metrics:

- feasible rate: `0.822265625`
- pareto size: `7`
- first feasible eval: `3`
- best peak on Pareto: `305.8793871745624`
- best gradient on Pareto: `10.999479788598341`

### 5.3 Old LLM Full

Artifact:

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_0015__llm/optimization_result.json`

Metrics:

- feasible rate: `0.806640625`
- pareto size: `5`
- first feasible eval: `3`
- best peak on Pareto: `305.4234947390854`
- best gradient on Pareto: `10.814851282343104`

Interpretation:

- `old full llm` was competitive with `union` on some fronts
- but its controller behavior still had obvious route collapse and recovery pathologies

---

## 6. Recovery Sequence Already Completed

The work followed an incremental `L2 -> L3 -> L4 -> L5` recovery pattern.

### 6.1 Pre-L5 Important Fixed Issues

#### A. `.env` / API Config Recovery

Goal:

- make the OpenAI-compatible client reliably pick up runtime credentials and base URL without re-implementing the transport stack

Relevant files:

- `llm/openai_compatible/config.py`
- `llm/openai_compatible/client.py`

Outcome:

- the transport path is now stable on the current platform
- the latest successful runs do not show fallback/retry/schema-invalid problems

#### B. Expand Route-Family Collapse

Symptom:

- `post_feasible_expand` would collapse into one semantic route family, which made the `llm` controller effectively non-diverse

Primary file:

- `optimizers/operator_pool/policy_kernel.py`

Outcome:

- route-family diversity in `expand` was restored

#### C. Recover Single-Semantic Collapse

Symptom:

- `post_feasible_recover` could collapse into a single semantic operator instead of preserving a stable floor

Primary file:

- `optimizers/operator_pool/policy_kernel.py`

Outcome:

- recover now keeps a stable floor plus limited semantic visibility

#### D. Hard Recover Priority In Arbitration

Symptom:

- `recover` previously had an overly hard priority and suppressed `expand` even when frontier stagnation suggested expansion should win

Primary file:

- `optimizers/operator_pool/domain_state.py`

Important new progress-state fields added:

- `stable_preservation_streak`
- `new_dominant_violation_family`

Outcome:

- recover no longer wins unconditionally
- expand can win when regression pressure does not dominate and frontier stagnation is high

---

## 7. L5 Work Completed In This Session

### 7.1 L5 Objective

L5 focused on the next bottleneck after L4:

- semantic routes were visible
- but semantic routes were not converting well enough into frontier gains
- and recent `expand` allocations could still spend too much effort on regression-dominant semantic routes

So L5 implemented:

- recent `post_feasible_expand` budget accounting
- semantic route throttling inside `post_feasible_expand`
- controller-state / prompt metadata for expand budget
- controller-trace diagnostics for expand-family outcome attribution

### 7.2 Files Modified In L5

Primary implementation files:

- `optimizers/operator_pool/route_families.py`
- `optimizers/operator_pool/reflection.py`
- `optimizers/operator_pool/state_builder.py`
- `optimizers/operator_pool/policy_kernel.py`
- `optimizers/operator_pool/llm_controller.py`
- `optimizers/operator_pool/diagnostics.py`

Tests added or updated:

- `tests/optimizers/test_llm_policy_kernel.py`
- `tests/optimizers/test_llm_controller.py`
- `tests/optimizers/test_llm_controller_state.py`
- `tests/optimizers/test_optimizer_cli.py`

### 7.3 What L5 Added Semantically

#### A. Recent Expand Credit Accounting

Per route family, L5 now computes recent:

- expand selection count
- expand feasible preservation count
- expand feasible regression count
- expand frontier add count

This is derived from controller trace plus operator outcome history, not from hand-coded benchmark exceptions.

#### B. Expand Budget Status

Each route family gets a compact budget state:

- `preferred`
- `neutral`
- `throttled`

The current scoring logic is intentionally simple and local:

- frontier credit helps
- preserve credit helps
- regression credit hurts more strongly

#### C. Phase-Local Enforcement

Budget throttling is only enforced in:

- `post_feasible_expand`

It does not globally punish the route in other phases.

#### D. Prompt / State Exposure

Prompt-facing operator rows now expose:

- `recent_expand_preserve_credit`
- `recent_expand_regression_credit`
- `recent_expand_frontier_credit`
- `expand_budget_status`

#### E. Diagnostics Upgrade

`controller_trace_summary.json` now reports:

- `expand_family_outcomes`
- route-family-level frontier/preserve/regression counts
- budget-related LLM trace summaries where available

---

## 8. Verification Already Run

### 8.1 Focused L5 Red-Green Tests

The following new tests were written, failed first, and then passed after implementation:

- `test_post_feasible_expand_throttles_semantic_route_with_recent_regression_and_no_frontier_credit`
- `test_llm_controller_expand_request_marks_regression_dominant_semantic_route_as_throttled`
- `test_build_controller_state_emits_expand_budget_credit_fields`
- diagnostics-side tests for expand-family outcomes and budget reporting

### 8.2 Fresh Passing Verification

Fresh passing command:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_prompt_projection.py -v
```

Observed result:

- `44 passed`

Additional diagnostics verification:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_analyze_controller_trace_accepts_optional_operator_and_request_sidecars \
  tests/optimizers/test_optimizer_cli.py::test_analyze_controller_trace_reports_expand_family_outcomes_and_budget_throttling -v
```

Observed result:

- `2 passed`

---

## 9. Live Runs Performed

### 9.1 L3 Mid Reference

Artifact root:

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1325__llm_l3_mid_smoke`

Important metrics:

- feasible rate: `0.7916666666666666`
- pareto size: `3`
- best peak: `306.66234519640375`
- best gradient: `11.713450971888767`
- semantic frontier add count: `8`
- expand route-family entropy: `0.49715018363696706`

Interpretation:

- semantic conversion existed
- but route-family diversity was poor

### 9.2 L4 v4 Mid Reference

Artifact root:

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1622__llm_l4_mid_smoke_v4`

Important metrics:

- feasible rate: `0.7638888888888888`
- pareto size: `4`
- best peak: `307.33766038106785`
- best gradient: `11.89204580316632`
- semantic frontier add count: `0`
- expand route-family entropy: `1.8879185026711327`

Interpretation:

- diversity was fixed
- but semantic routes stopped converting to frontier improvements

### 9.3 L5 Mid Smoke

Artifact root:

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1758__llm_l5_mid_smoke`

Key metrics:

- feasible rate: `0.8611111111111112`
- pareto size: `4`
- first feasible eval: `3`
- best peak on Pareto: `306.8539189510191`
- best gradient on Pareto: `12.282698296960433`

Controller summary:

- semantic frontier add count: `1`
- semantic feasible preservation count: `16`
- semantic selection rate: `0.3333333333333333`
- expand route-family entropy: `1.497449071065274`
- post-feasible frontier adds: `7`
- post-feasible feasible regressions: `6`
- post-feasible feasible preservations: `50`

LLM runtime:

- request count: `63`
- fallback count: `0`
- retry count: `0`
- invalid count: `0`
- elapsed seconds avg: `2.995983225523892`

Interpretation:

- this was a real improvement over `L4 v4`
- the chain was stable
- the controller became more conservative in a helpful way at mid budget

### 9.4 L5 Full Run

Artifact root:

- `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm`

Important output files:

- `optimization_result.json`
- `llm_metrics.json`
- `controller_trace.json`
- `controller_trace_summary.json`
- `operator_trace.json`
- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`

Core metrics:

- feasible rate: `0.77734375`
- pareto size: `4`
- first feasible eval: `3`
- best peak on Pareto: `305.8607837367596`
- best gradient on Pareto: `10.552823033413512`

Representative points:

- min peak:
  - eval `168`
  - `temp_max = 305.8607837367596`
  - `grad_rms = 12.540741252937428`
  - `sink_span = 0.48`
  - span budget violation `0.0`
- min gradient:
  - eval `139`
  - `temp_max = 316.8952990857221`
  - `grad_rms = 10.552823033413512`
  - `sink_span = 0.15000000000000002`
  - span budget violation `-0.32999999999999996`
- knee:
  - eval `265`
  - `temp_max = 312.74547654641117`
  - `grad_rms = 11.284475416677413`
  - `sink_span = 0.1901848901252636`
  - span budget violation `-0.28981510987473635`

LLM runtime:

- request count: `480`
- response count: `480`
- fallback count: `0`
- retry count: `0`
- invalid response count: `0`
- elapsed seconds avg: `3.213841228168739`
- elapsed seconds max: `5.124769740001284`

This confirms:

- the current transport path is usable
- the full run is not currently failing because of network/response instability

---

## 10. Comparative Interpretation

### 10.1 New Full L5 Versus Old Full LLM

Old full LLM:

- feasible rate: `0.806640625`
- pareto size: `5`
- best peak: `305.4234947390854`
- best gradient: `10.814851282343104`

New full L5:

- feasible rate: `0.77734375`
- pareto size: `4`
- best peak: `305.8607837367596`
- best gradient: `10.552823033413512`

Interpretation:

- L5 improved the best gradient endpoint
- L5 improved live response latency materially
- but L5 made full-run feasible rate and Pareto size worse
- L5 also slightly worsened the best peak endpoint

### 10.2 New Full L5 Versus Union Full

Union full:

- feasible rate: `0.822265625`
- pareto size: `7`
- best peak: `305.8793871745624`
- best gradient: `10.999479788598341`

New L5 full:

- feasible rate is worse than `union`
- pareto size is worse than `union`
- best peak is almost the same and very slightly better than `union`
- best gradient is better than `union`

Interpretation:

- L5 full does not yet beat `union` overall
- it is currently more like a gradient-biased, less stable controller

### 10.3 New Full L5 Versus Raw Full

Raw full:

- feasible rate: `0.763671875`
- pareto size: `5`
- best peak: `304.4342415107047`
- best gradient: `9.659754416176332`

Interpretation:

- L5 full is slightly better than `raw` on feasible rate
- but `raw` still dominates the extreme objective endpoints

---

## 11. Controller-Level Diagnosis

### 11.1 What L5 Actually Improved

Compared with `old full llm`, L5 improved controller richness:

- semantic selection rate:
  - old full: `0.26804123711340205`
  - L5 full: `0.6416666666666667`
- semantic frontier add count:
  - old full: `6`
  - L5 full: `9`
- expand route-family entropy:
  - old full: `0.9971803988942642`
  - L5 full: `1.6184337381383895`
- stable vs semantic Pareto ownership:
  - old full: `semantic 1 / stable 4`
  - L5 full: `semantic 2 / stable 2`

This means:

- the L5 controller is genuinely changing search behavior
- it is not just a cosmetic prompt change
- it is producing a more semantically active and more diverse expand policy

### 11.2 What L5 Broke Or Overcorrected

The main new pathology is expand over-saturation.

Policy-phase counts from request trace:

- old full:
  - `post_feasible_recover = 277`
  - `post_feasible_expand = 192`
- L5 full:
  - `post_feasible_recover = 64`
  - `post_feasible_expand = 416`

This is the clearest structural signal in the whole recovery line.

Interpretation:

- old full spent too much time in recover
- L5 full overcorrected and spent far too much time in expand

The downstream effect is also visible in:

- `evaluations_since_frontier_add`
  - old full: `22`
  - L5 full: `189`

So L5 full can keep expanding long after frontier growth has effectively stalled.

### 11.3 What The New Diagnostics Show

From L5 full `controller_trace_summary.json`:

- `post_feasible_expand_semantic_budget` fired `28` times
- `post_feasible_expand_route_family_dominance_cap` fired `158` times
- `post_feasible_expand_frontier_bias` fired `357` times

This means the budget logic is real and active.

But the same summary also shows:

- `expand_budget_throttled_operator_counts = {}`
- `expand_budget_throttled_route_family_counts = {}`

This apparent contradiction is explained by the trace structure:

- the budget suppression is happening before the final prompt candidate set is serialized
- so the model only sees the post-filter candidate set
- it does not explicitly see the throttled candidates that were suppressed

This is important because it means the controller-state / prompt adaptation is still incomplete:

- local policy knows some routes were throttled
- the prompt-side view does not make that fully explicit

### 11.4 Expand-Family Outcome Pattern In L5 Full

L5 full expand-family outcomes:

- `hotspot_spread`
  - selection count: `188`
  - frontier adds: `6`
  - feasible preservations: `149`
  - feasible regressions: `33`
- `congestion_relief`
  - selection count: `89`
  - frontier adds: `1`
  - feasible preservations: `65`
  - feasible regressions: `23`
- `sink_retarget`
  - selection count: `7`
  - frontier adds: `0`
  - feasible preservations: `3`
  - feasible regressions: `4`
- `stable_local`
  - selection count: `132`
  - frontier adds: `2`
  - feasible preservations: `118`
  - feasible regressions: `12`

Interpretation:

- `hotspot_spread` still drives most semantic frontier gains
- `congestion_relief` is active but not very efficient
- `sink_retarget` is weak in the current full run
- the controller is still willing to spend too much budget in expand even when frontier yield has gone down

---

## 12. Current Main Problem

The current main problem is no longer:

- API transport instability
- schema invalid LLM responses
- route-family collapse
- recover single-semantic monopoly
- hard recover priority

The current main problem is:

- the controller now over-allocates to `post_feasible_expand`
- it does not exit `expand` quickly enough after semantic frontier yield saturates
- the current budget logic filters poor semantic routes locally, but does not yet solve phase-level over-expansion

In one sentence:

L5 moved the bottleneck from "expand is too weak and too collapsed" to "expand is now structurally overused and exit control is too weak."

---

## 13. Recommended Next Step: L6

The recommended next line is an `L6` controller package.

### 13.1 Primary Recommendation

Add an expand saturation governor.

This should operate above per-route budgeting and decide when to stop staying in `post_feasible_expand`.

Recommended direction:

- monitor consecutive or cumulative `expand` decisions without meaningful frontier gain
- when expand stagnation crosses a threshold, demote the regime back toward:
  - `post_feasible_preserve`
  - or `post_feasible_recover`
- do this using local controller state, not benchmark-specific hacks

### 13.2 Secondary Recommendation

Expose suppressed candidates explicitly in prompt metadata.

Right now the model sees only:

- filtered candidate set

It should also see something like:

- original candidate set
- suppressed operator ids
- suppression reason by route family

This would make controller-state / prompt alignment more honest and more diagnosable.

### 13.3 Tertiary Recommendation

Split expand intent more explicitly between:

- peak-oriented expansion
- gradient-oriented expansion

Current full results suggest the controller can drift toward gradient-favoring tradeoffs while sacrificing feasible-rate and Pareto breadth.

### 13.4 Execution Recommendation

Do not immediately keep iterating on full runs.

Preferred cadence:

1. implement L6
2. run a matched `12 x 6` mid smoke
3. confirm:
   - expand-share comes down
   - frontier yield per expand decision improves
   - `evaluations_since_frontier_add` improves materially
4. only then run the next full `llm`

---

## 14. Key Source Files To Read First

If continuing implementation, read these in order:

### Core benchmark and spec files

- `AGENTS.md`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`

### Controller state and policy

- `optimizers/operator_pool/domain_state.py`
- `optimizers/operator_pool/state_builder.py`
- `optimizers/operator_pool/reflection.py`
- `optimizers/operator_pool/route_families.py`
- `optimizers/operator_pool/policy_kernel.py`
- `optimizers/operator_pool/llm_controller.py`
- `optimizers/operator_pool/prompt_projection.py`
- `optimizers/operator_pool/diagnostics.py`

### LLM transport layer

- `llm/openai_compatible/config.py`
- `llm/openai_compatible/client.py`
- `llm/openai_compatible/schemas.py`

### Supporting optimizer files

- `optimizers/llm_summary.py`
- `optimizers/llm_decision_summary.py`
- `optimizers/cli.py`
- `optimizers/artifacts.py`

### Tests

- `tests/optimizers/test_llm_controller_state.py`
- `tests/optimizers/test_llm_policy_kernel.py`
- `tests/optimizers/test_llm_controller.py`
- `tests/optimizers/test_llm_prompt_projection.py`
- `tests/optimizers/test_optimizer_cli.py`

---

## 15. Key Artifact Paths

### Baselines

- raw full:
  - `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/raw/seeds/seed-11/optimization_result.json`
- union full:
  - `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/union/seeds/seed-11/optimization_result.json`
- old llm full:
  - `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_0015__llm/`

### Recovery references

- L3 mid:
  - `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1325__llm_l3_mid_smoke/`
- L4 v4 mid:
  - `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1622__llm_l4_mid_smoke_v4/`
- L5 mid:
  - `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1758__llm_l5_mid_smoke/`
- L5 full:
  - `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm/`

For both L5 runs, the most useful files are:

- `optimization_result.json`
- `controller_trace_summary.json`
- `llm_metrics.json`
- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `controller_trace.json`
- `operator_trace.json`

---

## 16. Commands Most Likely Needed Next

### Re-run focused tests

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_prompt_projection.py -v
```

### Re-run diagnostics tests

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_analyze_controller_trace_accepts_optional_operator_and_request_sidecars \
  tests/optimizers/test_optimizer_cli.py::test_analyze_controller_trace_reports_expand_family_outcomes_and_budget_throttling -v
```

### Analyze an existing run

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm/controller_trace.json \
  --optimization-result /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm/optimization_result.json \
  --operator-trace /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm/operator_trace.json \
  --llm-request-trace /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm/llm_request_trace.jsonl \
  --llm-response-trace /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm/llm_response_trace.jsonl \
  --output /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/0415_1802__llm/controller_trace_summary.json
```

### Mid-budget smoke pattern

Use a temporary spec with matched setup and reduced:

- `population_size = 12`
- `num_generations = 6`

Then run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec /tmp/<mid_smoke_spec>.yaml \
  --evaluation-workers 2 \
  --output-root /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/<run_id>
```

### Full LLM run pattern

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root /home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery/scenario_runs/s1_typical/<run_id>
```

---

## 17. Bottom-Line Summary For Claude

The short handoff version is:

- the benchmark and paper boundary are strict: same problem, same operator pool, controller-only difference
- transport and API availability are currently fine on `https://rust.cat/v1` with `gpt-5.4`
- the controller recovery already fixed:
  - route-family collapse
  - recover semantic monopoly
  - hard recover priority
- L5 added recent expand-budget accounting and route throttling
- L5 mid-smoke improved clearly
- but L5 full overcorrected into too much `post_feasible_expand`
- the current bottleneck is now expand saturation and weak expand exit control
- the best next step is an `L6` expand saturation governor plus better prompt-side exposure of suppressed candidates

If you only remember one sentence:

The controller is no longer too weak; it is now too eager to keep expanding after frontier yield has already stalled.
