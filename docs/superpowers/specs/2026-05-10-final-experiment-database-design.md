# Final Experiment Database Design

## 背景

最终论文实验结构固定为五类证据：

- Main: S4/S5/S6，5 seeds，`raw` vs `llm_deepseek_v4_flash`
- Semantic Ablation: S4，5 seeds，`raw / union / llm`
- Feedback-Off Diagnostic: S6 seed23，single-seed negative control，`raw` vs feedback-off DeepSeek
- Model Sensitivity: S5 seed11，DeepSeek/Qwen/GPT/MiMo 为主，GLM/MiniMax 可放 appendix
- Algorithm Baseline: S5，5 seeds，NSGA-II/SPEA2/MOEA/D raw

旧的 `llm_direct` block 不再作为 final paper-facing requirement。该方向容易混入多个机制变化，且不如 S6 seed23 feedback-off 诊断直接。后续写作和数据库导出应删除 `llm_direct` 主实验要求。

## 当前 Artifact 状态

- S4 complete archive:
  - `scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed`
  - active seeds: `11,13,17,19,23`
  - superseded audit archive: `scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed__superseded_20260511_seeds_11_17_23_29_31`
- S5 main complete archive:
  - `scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5`
- S5 model sensitivity complete archive:
  - `scenario_runs/s5_aggressive15/0510_archive__model_compare_seed11`
- S5 algorithm baseline complete archive:
  - `scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw`
- S6 raw complete archive:
  - `scenario_runs/s6_aggressive20/0510_archive__raw_5seed`
- S6 feedback-off diagnostic archive:
  - `scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic`
- S6 formal DeepSeek currently still needs valid main-block seeds `17,23,29,31` archived after rerun. Seed `11` remains sourced from:
  - `scenario_runs/s6_aggressive20/0509_0130__llm-deepseek_v4_flash`
- S6 formal candidate root for the remaining seeds is:
  - `scenario_runs/s6_aggressive20/0510_1830__llm-deepseek_v4_flash`
- Do not use `scenario_runs/s6_aggressive20/0510_1239__llm-deepseek_v4_flash` as S6 main evidence. That root contains the seed-23 feedback-off diagnostic and is excluded from main statistics.

## Feedback-Off Diagnostic Definition

The S6 seed23 feedback-off diagnostic is a single-seed mechanism negative control. It is not a statistical baseline and must not be pooled into S6 main results.

Evidence:

- same-seed raw final HV: `1065.40037845193`
- feedback-off DeepSeek final HV: `543.0890972871468`
- feedback-off / raw HV ratio: `0.509751`
- runtime PDE attempts in feedback-off run: `982`
- runtime feasible count in feedback-off run: `734`
- prompt audit:
  - prompts with `operator_panel`: `1920`
  - audited operator-panel rows: `17280`
  - nonzero operator-level PDE feedback rows: `0`

Interpretation:

The workflow still performs PDE evaluations, but the semantic controller cannot see operator-level PDE outcome evidence. This prevents closed-loop operator credit assignment. Therefore the result supports the claim that the LLM component is useful as a semantic controller only when coupled with operator-effect feedback, ranking/caps, and the repair/skip/constraint workflow.

Recommended paper wording:

```text
We include a single-seed diagnostic on S6 seed 23 where the LLM controller receives the semantic prompt context but the operator-level PDE outcome fields in the operator panel are zeroed. The workflow still performs PDE evaluations, but the controller cannot assign credit to operators from observed PDE outcomes. The run reaches only about 51% of the same-seed raw hypervolume, showing that the proposed semantic controller requires closed-loop operator-effect feedback rather than LLM operator choice alone.
```

## Database Target

The paper-facing database root is:

- `scenario_runs/paper_experiment_db/`

Required outputs:

- `manifest.yaml`
- `tables/completeness_matrix.csv`
- `tables/artifact_index.csv`
- `tables/claim_evidence.csv`
- `tables/seed_metrics.csv`
- `tables/aggregate_metrics.csv`
- `tables/pairwise_deltas.csv`
- `tables/common_pde_cutoff.csv`
- `tables/model_sensitivity_metrics.csv`
- `tables/llm_diagnostics.csv`
- `msfenicsx_experiments.duckdb`
- figure folders under `figures/`

IGD/nIGD policy:

- Use comparison-scope empirical reference fronts.
- Normalize objectives within the same scenario/block/seed scope before nIGD.
- Do not directly compare absolute IGD across S4/S5/S6.
- Report paired deltas and win rates within registered blocks.

## Execution Plan

Use:

- `docs/superpowers/plans/2026-05-10-final-experiment-database-and-s5-diagnostic-case.md`

The database can be executed in two stages.

Stage A can run now using completed evidence blocks:

- S4 main/semantic archive with seeds `11,13,17,19,23`
- S5 main archive
- S5 model sensitivity archive
- S5 algorithm baseline archive
- S6 seed23 feedback-off diagnostic archive

Stage A must leave `main_s6` marked `pending` in `claim_evidence.csv` and `completeness_matrix.csv`. It should not block the current database, S5 diagnostic figures, model table, algorithm table, or feedback-off diagnostic table on missing S6 DeepSeek seeds.

Stage B runs later after valid S6 formal DeepSeek seeds `17,23,29,31` finish with nonzero operator-level PDE feedback in prompts. At that point create:

- `scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed`

Then rebuild S6 main comparisons and re-export the paper database metrics.

Comparison implementation note:

- Use `optimizers.benchmark_runner.comparisons.plan_campaign_comparisons` for main and S4 semantic archives because the LLM directory is named `llm-deepseek-v4-flash`, not literal `llm`.
- For `scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw`, generate by-seed comparison bundles only. The final aggregate must be computed in `scenario_runs/paper_experiment_db/tables/aggregate_metrics.csv` grouped by algorithm-aware `method_slug`, because all three algorithms record `mode: raw` in `run.yaml`.
