# Final Experiment Database Design

## 背景

最终论文实验结构固定为五类证据：

- Main: S4/S5/S6，5 seeds，`raw` vs `llm_deepseek_v4_flash`
- Semantic Ablation: S4，5 seeds，`raw / union / llm`
- Mechanism / Feedback-Off Diagnostic: S6 seed23，single-seed 三方机制消融，`raw` vs normal DeepSeek LLM vs feedback-off DeepSeek
- Model Sensitivity: S5 seed11，DeepSeek/Qwen/GPT-5.5/MiMo 为主，GLM/MiniMax 可放 appendix
- Algorithm Baseline: S5，5 seeds，NSGA-II/SPEA2/MOEA/D raw

旧的 `llm_direct` block、Kimi final requirement、旧 representative diagnostic seed 图文口径不再作为 active final paper-facing requirement。后续写作和数据库导出以 `paper_database/paper_experiment_db/` 的 registered evidence 为准。

## 当前 Artifact 状态

- S4 main / semantic ablation complete archive:
  - `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed`
  - active seeds: `11,13,17,19,23`
  - superseded audit archive: `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed__superseded_20260511_seeds_11_17_23_29_31`
- S5 main complete archive:
  - `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5`
  - active seeds: `23,37,19,11,41`
- S5 model sensitivity complete archive:
  - `paper_database/s5_aggressive15/archives/0511_archive__model_compare_seed11`
- S5 algorithm baseline complete archive:
  - `paper_database/s5_aggressive15/archives/0511_archive__algorithm_compare_raw`
- S6 main complete archive:
  - `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed`
  - active seeds: `13,19,11,21,23`
- S6 mechanism / feedback-off diagnostic archive:
  - `paper_database/s6_aggressive20/archives/0511_archive__feedback_off_deepseek_seed23_diagnostic`

Do not use `scenario_runs/s6_aggressive20/0510_1239__llm-deepseek_v4_flash` as S6 main evidence. Its seed23 LLM run is the normal LLM source for the S6 seed23 mechanism diagnostic, while the feedback-off archive provides the masked-feedback condition. Diagnostic roots are excluded from S6 main aggregate unless explicitly listed in the main archive above.

## Feedback-Off Diagnostic Definition

The S6 seed23 mechanism / feedback-off diagnostic is a single-seed mechanism negative control. It is not a statistical baseline and must not be pooled into S6 main results.

Evidence:

- same-seed raw final HV: `1065.400`
- normal DeepSeek LLM final HV: `1144.438`
- feedback-off DeepSeek final HV: `858.588`
- prompt audit for feedback-off:
  - prompts with `operator_panel`: `1920`
  - audited operator-panel rows: `17280`
  - nonzero operator-level PDE feedback rows: `0`

Interpretation:

The workflow still performs PDE evaluations, but the feedback-off semantic controller cannot see operator-level PDE outcome evidence. This supports the claim that the LLM component is useful as a semantic controller only when coupled with operator-effect feedback, ranking/caps, and the repair/skip/constraint workflow.

Recommended paper wording:

```text
We include a single-seed S6 seed23 mechanism diagnostic that compares same-seed raw, the normal DeepSeek semantic controller, and a feedback-off DeepSeek controller whose operator-level PDE outcome fields are zeroed. The feedback-off condition has zero nonzero operator-feedback rows across the audited operator panels and is weaker than the normal LLM condition and same-seed raw, supporting the interpretation that closed-loop operator-effect feedback matters for semantic operator routing.
```

## Database Target

The paper-facing database root is:

- `paper_database/paper_experiment_db/`

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
- `tables/llm_diagnostics.csv` generated from feedback-off prompt/operator audit metadata
- `msfenicsx_experiments.duckdb`
- figure folders under `figures/`

The S5 seed11 representative-case export is a paper-facing qualitative artifact root under
`paper_database/paper_experiment_db/figures/s5_seed11_raw_llm_representatives/`.
It compares raw and normal DeepSeek LLM for visual inspection only. It does not define a new performance block and must not be pooled into `main_s5`.

IGD/nIGD policy:

- Use comparison-scope empirical reference fronts.
- Normalize objectives within the same scenario/block/seed scope before nIGD.
- Do not directly compare absolute IGD across S4/S5/S6.
- Report paired deltas and win rates within registered blocks.

## Execution Plan

Use:

- `docs/superpowers/plans/2026-05-11-s5-s6-main-results-paper-sync.md`

The active paper-facing database is now a completed Stage A database:

- S4 main / semantic ablation with seeds `11,13,17,19,23`
- S5 main with seeds `23,37,19,11,41`
- S6 main with seeds `13,19,11,21,23`
- S6 seed23 mechanism / feedback-off diagnostic
- S5 seed11 raw / normal DeepSeek LLM representative-case qualitative export
- S5 seed11 model sensitivity
- S5 raw-only algorithm baseline

Comparison implementation note:

- Use `optimizers.benchmark_runner.comparisons.plan_campaign_comparisons` for main and S4 semantic archives because the LLM directory is named `llm-deepseek-v4-flash`, not literal `llm`.
- For `paper_database/s5_aggressive15/archives/0511_archive__algorithm_compare_raw`, generate by-seed comparison bundles only. The final aggregate must be computed in `paper_database/paper_experiment_db/tables/aggregate_metrics.csv` grouped by algorithm-aware `method_slug`, because all three algorithms record `mode: raw` in `run.yaml`.
