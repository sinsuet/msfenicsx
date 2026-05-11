# Stage A IGD 指标与论文图表使用说明

生成时间：2026-05-10  
最近同步：2026-05-11  
数据来源：`paper_database/paper_experiment_db/tables/` 与各 official archive 的 suite-owned `comparisons/` bundle  
适用范围：Stage A 当前 paper-facing 证据库。S4/S5/S6 main、S4 semantic ablation、S6 seed23 mechanism / feedback-off diagnostic、S5 model sensitivity 和 S5 raw-only algorithm baseline 均已形成注册证据。

## 结论先行

当前 Stage A 结果支持以下有边界的结论：

- 在 S4/S5/S6 三个 main block 中，论文主统计看每个 block 内的 five-seed aggregate mean。按该口径，DeepSeek LLM 相比 raw 在 mean nIGD、mean HV、mean gradient RMS、mean peak temperature 和 feasible rate 上均占优。
- S4 semantic ablation 显示 LLM 在同一 primitive structured operator support 上优于 raw 和 fixed stochastic union，说明收益不是单纯来自更大算子池。
- S6 seed23 mechanism / feedback-off diagnostic 是 single-seed 三方机制消融：同 seed raw、正常 DeepSeek LLM、feedback-off DeepSeek LLM。它只支撑机制解释，不替代 S6 main multi-seed aggregate。
- S5 seed11 model sensitivity 是 single-seed profile diagnostic。GPT-5.5 在该 seed 上表现最好，但不能外推为 profile-level statistical claim。
- S5 raw-only algorithm baseline 显示 raw baseline 不是只因 NSGA-II 偏弱；MOEA/D raw 是该 block 内更强的 raw-only 参照。

IGD/nIGD 解释规则：

- `normalized_final_igd` 是当前推荐使用的 paper-facing nIGD 指标，lower is better；当前 Stage A 表格使用 `block_archive_dense_nigd`。
- `block_archive_dense_nigd` 在每个 registered block 内读取现有 `evaluation_events.jsonl` 的全部 `status=ok` PDE 评价点，构造 block-level empirical archive 非支配前沿，并按弧长稠密采样 201 个 reference 点；不重跑实验，也不手工改结论。
- nIGD 只在同一个 registered block/reference policy 内解释；跨 S4/S5/S6 表述应使用各 block 内 raw-vs-LLM 的方向性、相对变化和 win-rate，而不是比较不同规模的绝对 nIGD。

## Main Block IGD / nIGD 摘要

| Block | Method | Seeds | Mean nIGD ↓ | Median nIGD ↓ | IQR | Mean HV ↑ | Mean Gradient RMS ↓ | Mean Peak Temp ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| main_s4 | raw | 5 | 0.2831 | 0.2631 | 0.1378 | 909.73 | 12.6756 | 314.2745 |
| main_s4 | LLM DeepSeek | 5 | 0.1057 | 0.0804 | 0.0177 | 1103.99 | 10.5761 | 313.5375 |
| main_s5 | raw | 5 | 0.2352 | 0.2635 | 0.0859 | 889.67 | 15.0164 | 319.9050 |
| main_s5 | LLM DeepSeek | 5 | 0.1199 | 0.1150 | 0.0656 | 1080.88 | 12.7020 | 319.3747 |
| main_s6 | raw | 5 | 0.2345 | 0.2371 | 0.1328 | 811.06 | 16.0287 | 323.4212 |
| main_s6 | LLM DeepSeek | 5 | 0.1171 | 0.0667 | 0.1045 | 959.45 | 14.3032 | 322.1267 |

相对 raw 的均值变化：

| Block | nIGD reduction | HV change | Gradient RMS change | Peak Temp change |
|---|---:|---:|---:|---:|
| main_s4 | -62.7% | +21.4% | -16.6% | -0.23% |
| main_s5 | -49.0% | +21.5% | -15.4% | -0.17% |
| main_s6 | -50.1% | +18.3% | -10.8% | -0.40% |

