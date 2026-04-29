# S5 aggressive LLM post-feasible strategy tuning implementation plan

> **For agentic workers:** 该计划针对当前 main 上已合并的 prompt compacting / GPT 默认链路 / prompt_size trace 状态。执行时不要回退这些工程链路改动。

## Goal

在不改变 provider、不扩大 prompt、不硬编码 S5 结果的前提下，让 `nsga2_llm` 在 S5 aggressive 的 post-feasible stagnation 阶段增加 bounded structured/sink exploration 暴露，并减少过早 local cleanup/preserve bias。

## Scope

修改文件：

- `optimizers/operator_pool/domain_state.py`
- `optimizers/operator_pool/state_builder.py`
- `optimizers/operator_pool/policy_kernel.py`
- `optimizers/operator_pool/prompt_projection.py`
- `optimizers/operator_pool/llm_controller.py`
- `tests/optimizers/test_llm_controller.py`
- `tests/optimizers/test_llm_prompt_projection.py`

新增文档：

- `docs/superpowers/specs/2026-04-29-s5-llm-post-feasible-strategy-tuning-design.md`
- `docs/superpowers/plans/2026-04-29-s5-llm-post-feasible-strategy-tuning.md`

## Implementation steps

### 1. 放宽 post-feasible expand promotion

- [ ] 在 `domain_state.build_progress_state()` 中增加 `expand_pressure_active`：
  - `recent_frontier_stagnation_count >= 2`
  - `diversity_deficit_level in {high, medium}`
  - `regression_surplus <= 1`
- [ ] 当 `expand_pressure_active` 成立时，允许打断 preserve dwell，把 `post_feasible_mode` 设为 `expand`。
- [ ] 在 `policy_kernel._post_feasible_expand_promotion_active()` 中把 regression surplus 阈值从 `>0` 放宽为 `>1`，与 domain state 保持一致。

### 2. 引入 post-feasible mixed fit

- [ ] 在 `state_builder` 新增 `_phase_fit_value(summary, phase, regime_panel)` 或等价局部逻辑。
- [ ] `post_feasible_expand` 继续使用 `expand_fit`。
- [ ] `post_feasible_recover` 使用 `max(preserve_fit, expand_fit)`。
- [ ] `post_feasible_preserve` 在 `frontier_pressure in {medium, high}` 时使用 `max(preserve_fit, expand_fit)`，否则保持 `preserve_fit`。
- [ ] 保留 high regression risk 的扣分，但不要让 structured/sink exposure priority 被 early sparse failures 完全压没。

### 3. 增加 route exposure annotation

- [ ] 在 `policy_kernel.py` 定义：
  - structured exposure operators：`component_block_translate_2_4`, `component_subspace_sbx`
  - sink exposure operators：`sink_shift`, `sink_resize`
  - cleanup operators：`component_jitter_1`, `anchored_component_jitter`, `component_swap_2`, `component_relocate_1`
- [ ] 新增 `_annotate_post_feasible_exposure_priority(...)`：
  - 只在 post-feasible 且 expand pressure active 时生效。
  - 统计 recent_decisions 中 structured/sink/cleanup share。
  - structured share 低于目标时标记 structured target。
  - sink share 低于目标时标记 sink target。
  - cleanup share 过高时标记 cleanup cooldown。
- [ ] 在 `build_policy_snapshot()` post-feasible annotation pipeline 中调用。
- [ ] reason_codes 中加入 `post_feasible_bounded_exploration_exposure`。

### 4. 投影 exposure 字段到 compact prompt

- [ ] 在 `prompt_projection._POST_FEASIBLE_OPERATOR_PANEL_PROMPT_KEYS` 和 `llm_controller._COMPACT_OPERATOR_PANEL_KEYS` 中加入：
  - `exposure_priority`
  - `exposure_status`
- [ ] 在 `_project_candidate_annotation()` 中保留这两个字段。

### 5. 调整 decision axes 和 system prompt

- [ ] 在 `_build_decision_axes()` 中输出：
  - `bounded_exploration_targets`
  - `local_cleanup_cooldown_targets`
  - `exploration_exposure_mode`
- [ ] 修改 `_build_shared_primitive_trial_candidates()`：当 structured operator 有 exposure priority 时，即使 low-success trial 也可作为 bounded target 进入候选。
- [ ] system prompt 追加短句：post-feasible small Pareto/stagnation 下重复 bounded structured/sink exploration before local cleanup。

### 6. 补测试

- [ ] `test_llm_controller.py`：
  - policy snapshot 在 small Pareto + stagnation + mild regression 时进入 `post_feasible_expand`。
  - decision axes 暴露 structured/sink bounded targets。
  - low-success structured exposure target 仍进入 shared primitive candidates。
  - system prompt 保持 compact 且包含 bounded exploration 短规则。
- [ ] `test_llm_prompt_projection.py`：
  - compact operator panel 保留 exposure 字段。

### 7. 聚焦验证

运行：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_prompt_projection.py
```

若失败，按失败用例最小修正；不要跑全仓，除非明确需要。

## Follow-up smoke

聚焦测试通过后，建议下一步再跑 S5 GPT 10×5 smoke，优先检查：

- fallback/retry 仍为 0；
- prompt total 仍在约 9k 级别；
- post-feasible structured + sink share 明显高于旧 20×10；
- local cleanup 不再长期主导。
