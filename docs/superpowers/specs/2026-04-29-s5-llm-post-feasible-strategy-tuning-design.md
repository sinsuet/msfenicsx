# S5 aggressive LLM post-feasible strategy tuning design

## 背景

当前 `nsga2_llm` 的 provider、prompt compacting、response contract 与 trace 链路已经稳定：S5 GPT 20×10 运行无 fallback、无 retry，prompt 大小降到约 9k 字符级别。但 S5 20×10 下 `llm` 仍未超过 `union`，并且低于 `union` 的可行率、最佳 `T_max`、最佳 `gradient_rms`。

这说明瓶颈已经从工程链路转移到 operator policy：GPT 收到的状态面与策略提示仍然把 first-feasible 之后的 S5 aggressive 搜索解释成保守的可行保持/局部清理，而不是持续的 structured/sink basin discovery。

## 证据摘要

S5 GPT 20×10 的关键现象：

- `llm` provider 链路健康：request/response 完整，fallback=0，retry=0。
- 同等预算下 `union` 明显优于 `llm`。
- `union` 的有效路径来自多类算子协作：`component_block_translate_2_4`、`component_subspace_sbx`、`sink_shift`、`sink_resize` 与后期 `component_jitter_1` 精修。
- `llm` 仍过度集中在局部/稳定路线，structured/sink 暴露不足。

源码层面的已知偏置：

- `build_progress_state()` 中 first-feasible 后 preservation dwell 容易把 `post_feasible_mode` 锁到 `preserve`。
- `state_builder` 对非 expand 的 post-feasible 阶段使用 `preserve_fit`，弱化 frontier/structured evidence。
- `policy_kernel` 已有 route budget、stable cooldown、preserve plateau 等机制，但缺少针对 S5 aggressive 风格的 structured/sink 最低暴露提示。
- `llm_controller` 已 compact prompt，但 system prompt 仍没有明确告诉模型：小 Pareto 支撑 + frontier/objective stagnation 时，应重复执行 bounded structured/sink exploration 后再 local cleanup。

## 目标

让 LLM 在 S5 aggressive 这类 first-feasible 之后仍需开新盆地的场景中，形成比 `random_uniform union` 更有节奏的算子分配：

1. first-feasible 后小 Pareto 支撑或 frontier stagnation 时，优先进入/保持 `post_feasible_expand`。
2. structured/sink primitives 获得可见的 underexposed exploration priority。
3. `component_jitter_1` / `component_swap_2` 等 stable/local/global 路线在近期过度集中时不再继续主导。
4. structured primitives 的 early failures 不直接等价为 preserve failure，而被视作 bounded exploration cost。
5. prompt compacting 不回退，新增字段必须短、可诊断、可 trace。

## 非目标

- 不改 provider profile。
- 不扩大 prompt 到旧版长 intent menu。
- 不硬编码 S5 seed、scenario id、operator 最终选择。
- 不改变 raw/union 的算子池或预算。
- 不直接修改生成的 `scenario_runs/` 结果。

## 设计

### 1. Post-feasible expand promotion 放宽

在 `domain_state.build_progress_state()` 和 `policy_kernel.detect_search_phase()` 中，把以下状态视作 expand pressure：

- first feasible 已出现；
- `recent_frontier_stagnation_count >= 2`；
- `diversity_deficit_level in {high, medium}`；
- regression pressure 不是 high，或 regression surplus 至多为 1。

在该状态下，preservation dwell 可以被 expand pressure 打断，避免 first-feasible 后默认吸入 preserve。

### 2. Mixed post-feasible fit

在 `state_builder._build_operator_applicability_row()` 中保留 `post_feasible_expand -> expand_fit`，但对：

- `post_feasible_recover`
- `post_feasible_preserve` 且 `frontier_pressure` 为 medium/high

使用 `max(preserve_fit, expand_fit)` 的 mixed fit。这样不会删除 preserve evidence，但能让有 frontier evidence 的 structured/sink 算子在 stagnation 下露出。

### 3. Structured/sink exposure priority

在 `policy_kernel` 中新增 post-feasible exposure annotation：

- structured target：`component_block_translate_2_4`、`component_subspace_sbx`
- sink target：`sink_shift`、`sink_resize`
- local/global cleanup：`component_jitter_1`、`anchored_component_jitter`、`component_swap_2`、`component_relocate_1`

当 expand pressure 激活且近期 structured/sink 占比低时：

- structured/sink target 标记 `exposure_priority=structured_underexposed` 或 `sink_underexposed`；
- local/global cleanup 若近期占比过高，标记 `exposure_status=local_cleanup_cooldown`。

这些是 soft policy，不直接删候选；通过 prompt projection 和 decision axes 传给 GPT。

### 4. Decision axes 与 system prompt 短提示

在 `LLMOperatorController._build_decision_axes()` 中新增：

- `bounded_exploration_targets`
- `local_cleanup_cooldown_targets`
- `exploration_exposure_mode`

当 bounded exploration targets 非空时，system prompt 加一句短规则：

> In post-feasible stagnation with small Pareto support, repeat bounded structured/sink exploration before local cleanup.

同时允许 `_build_shared_primitive_trial_candidates()` 在 exposure priority 存在时保留 structured primitive，即使它的早期 success rate 或 regression risk 还不理想。

## 验证

聚焦验证顺序：

1. `tests/optimizers/test_llm_controller.py`
   - phase promotion / decision axes / prompt trace / shared primitive candidates。
2. `tests/optimizers/test_llm_prompt_projection.py`
   - exposure 字段进入 compact operator panel。
3. 必要时补充 `tests/optimizers/test_policy_kernel.py` 或在现有 controller 测试中覆盖 policy snapshot。

运行命令：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_controller.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_prompt_projection.py
```

若聚焦测试通过，再跑 S5 GPT 10×5 smoke，先检查 operator distribution，不直接以最终最优值作为唯一判断。
