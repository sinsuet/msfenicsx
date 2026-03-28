# R67 msfenicsx Multi-Backbone Optimizer Matrix Doc Reset

Date: 2026-03-27

## Scope

This report records a documentation reset only. No optimizer implementation was changed in this step.

Historical note: this report captures the approval/reset point for the matrix direction. The repository has since implemented the first-batch raw matrix runtime. An exploratory matrix `pool-random` implementation was also tried, but that code/spec path was later removed from the active repository state to keep the platform clean. Further update on 2026-03-28: the matrix direction remains the optimizer-platform line, while the next paper-facing controller story is now documented separately as an `NSGA-II` hybrid-union line.

At the time of this reset, the repository's implemented optimizer mainline remained:

- pure `pymoo` `NSGA-II`
- paired hot/cold four-component benchmark
- shared legality repair
- multicase evaluation and Pareto artifact bundle

What changed in docs is the approved next-stage direction:

- operator-pool work is no longer framed as an `NSGA-II`-only extension
- the approved next-stage optimizer platform is now a multi-backbone raw/pool matrix
- the first complete matrix batch is:
  - `NSGA-II`
  - `NSGA-III`
  - `C-TAEA`
  - `RVEA`
  - constrained `MOEA/D`
  - `CMOPSO`

## Why The Reset Was Needed

The previous operator-pool fairness write-up still assumed a single-backbone `NSGA-II` extension. That no longer matched the approved research direction.

Keeping that document around would leave the repository with two conflicting stories:

1. a single-backbone operator-pool path
2. a multi-backbone shared-operator platform

The second story is now the approved one.

## New Active Planning References

- benchmark reference: `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`
- new optimizer-platform design: `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- new optimizer-platform implementation plan: `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`

## Removed Or Re-scoped Material

- deleted the obsolete single-backbone operator-pool plan
- updated repository status docs so they no longer imply that the future operator pool belongs only to `NSGA-II`
- updated the benchmark design and legacy implementation-plan notes so readers can distinguish:
  - current implemented truth
  - approved next-stage platform direction

## Verification

Documentation verification executed:

1. `git diff --check -- README.md AGENTS.md docs`
   Result: clean
2. `git grep -n 'operator_pool_nsga2\|single-backbone operator-pool\|Hybrid-Operator `NSGA-II`' -- README.md AGENTS.md docs || true`
   Result: no active-document matches after the reset

## Status

Implemented truth remains:

- active classical optimizer baseline: pure `NSGA-II`

Approved next-stage truth is now:

- multi-backbone raw matrix
- exploratory multi-backbone union-uniform matrix
- possible later multi-backbone union-LLM matrix as a platform experiment class
- plus a separate paper-facing `NSGA-II` hybrid-union controller ladder
- with the immediate next paper-facing implementation step now focused on `NSGA-II union-LLM`
