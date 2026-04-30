# S5 LLM sink-budget 自适应 gate 设计

## 背景

S5 GPT 20×10 的连续验证表明，`sink_budget_shape` 既不是应当长期主导的 exploitation 算子族，也不能在 post-feasible 阶段被硬性降权。上一轮 `stage-policy` 运行中，`sink_resize` 总次数为 53，expand 阶段 `sink_budget_shape` 为 36，最终达到 `bestT=324.7156`、`bestG=17.8788`。随后硬降权版本把 `sink_resize` 降到 24、expand 阶段 `sink_budget_shape` 降到 11，但可行率从 0.515 退到 0.495，PDE 从 161 退到 151，最终目标退化到 `bestT=325.5907`、`bestG=18.2733`。这说明 `sink_budget_shape` 在 S5 aggressive 中承担早中期可行流形稳定器作用，问题应定义为“何时降权”，不是“是否降权”。

## 目标

本次改动将 controller 的 post-feasible 语义策略改为自适应 gate：早中期保留 `sink_budget_shape` 的稳定化价值，后期在可行率已经足够、frontier 已经停滞且 `sink_resize` 没有 frontier credit 时，才把预算窗口调整从主要任务降为饱和重复，转向 `semantic_block_move`、`semantic_subspace_recombine` 和 `local_polish`。

## 策略设计

`policy_kernel` 中的 sink-budget 降权逻辑应满足以下条件才触发：当前 phase 属于 `post_feasible_expand` 或 `post_feasible_preserve`；`feasible_rate >= 0.50`；`recent_frontier_stagnation_count >= 6`；没有 sink-budget 主违规，也没有近期可行性回退压力；并且候选 `sink_resize` / `sink_budget_shape` 没有 `pareto_contribution_count`、`frontier_novelty_count` 或 `recent_expand_frontier_add_count`。如果这些条件不满足，`sink_budget_shape` 继续保持稳定器角色，不因全局选择次数高而被硬性判为饱和。

`state_builder` 中的 semantic task 排序应同步使用同一 gate 思路。post-feasible expand 的早中期，`sink_budget_shape` 可以保留在中前位，尤其当可行率不足 0.50 或 sink-budget 仍有真实压力时。只有当 gate 触发时，推荐任务顺序才把 `semantic_block_move`、`semantic_subspace_recombine`、`local_polish` 放在 `sink_budget_shape` 之前。`baseline_reset` 在 post-feasible expand 的局部拥挤或 frontier stagnation 下仍作为后备锚点，不应仅因 recent share 为零抢占 exploitation 任务前位。

## 测试设计

先更新和新增 focused tests。`test_llm_policy_kernel.py` 应覆盖两类场景：可行率不足 0.50 时，即便 `sink_resize` 历史选择较多，也不应被标为 `avoid_saturated_repeat`；可行率达到 0.50 且 frontier stagnation 足够高时，无 frontier credit 的 `sink_resize` 应被标为 `saturated_no_frontier`。`test_llm_controller_state.py` 应覆盖 semantic panel 排序：早中期不把合法满额 sink 直接视为预算压力；late-stagnation gate 触发时 exploitation 任务优先于 `sink_budget_shape`。

## 验证

实现后先运行 focused tests：`tests/optimizers/test_llm_policy_kernel.py`，以及 `tests/optimizers/test_llm_controller_state.py` 中相关 semantic panel 测试。随后运行 `git diff --check`。如果 focused tests 通过，再启动一次 S5 GPT 20×10：`run-llm default --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml --evaluation-workers 2 --population-size 20 --num-generations 10`，输出目录使用新的时间戳和 `llm_gpt_20x10_adaptive_sink_gate` 后缀。完成后对比上一轮 `0430_0146__llm_gpt_20x10_stage_policy` 与 `0430_0902__llm_gpt_20x10_sink_debt_policy`。

## 非目标

本次不调整 LLM provider、prompt schema、基础 operator registry 或 S5 scenario YAML。也不直接追求降低 `sink_resize` 的绝对次数；目标是让 `sink_resize` 的使用时机更符合阶段语义，并观察 20×10 预算下的可行率、PDE 利用率和 Pareto 质量是否恢复。