建议正文结论句：

> Across the registered S4, S5, and S6 main blocks, the DeepSeek semantic controller improves aggregate mean nIGD, hypervolume, gradient RMS, peak temperature, and feasible rate over raw NSGA-II under each block's matched seed cohort and budget.

## S4 Semantic Ablation

| Method | Seeds | Mean nIGD ↓ | Mean HV ↑ | Mean Gradient RMS ↓ | Mean Peak Temp ↓ |
|---|---:|---:|---:|---:|---:|
| raw | 5 | 0.2786 | 909.73 | 12.6756 | 314.2745 |
| union | 5 | 0.2876 | 869.16 | 13.1443 | 314.7643 |
| LLM DeepSeek | 5 | 0.1046 | 1103.99 | 10.5761 | 313.5375 |

可用表述：

> In the S4 semantic ablation, LLM semantic control is the best aggregate-mean method among raw, non-semantic union control, and LLM control in nIGD, HV, gradient RMS, and peak temperature.

不建议表述：

> LLM dominates raw and union on every metric and every seed.

## S5 Algorithm Baseline

该 block 用来回答 “raw baseline 是否只是因为 NSGA-II 弱”。注意：algorithm baseline 的 nIGD reference policy 是该 block 内 NSGA-II/SPEA2/MOEA/D raw 的 `block_archive_dense_nigd`，不能与 main_s5 raw-vs-LLM 的 nIGD 绝对值直接混比。

| Method | Seeds | Mean nIGD ↓ | Median nIGD ↓ | Mean HV ↑ | Mean Gradient RMS ↓ | Mean Peak Temp ↓ |
|---|---:|---:|---:|---:|---:|---:|
| nsga2-raw | 5 | 0.2224 | 0.2264 | 913.61 | 14.5028 | 319.3326 |
| spea2-raw | 5 | 0.2149 | 0.1790 | 941.23 | 14.2353 | 318.9425 |
| moead-raw | 5 | 0.1533 | 0.1454 | 1014.38 | 13.4094 | 318.3694 |

主要观察：

- MOEA/D raw 在 algorithm baseline 内最强：mean nIGD、mean HV、mean gradient RMS 和 mean peak temperature 均优于 NSGA-II raw。
- 这说明主结果不应被解释成只是在打一个弱 raw optimizer。
- 如需严谨比较 `LLM DeepSeek vs MOEA/D raw`，应后续构造同一 comparison scope 的注册比较表；不要直接混比不同 reference scope 的 nIGD。

## S5 Model Sensitivity

当前 `model_sensitivity_metrics.csv` 适合做 single-seed controller/profile sensitivity 表，而不是主性能统计表。GPT-5.5 结果按正常有效 profile 处理，不在正文中作为异常描述。

| Profile | Placement | Best Peak ↓ | Best Gradient ↓ | Feasible Rate | First Feasible PDE | Decision Count | Contract Invalid |
|---|---|---:|---:|---:|---:|---:|---:|
| DeepSeek v4 flash | main | 319.869 | 13.661 | 0.600 | 29 | 1270 | 0 |
| GPT-5.5 | main | 318.267 | 11.532 | 0.760 | 24 | 1310 | 0 |
| MiMo v2.5 | main | 320.189 | 14.213 | 0.602 | 10 | 1244 | 0 |
| Qwen3-6-plus | main | 319.789 | 15.102 | 0.691 | 49 | 1251 | 0 |
| GLM-5 | appendix | 320.200 | 14.853 | 0.636 | 30 | 1243 | 0 |
| MiniMax-M2.5 | appendix | 320.600 | 14.315 | 0.566 | 53 | 1172 | 0 |

建议：

