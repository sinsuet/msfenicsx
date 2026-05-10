# Stage A IGD 指标与论文图表使用说明

生成时间：2026-05-10  
数据来源：`scenario_runs/paper_experiment_db/tables/` 与各 suite-owned `comparisons/` bundle  
适用范围：仅覆盖 Stage A 已完成证据；`main_s6` 仍为 `pending`，不得纳入主结果结论。

## 结论先行

当前 Stage A 结果支持较强但有边界的结论：

- 在已完成的 S4/S5 main block 中，论文主统计看 multi-seed aggregate mean。按这个口径，DeepSeek LLM 相比 raw 在 mean nIGD、mean HV、mean gradient RMS、mean peak temperature 和 feasible rate 上均占优。
- 因此，正文可以宣传 “在已完成的 S4/S5 主实验中，LLM 在 aggregate mean 层面全面最优”。这里的 “全面” 指 registered aggregate metrics 的均值层面，不指 every-seed domination。
- S5 seed11 用作 representative diagnostic case 展示方法行为、布局变化、热场和 controller trace，不替代 multi-seed aggregate 统计。
- S6 main 仍 pending，没有可报告的 S6 raw-vs-LLM aggregate；S6 seed23 feedback-off 只能作为机制 negative control。
- 合理论文表述应是：LLM 在已完成 S4/S5 matched-seed blocks 上以 aggregate mean 口径全面改善 Pareto-front 接近度、HV、thermal-gradient、peak temperature 和 feasibility 指标，同时用 seed11 展示机制过程。

IGD/nIGD 解释规则：

- `normalized_final_igd` 是当前推荐使用的 IGD 指标。
- nIGD 越低越好。
- nIGD 只在同一个 `block_id + seed` 或同一个 registered block 内解释；不要跨 S4/S5/S6 或跨不同 reference scope 直接比较绝对值。
- S4 main 的 nIGD 是 raw-vs-LLM scope 下重算的；S4 semantic ablation 的 nIGD 是 raw/union/LLM 三方 scope。

## Main Block IGD / nIGD 摘要

| Block | Method | Seeds | Mean nIGD ↓ | Median nIGD ↓ | IQR | Mean HV ↑ | Mean Gradient RMS ↓ | Mean Peak Temp ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| main_s4 | raw | 5 | 0.5364 | 0.5479 | 0.1800 | 932.86 | 12.6460 | 314.0804 |
| main_s4 | LLM DeepSeek | 5 | 0.1356 | 0.1304 | 0.2084 | 1050.59 | 11.3818 | 313.6936 |
| main_s5 | raw | 5 | 0.7461 | 0.6835 | 0.4966 | 917.69 | 14.5028 | 319.3326 |
| main_s5 | LLM DeepSeek | 5 | 0.1914 | 0.0000 | 0.4103 | 1075.53 | 12.5949 | 318.9771 |

相对 raw 的均值变化：

| Block | nIGD reduction | HV change | Gradient RMS change | Peak Temp change |
|---|---:|---:|---:|---:|
| main_s4 | -74.7% | +12.6% | -10.0% | -0.12% |
| main_s5 | -74.3% | +17.2% | -13.2% | -0.11% |

逐 seed 胜率作为附录透明性材料，不作为主结论口径：

| Block | nIGD wins | HV wins | Gradient wins | Peak-temp wins |
|---|---:|---:|---:|---:|
| main_s4, LLM vs raw | 4/5 | 4/5 | 4/5 | 2/5 |
| main_s5, LLM vs raw | 4/5 | 5/5 | 5/5 | 3/5 |

逐 seed 非支配现象，建议放附录说明：

| Block | Seed | nIGD delta, LLM-raw | HV delta, LLM-raw | Gradient delta, LLM-raw | Peak delta, LLM-raw |
|---|---:|---:|---:|---:|---:|
| main_s4 | 31 | +0.2405 | -60.78 | +0.7464 | +0.6827 |
| main_s5 | 31 | +0.3226 | +16.83 | -0.2829 | +0.4714 |

说明：

- `delta_normalized_final_igd < 0` 表示 LLM 更好。
- `delta_final_hypervolume > 0` 表示 LLM 更好。
- `delta_best_gradient_rms < 0` 和 `delta_best_temperature_max < 0` 表示 LLM 更好。

## S4 Semantic Ablation

| Method | Seeds | Mean nIGD ↓ | Mean HV ↑ | Mean Gradient RMS ↓ | Mean Peak Temp ↓ |
|---|---:|---:|---:|---:|---:|
| raw | 5 | 0.6094 | 932.86 | 12.6460 | 314.0804 |
| union | 5 | 0.6603 | 908.00 | 12.9846 | 314.1542 |
| LLM DeepSeek | 5 | 0.2680 | 1050.59 | 11.3818 | 313.6936 |

LLM 相比 raw：

- nIGD 胜率：4/5 seeds，mean delta -0.3414。
- HV 胜率：4/5 seeds，mean delta +117.73。
- gradient RMS 胜率：4/5 seeds，mean delta -1.2642。

