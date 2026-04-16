# R70 msfenicsx L1 Reusable Controller Kernel Validation

Date: 2026-04-01

## Scope

This report records the first matched full-budget validation of the reusable `L1` controller-policy kernel for the paper-facing `NSGA-II hybrid-union` line.

The validated controller path is still:

- fixed `NSGA-II` union action registry
- fixed repair
- fixed expensive thermal evaluation loop
- fixed survival semantics
- controller-only change at the `LLM` selection layer

The question for this report is not whether a benchmark-specific prompt tweak can rescue one seed.
The question is whether the reusable optimizer-layer kernel introduced for:

- phase awareness
- evidence awareness
- operator-family awareness
- progress-aware reset logic

materially improves the `L1` line under matched seeds and matched budgets.

## Validation Setup

Matched full-budget validation used:

- benchmark seeds: `11`, `17`, `23`
- algorithm seed: `7`
- population size: `16`
- generations: `8`
- provider: `openai-compatible`
- capability profile: `chat_compatible_json`
- model: `GPT-5.4`
- base URL: `https://llmapi.paratera.com/v1`
- fallback controller: `random_uniform`

Commands run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_live.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed11

/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec /tmp/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_live_seed17_20260401.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17

/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec /tmp/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_live_seed23_20260401.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed23
```

Cheap local diagnostics were then generated with:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace <run>/controller_trace.json \
  --output <run>/controller_trace_summary.json
```

The aggregated runtime summary for this report is stored at:

- `scenario_runs/optimizations/diagnostics/2026-04-01-gpt54-kernel-validation-summary.json`

## Bounded Gate Status

Before the full ladder, a bounded fresh `seed17` rerun was used as the required cheap live gate.

That gate passed:

- `first_feasible_eval=39`
- `feasible_rate=0.04615` over the bounded `65`-evaluation budget
- `prefeasible.max_speculative_family_streak=0`
- `prefeasible.forced_reset_count=34`
- `prefeasible.fallback_count=0`

So the full matched reruns below were started only after the historically unstable seed no longer showed the old speculative-family monopoly pattern.

## Current Kernel Results

| Seed | Feasible Rate | First Feasible Eval | Pareto Size | Requests | Fallbacks | Avg LLM Seconds | Prefeasible Family Mix | Forced Resets | Dominance Guardrails | Prefeasible Max Speculative Streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 11 | 0.07752 | 57 | 5 | 106 | 0 | 5.76 | `local_refine=20`, `global_explore=10`, `native_baseline=4` | 32 | 12 | 0 |
| 17 | 0.20155 | 39 | 13 | 107 | 0 | 5.07 | `native_baseline=24`, `global_explore=10` | 34 | 11 | 0 |
| 23 | 0.08527 | 52 | 8 | 106 | 0 | 5.24 | `native_baseline=36`, `global_explore=14` | 50 | 11 | 0 |

Observed invariants across all three seeds:

- `prefeasible.max_speculative_family_streak=0`
- `fallback_count=0`
- the pre-feasible bucket stayed inside stable families only
- the kernel used forced-reset windows heavily before first feasible entry

## Comparison Against Earlier Baselines

Mean metrics across matched seeds `11/17/23`:

| Method | Mean Feasible Rate | Mean First Feasible Eval | Mean Pareto Size |
| --- | ---: | ---: | ---: |
| Raw `NSGA-II` | 0.09044 | 68.00 | 5.67 |
| `NSGA-II union-uniform` | 0.11886 | 65.00 | 9.33 |
| Older compact `GPT-5.4 L1` | 0.09044 | 69.00 | 8.00 |
| Current reusable-kernel `GPT-5.4 L1` | 0.12145 | 49.33 | 8.67 |

Interpretation:

- against raw `NSGA-II`, the current kernel improves average feasible rate, reaches first feasible much earlier, and yields a larger mean Pareto set
- against the older compact `GPT-5.4` controller, the current kernel improves all three mean metrics
- against `union-uniform`, the current kernel improves average feasible rate and reaches first feasible much earlier, but still trails slightly on mean Pareto size

Per-seed comparison highlights:

- `seed11`: current kernel beats raw on feasible rate and Pareto size, but regresses against the older compact `L1` and does not beat `union-uniform`
- `seed17`: current kernel strongly improves over raw and the older compact `L1`; `union-uniform` still remains stronger on this seed
- `seed23`: current kernel materially rescues the earlier failure mode and strongly beats both the older compact `L1` and `union-uniform`; raw still keeps a slightly higher feasible rate, but the current kernel reaches feasibility much earlier and returns a larger Pareto set

## Controller-Behavior Interpretation

The most important result from this report is not only the aggregate metrics.
It is the behavioral shift in the pre-feasible prefix.

For the previously unstable route:

- historical `seed17` window-guardrail artifact showed `max_speculative_family_streak=40`
- historical `seed23` window-guardrail artifact showed `max_speculative_family_streak=32`

Under the current reusable kernel:

- `seed11`, `seed17`, and `seed23` all show `prefeasible.max_speculative_family_streak=0`
- pre-feasible selections stay within `native_baseline`, `global_explore`, and `local_refine`
- forced-reset logic and recent-dominance guardrails are actually being exercised, not merely defined in code

That is exactly the kind of evidence needed for a reusable framework claim:

- the improvement is expressed through generic family-level control
- it does not require operator-name-specific permanent exceptions
- it transfers across more than one benchmark seed

## Residual Limitations

This validation still leaves visible limits.

- The current trace summaries still place many late-run decisions in the `unknown` bucket rather than in an explicit `post_feasible` bucket.
- That means the current evidence is strongest for pre-feasible stabilization, and weaker for fine-grained post-feasible phase attribution.
- The current kernel does not yet cleanly dominate `union-uniform` on mean Pareto size.
- `seed11` remains a reminder that the new kernel is not a universal win across every metric on every seed.

So the right conclusion is not "problem solved everywhere."
The right conclusion is:

- reusable pre-feasible stabilization is now validated
- average paper-facing `L1` performance is now better than raw and better than the older compact `L1`
- the remaining gap is mainly in post-feasible expansion quality and in making phase attribution fully explicit outside active guardrail windows

## Claim Status

The repository can now support the following bounded claims:

1. The reusable controller-policy kernel is validated as optimizer-layer framework logic rather than as a benchmark-seed patch.
2. Under matched `11/17/23` seeds and matched budgets, the current `GPT-5.4` `L1` line beats raw `NSGA-II` on average.
3. Under the same matched seeds and budgets, the current `GPT-5.4` `L1` line beats the older compact `GPT-5.4` `L1` line on average.
4. The current `GPT-5.4` `L1` line does not yet fully replace `union-uniform` as the strongest paper-facing comparator, because the comparison remains mixed.

Claims that are still not justified:

- that the current kernel dominates every matched baseline on every seed
- that post-feasible controller phases are fully explained by the current trace metadata
- that the controller is already ready for repository-wide generalized superiority claims beyond the current `NSGA-II` paper-facing line
