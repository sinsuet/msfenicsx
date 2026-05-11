# EAAI Paper Brief 计划恢复审计与继续执行记录

日期：2026-05-09  
状态更新：2026-05-11 已 superseded，不作为当前论文证据口径执行。

## 当前说明

本报告记录的是 2026-05-09 上下文恢复时的 paper brief 状态。当时 `paper/msgalaxy/planning/` 下的 registers 和 chapter briefs 已经生成，但 S4/S5/S6 final main block 尚未全部进入当前 paper-facing evidence database。

该中间状态已经被 2026-05-11 的 Stage A 论文整理取代。当前证据入口为：

- `paper_database/paper_experiment_db/tables/claim_evidence.csv`
- `paper_database/paper_experiment_db/tables/aggregate_metrics.csv`
- `paper/msgalaxy/planning/evidence_register.md`
- `docs/reports/2026-05-10-stage-a-igd-and-paper-assets.md`

## 当前 Active 口径

- Main: S4/S5/S6，5 seeds，`raw` vs `llm_deepseek_v4_flash`
- Semantic Ablation: S4，5 seeds，`raw / union / llm`
- Mechanism / Feedback-Off Diagnostic: S6 seed23，single-seed raw / normal DeepSeek LLM / feedback-off DeepSeek LLM
- Model Sensitivity: S5 seed11，DeepSeek/Qwen/GPT-5.5/MiMo，GLM/MiniMax 可放 appendix
- Algorithm Baseline: S5，5 seeds，NSGA-II/SPEA2/MOEA/D raw

## Retired 2026-05-09 Assumptions

以下内容只保留为历史审计背景，不能作为当前 Results 或 Mechanistic Analysis 的写作依据：

- S4/S5/S6 final main block 仍未完成。
- 旧 single-seed semantic ablation 是当前最干净的主机制证据。
- 旧 representative diagnostic seed 是 active mechanism diagnostic。
- Kimi 或 `llm_direct` 是 final requirement。

## 保留价值

该报告仍说明一个工程事实：`paper/` 被 `.gitignore` 忽略，因此论文正文、planning register 和编译产物不会自动进入普通 `git status` / `git diff`。如果需要版本化论文目录，后续应明确使用 `.gitignore` 调整或 `git add -f` 策略。