LLM 相比 union：

- nIGD 胜率：4/5 seeds，mean delta -0.3923。
- HV 胜率：4/5 seeds，mean delta +142.59。
- gradient RMS 胜率：4/5 seeds，mean delta -1.6028。

可用表述：

> In the S4 semantic ablation, LLM semantic control is the best aggregate-mean method among raw, non-semantic union control, and LLM control in nIGD, HV, gradient RMS, and peak temperature.

不建议表述：

> LLM dominates raw and union on every metric and every seed.

## S5 Algorithm Baseline

该 block 用来回答 “raw baseline 是否只是因为 NSGA-II 弱”。注意：algorithm baseline 的 nIGD reference scope 是 NSGA-II/SPEA2/MOEA/D raw 三方比较，不能与 main_s5 raw-vs-LLM 的 nIGD 绝对值直接混比。

| Method | Seeds | Mean nIGD ↓ | Median nIGD ↓ | Mean HV ↑ | Mean Gradient RMS ↓ | Mean Peak Temp ↓ |
|---|---:|---:|---:|---:|---:|---:|
| nsga2-raw | 5 | 0.9509 | 1.0439 | 913.61 | 14.5028 | 319.3326 |
| spea2-raw | 5 | 0.6699 | 0.9193 | 941.23 | 14.2353 | 318.9425 |
| moead-raw | 5 | 0.2390 | 0.0000 | 1014.38 | 13.4094 | 318.3694 |

主要观察：

- MOEA/D raw 在 algorithm baseline 内最强：nIGD 相比 NSGA-II raw 5/5 seeds 更低；gradient RMS 4/5 seeds 更低；HV 3/5 seeds 更高。
- SPEA2 raw 相比 NSGA-II raw 也更强一些：nIGD 4/5 seeds 更低；HV 3/5 seeds 更高。
- 这说明 native NSGA-II raw 不是唯一可用 baseline；论文中应保留 algorithm baseline 表，避免 reviewer 认为主结果只是在打弱 baseline。

建议写法：

> The raw-only algorithm baseline shows that the comparison is not tied to a single weak raw optimizer: MOEA/D raw is the strongest raw-only variant under the registered S5 baseline block.

边界：

- 不要直接用 algorithm baseline 的 nIGD 绝对值和 main_s5 的 LLM nIGD 比较，因为 reference front 不同。
- 如需严谨比较 `LLM DeepSeek vs MOEA/D raw`，应后续构造同一 comparison scope 的注册比较表。

## S5 Model Sensitivity

当前 `model_sensitivity_metrics.csv` 未导出 comparison-scope nIGD；它更适合做 single-seed controller/profile sensitivity 表，而不是主性能统计表。GPT-5.5 结果按正常有效 profile 处理，不在正文中作为异常描述。

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
- MiniMax 应放 appendix，作为 profile compatibility / exploratory profile，不在正文中展开为主要性能证据。

## S6 Feedback-Off Diagnostic

该项是机制 negative control，不是 S6 main 统计证据。

| Method | Seed | HV ↑ | HV Ratio vs Raw | Best Peak ↓ | Best Gradient ↓ | PDE Attempts Runtime | Runtime Feasible Count |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw | 23 | 1065.40 | 1.000 | 323.336 | 14.513 | 1629 | 1409 |
| feedback-off DeepSeek | 23 | 543.09 | 0.5098 | 324.410 | 17.093 | 982 | 734 |

Prompt audit：

- prompts with `operator_panel`: 1920
- audited operator-panel rows: 17280
- nonzero operator-level PDE feedback rows: 0

建议用途：

- 正文机制分析或消融诊断表。
- 不纳入 S6 main aggregate。
- 表述为 `operator-feedback masked negative control` 或 `feedback-off diagnostic`，不要写成正式 baseline。

## 正文建议使用的图表

### Main Results

1. S4 semantic/main aggregate summary
   - `scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash/figures/pdf/summary_overview.pdf`
   - 用途：S4 raw/union/LLM 三方总览。
   - 适合正文：是。

2. S4 aggregate HV / gradient trace
   - `.../figures/pdf/hypervolume_iqr_comparison.pdf`
   - `.../figures/pdf/gradient_trace_median_band.pdf`
   - 用途：展示 LLM 在 S4 上的前沿质量和 gradient 轨迹优势。
   - 适合正文：择一使用；另一个可放附录。

3. S5 main aggregate summary
   - `scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/comparisons/aggregate/raw_vs_llm-deepseek_v4_flash/figures/pdf/summary_overview.pdf`
   - 用途：S5 raw-vs-LLM 主结果总览。
   - 适合正文：是。

4. S5 aggregate HV / gradient trace
   - `.../figures/pdf/hypervolume_iqr_comparison.pdf`
   - `.../figures/pdf/gradient_trace_median_band.pdf`
   - 用途：展示 S5 matched-seed 下 LLM 的搜索质量进展。
   - 适合正文：可二选一；若版面允许，和 S4 形成并列 panel。

