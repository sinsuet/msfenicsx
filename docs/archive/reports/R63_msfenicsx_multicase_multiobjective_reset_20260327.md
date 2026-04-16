# R63 msfenicsx Multicase Multiobjective Reset (2026-03-27)

## Summary

This report resets the active optimization direction of `msfenicsx`.

The previous constrained single-objective `pymoo` baseline was useful as a narrow infrastructure checkpoint, but it is no longer the active mainline because it does not match the intended satellite thermal research framing closely enough.

The new active optimization path is:

- paired hot/cold operating cases
- multiobjective thermal evaluation
- Pareto-oriented search results
- representative-candidate reporting instead of one scalar best result

## Why the Single-Objective Path Is No Longer the Mainline

The old baseline optimized one thermal objective for one solved case and exported one best candidate.

That path is too narrow for the intended engineering narrative because realistic satellite thermal design is usually about:

- keeping components within thermal limits across multiple operating cases
- balancing hot-case cooling performance against cold-case overcooling or thermal-control effort
- reasoning about trade-offs rather than one best scalar score

For these reasons, the single-objective baseline is now treated as a migration artifact rather than the active research target.

## Why `NSGA-II` Is the First Multicase Baseline

The first reset target uses two or three objectives, not many-objective search.

`NSGA-II` is therefore the right first baseline because it:

- matches small-objective-count Pareto problems well
- is easier to verify and explain in early experiments
- avoids prematurely committing to `NSGA-III` before the objective count requires it

`NSGA-III` remains a possible later extension if the active objective set grows substantially.

## What Stays Reusable

The reset keeps these pieces as valid internals:

- `core/` canonical objects and single-case solver loop
- single-case evaluation metric extraction internals where still useful
- design-variable codec machinery where it remains compatible
- `pymoo` integration patterns at the driver boundary

## What Becomes Obsolete

The reset plans to remove or replace these public active interfaces:

- single-objective optimizer specs
- single-objective CLI examples as the mainline workflow
- `best_candidate` as the optimizer result contract
- reporting framed around one primary objective improvement ratio

## Immediate Next Steps

1. Add explicit hot and cold reference operating cases.
2. Extend `evaluation/` to multicase aggregation and realistic thermal metrics.
3. Replace the single-objective optimizer result contract with Pareto outputs.
4. Implement a multicase `NSGA-II` baseline before resuming any LLM policy-layer work.
