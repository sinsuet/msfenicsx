# Superseded Final Experiment Database Plan

> Superseded on 2026-05-11. Do not execute this plan for active paper-facing work.

This file previously described the intermediate Stage A database plan while S6 main was incomplete and while an older representative diagnostic case was under consideration. That state is no longer the active paper contract.

Use the current plan instead:

- `docs/superpowers/plans/2026-05-11-s5-s6-main-results-paper-sync.md`

Active paper-facing state:

- Main: S4/S5/S6, 5 seeds, `raw` vs `llm_deepseek_v4_flash`
- Semantic Ablation: S4, 5 seeds, `raw / union / llm`
- Mechanism / Feedback-Off Diagnostic: S6 seed23, single-seed raw / normal DeepSeek LLM / feedback-off DeepSeek LLM
- Model Sensitivity: S5 seed11, DeepSeek/Qwen/GPT-5.5/MiMo, with GLM/MiniMax as appendix exploratory profiles
- Algorithm Baseline: S5, 5 seeds, NSGA-II/SPEA2/MOEA/D raw

Current evidence root:

- `paper_database/paper_experiment_db/`

Current official archives:

- S4 main / semantic ablation: `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed`
- S5 main: `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5`
- S6 main: `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed`
- S6 mechanism / feedback-off diagnostic: `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/`
- S5 model sensitivity: `paper_database/s5_aggressive15/archives/0511_archive__model_compare_seed11`
- S5 algorithm baseline: `paper_database/s5_aggressive15/archives/0511_archive__algorithm_compare_raw`

Retired assumptions from the old plan:

- `main_s6` is now complete in the active Stage A paper database.
- The older representative diagnostic seed is not the active paper-facing mechanism diagnostic.
- The feedback-off diagnostic should not be summarized as only a two-way raw-vs-feedback-off comparison in the main paper text; the active mechanism diagnostic is the three-way seed23 comparison.
- Kimi and `llm_direct` are not active final requirements.