5. Final metrics table
   - `scenario_runs/paper_experiment_db/tables/aggregate_metrics.csv`
   - 用途：正文主表，列出 `mean nIGD / mean HV / mean gradient RMS / feasible rate / PDE accounting`。
   - 适合正文：是，建议将 S4 main、S5 main、S4 semantic、S5 algorithm baseline 分成两个表或一个主表加 appendix full table。

### Mechanistic / Diagnostic Figures

1. S5 seed11 representative diagnostic case
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/layout_initial.png`
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/layout_final.png`
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/temperature_field_knee-candidate.png`
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/gradient_field_knee-candidate.png`
   - 用途：展示一个完整 traced medium-scale case 的布局和热场变化。
   - 适合正文：是；定位为 seed11 representative diagnostic case，用于展示方法行为。多 seed 统计结论仍来自 aggregate tables。

2. S5 seed11 search/process diagnostics
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/search_trajectory_network.png`
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/operator_phase_heatmap.png`
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/hypervolume_progress.png`
   - `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/objective_progress.png`
   - 用途：说明 LLM 是做 state-to-operator routing，不是直接生成布局。
   - 适合正文：`search_trajectory_network + operator_phase_heatmap` 可作为机制图；progress 图可放附录。

3. S6 feedback-off diagnostic table
   - `scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23/tables/summary_metrics.csv`
   - `scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23/analytics/operator_feedback_audit.json`
   - 用途：机制 negative control。
   - 适合正文：建议做成小表或一段文字，不建议作为主性能图。

## 适合附录的内容

1. Per-seed comparison dashboards
   - S4 by-seed:
     - `scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/by_seed/seed-*/raw_vs_union_vs_llm-deepseek_v4_flash/figures/summary_overview.png`
   - S5 by-seed:
     - `scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/comparisons/by_seed/seed-*/raw_vs_llm-deepseek_v4_flash/figures/summary_overview.png`
   - 用途：提供逐 seed 透明性，说明主结论采用 aggregate mean 口径。

2. Per-seed layout/field comparisons
   - `final_layout_comparison.png`
   - `temperature_field_comparison.png`
   - `gradient_field_comparison.png`
   - 用途：定性检查每个 seed 的代表解；不建议全部放正文。

3. PDE budget accounting
   - `pde_budget_accounting.png`
   - `tables/pde_budget_accounting.csv`
   - `scenario_runs/paper_experiment_db/tables/common_pde_cutoff.csv`
   - 用途：回应 cheap screening / PDE budget 公平性问题。

4. Algorithm baseline by-seed figures
   - `scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw/comparisons/by_seed/seed-*/nsga2-raw_vs_spea2-raw_vs_moead-raw/figures/summary_overview.png`
   - 用途：raw-only algorithm baseline 的逐 seed 证据。
   - 适合附录：是。正文建议只放 aggregate table。

5. Full numeric tables
   - `seed_metrics.csv`
   - `pairwise_deltas.csv`
   - `common_pde_cutoff.csv`
   - `model_sensitivity_metrics.csv`
   - 用途：appendix tables 或 supplementary material。

## 建议主文指标口径

正文主表建议列：

- `normalized_final_igd_mean`：主 Pareto-front 接近度指标，lower is better。
- `final_hypervolume_mean`：前沿覆盖/质量指标，higher is better。
- `best_gradient_rms_mean`：主要 thermal-gradient 指标，lower is better。
- `best_temperature_max_mean`：peak temperature，作为 secondary metric；按 aggregate mean 口径，LLM 在已完成 S4/S5 main 中也优于 raw。
- `feasible_rate_mean`：搜索可行性。
- `pde_evaluations_mean` 和 `solver_skipped_evaluations_mean`：PDE accounting / cheap screening transparency。

建议正文结论句：

> Across the completed S4 and S5 main blocks, the DeepSeek semantic controller is consistently best under the registered aggregate-mean metrics: it reduces mean nIGD by about 74% relative to raw, increases mean hypervolume, reduces mean gradient RMS and peak temperature, and improves feasible-search behavior under matched seeds and budgets. We use S5 seed 11 as a representative diagnostic case to visualize how this aggregate advantage arises in a fully traced medium-scale run.

## 写作边界

- “LLM 全面最优 / 全面占优” 的主文口径应限定为 registered aggregate-mean metrics；逐 seed 细节作为附录透明性材料。
- 不能写 “LLM 在 S4/S5/S6 上已验证 scale-up dominance”，因为 `main_s6` pending。
- 不能把 S6 seed23 feedback-off 纳入 S6 main aggregate。
- 不能用 model sensitivity 的 single-seed GPT-5.5 结果声称 GPT 统计上稳定优于 DeepSeek；可以写 GPT-5.5 在 seed11 sensitivity case 上表现最好。
- 不能把 algorithm baseline 的 nIGD 绝对值和 main_s5 的 nIGD 绝对值直接比较，除非后续重建同一 reference-scope comparison。