- 正文可放一个简表，重点说明 main profiles 的 controller 兼容性和性能差异。
- GPT-5.5 在该 single seed 上 peak、gradient 和 feasible rate 最好，可作为 model sensitivity 中的强 profile 展示。
- DeepSeek 仍作为 paper-facing default profile，因为主实验 multi-seed archive 已完成，且 controller contract invalid 为 0。

## S6 Seed23 Mechanism / Feedback-Off Diagnostic

该项是 single-seed 机制诊断，不是 S6 main 统计证据。

| Method | Seed | Final HV ↑ | Best Peak ↓ | Best Gradient ↓ | Role |
|---|---:|---:|---:|---:|---|
| raw | 23 | 1065.400 | 323.336 | 14.513 | same-seed raw reference |
| DeepSeek LLM | 23 | 1144.438 | 322.200 | 13.851 | bounded semantic controller |
| feedback-off DeepSeek | 23 | 858.588 | 324.410 | 17.093 | operator-level PDE feedback masked |

Prompt audit for the feedback-off condition:

- prompts with `operator_panel`: 1920
- audited operator-panel rows: 17280
- nonzero operator-level PDE feedback rows: 0

建议用途：

- 正文机制分析或消融诊断表。
- 不纳入 S6 main aggregate。
- 表述为 `mechanism / feedback-off diagnostic` 或 `operator-feedback masked negative control`，不要写成正式 baseline。

## 正文建议使用的图表

### Main Results

1. S4 semantic/main aggregate summary  
   `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash/figures/pdf/summary_overview.pdf`

2. S5 main aggregate summary  
   `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/comparisons/aggregate/raw_vs_llm-deepseek_v4_flash/figures/pdf/summary_overview.pdf`

3. S6 main aggregate summary  
   `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_llm-deepseek_v4_flash/figures/pdf/summary_overview.pdf`

4. Final metrics table  
   `paper_database/paper_experiment_db/tables/aggregate_metrics.csv`

### Mechanistic / Diagnostic Figures

1. S6 seed23 mechanism / feedback-off diagnostic table and figures  
   `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/`

2. Operator feedback audit  
   `paper_database/s6_aggressive20/archives/0511_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23/analytics/operator_feedback_audit.json`

The feedback-off archive keeps a two-way audit comparison for masked-feedback verification, while the paper-facing mechanism figure root uses the three-way raw / LLM / feedback-off LLM export.

3. S5 seed23 raw / DeepSeek LLM representative-case export  
   `paper_database/paper_experiment_db/figures/s5_seed23_raw_llm_representatives/`

This S5 export is a single-seed qualitative representative artifact, not a new main statistical block.

## 适合附录的内容

1. Per-seed comparison dashboards for S4/S5/S6 main and S4 semantic ablation.
2. PDE budget accounting: `paper_database/paper_experiment_db/tables/common_pde_cutoff.csv` and per-comparison `pde_budget_accounting.csv` files.
3. Algorithm baseline aggregate and by-seed figures under `paper_database/paper_experiment_db/figures/algorithm_baseline/`.
4. Full numeric tables: `seed_metrics.csv`, `pairwise_deltas.csv`, `common_pde_cutoff.csv`, and `model_sensitivity_metrics.csv`.

## 写作边界

- “LLM 全面最优 / 全面占优” 的主文口径应限定为 registered aggregate-mean metrics；逐 seed 细节作为附录透明性材料。
- 不要把 S6 seed23 mechanism / feedback-off diagnostic 纳入 S6 main aggregate。
- 不要把 S5 seed23 raw / DeepSeek LLM representative case 纳入 S5 main aggregate。
- 不要用 model sensitivity 的 single-seed GPT-5.5 结果声称 GPT 统计上稳定优于 DeepSeek；可以写 GPT-5.5 在 S5 seed11 sensitivity case 上表现最好。
- 不要把 algorithm baseline 的 nIGD 绝对值和 main_s5 的 nIGD 绝对值直接比较，除非后续重建同一 reference-scope comparison。
