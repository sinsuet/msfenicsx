# LLM semantic portfolio planner design

## 背景

S5 aggressive15 的 GPT 20×10 验证显示，LLM provider、prompt compacting、response contract 与 trace 链路已经稳定，但优化结果仍未超过 `union`。本次 run `scenario_runs/s5_aggressive15/0429_2007__raw_union_llm` 中，`llm` 的 PDE evaluations 为 162、skip 为 38，均不劣于 `union` 的 160/40；首个可行 PDE 也同为第 13 次。因此问题不是预算或工程链路，而是 LLM 的每次 PDE 收益较低。

更关键的是，LLM 的后半程从“过度保守”转成了另一种失败模式：`component_subspace_sbx` 与 `sink_shift` 双算子循环。194 次 LLM 决策中，`component_subspace_sbx=85`、`sink_shift=69`、`anchored_component_jitter=23`，前三者占 91%；`vector_sbx_pm=0`、`sink_resize=0`、`component_block_translate_2_4=1`。相比之下，`union` 在同一 primitive substrate 上保持了更均衡的 operator/semantic-role 轮转，最终在 PDE 95-149 之间继续打开更优 basin。

这说明上一版 bounded structured/sink exploration 方向正确，但表达层仍是“给 GPT 一组 primitive operator 和若干 soft labels，然后让它选一个”。论文叙事需要的是：LLM 先理解热布局语义瓶颈，再选择语义搜索任务，最后把任务落到共享 primitive 算子上。

## 目标

把 `LLMOperatorController` 从单步 operator selector 升级为 compact semantic portfolio planner：

1. 显式构造 semantic task taxonomy，把 primitive operator 映射到 `baseline_reset`、`global_layout_expand`、`semantic_block_move`、`semantic_subspace_recombine`、`sink_alignment`、`sink_budget_shape`、`local_polish`。
2. 在 prompt 中暴露 `semantic_task_panel`，把 spatial/regime 状态翻译成 active bottleneck、task order、task rationale。
3. 在 policy kernel 中增加 task-level 与 operator-level portfolio annotation，识别 task debt、operator underexposure、task saturation、operator saturation。
4. 在 `decision_axes` 中把“先选语义任务，再选 operator”变成主决策面。
5. response contract 继续只强制 `selected_operator_id`，但允许 optional `selected_semantic_task`，用于 trace 与 summary。
6. summary 输出 task-level counts/entropy/by-phase，支撑论文中“LLM 在同一 primitive substrate 上做语义编排”的叙事。

## 非目标

- 不修改 raw/union 的 operator pool、预算或算法设置。
- 不硬编码 S5 seed、scenario id 或最终 operator 选择。
- 不把某个 operator 从候选中硬删；portfolio signal 是 prompt-visible soft policy。
- 不恢复旧版长 prompt/menu；新增字段必须 compact、可 trace、可测试。
- 不改 provider profile 或 LLM 模型默认值。

## 设计

### 1. Semantic task taxonomy

新增共享 mapping：

- `vector_sbx_pm -> baseline_reset`
- `component_relocate_1`, `component_swap_2 -> global_layout_expand`
- `component_block_translate_2_4 -> semantic_block_move`
- `component_subspace_sbx -> semantic_subspace_recombine`
- `sink_shift -> sink_alignment`
- `sink_resize -> sink_budget_shape`
- `component_jitter_1`, `anchored_component_jitter -> local_polish`

该 taxonomy 应放在 optimizer-layer 可复用位置，供 `policy_kernel`、`prompt_projection`、`llm_controller`、`llm_summary` 同步使用。

### 2. Semantic task panel

在 controller state/prompt metadata 中新增 `semantic_task_panel`，从 `regime_panel`、`spatial_panel`、`generation_panel` 和 candidate operator set 推导 compact 状态：

- `active_bottleneck`：如 `compact_hotspot_inside_sink`、`sink_misaligned_hotspot`、`objective_stagnation_small_pareto`。
- `recommended_task_order`：当前优先的 semantic tasks。
- `task_rationales`：每个 task 的短 reason。
- `task_operator_candidates`：task 到候选 operator 的映射。

示例：hotspot 已在 sink window、cluster compact、Pareto size 小、frontier stagnation 高时，优先顺序应更偏向 `semantic_block_move / global_layout_expand / sink_budget_shape / local_polish`，而不是继续重复 `sink_alignment`。

### 3. Semantic portfolio annotation

在 `policy_kernel` 的 post-feasible annotation 阶段新增 portfolio 状态：

- 最近窗口内每个 semantic task 的 share。
- 最近窗口内每个 operator 的 share。
- target share 区间：不是严格仿照 union，而是保证 post-feasible expand 下任务组合不过度坍缩。
- `semantic_task_status`：`under_target`、`balanced`、`saturated_no_frontier`。
- `operator_portfolio_status`：`underexposed`、`balanced`、`saturated_no_frontier`。

关键规则：

- 当 `semantic_subspace_recombine` 或 `sink_alignment` 最近窗口过高且没有 frontier credit，标记 saturation。
- 当 `semantic_block_move`、`sink_budget_shape`、`baseline_reset` 在 post-feasible stagnation 中长期低曝光，标记 debt/underexposed。
- saturation/debt 只作为 prompt-visible soft policy；候选仍全部保留。

### 4. Decision axes 升级

`LLMOperatorController._build_decision_axes()` 新增：

- `semantic_portfolio_mode`
- `active_semantic_tasks`
- `semantic_task_debts`
- `semantic_task_saturations`
- `next_task_preference`
- `avoid_repeating_operators`
- `semantic_task_to_operator_candidates`

system prompt 加 compact 规则：

> Choose the semantic task first, then the operator. In post-feasible stagnation, maintain a balanced semantic portfolio; repay task debt before reusing saturated subspace or sink-alignment tasks unless exact positive evidence is strong.

### 5. Optional selected_semantic_task

OpenAI-compatible schema 和 chat/retry prompt 允许 optional `selected_semantic_task`。解析后写入 response trace、decision metadata 和 decision log。若模型不返回该字段，用 selected operator 的 taxonomy 映射推导。

### 6. Task-level summaries

`llm_decision_summary` 增加：

- `semantic_task_counts`
- `semantic_task_entropy`
- `expand_semantic_task_counts`
- `expand_semantic_task_entropy`
- `semantic_task_by_phase`

`llm_decision_log` 增加 `selected_semantic_task`。

## 验证

聚焦测试：

1. `tests/optimizers/test_llm_prompt_projection.py`
   - semantic task fields 进入 compact operator panel。
2. `tests/optimizers/test_llm_policy_kernel.py`
   - subspace/sink_shift 近期过采样且无 frontier credit 时标记 saturation。
   - block/sink_resize/baseline 欠曝光时标记 debt。
3. `tests/optimizers/test_llm_controller.py`
   - decision axes 暴露 task debt/saturation/next task preference。
   - prompt 仍保持 compact budget。
   - optional selected_semantic_task 被记录。
4. `tests/optimizers/test_llm_client.py`
   - schema/解析接受 optional selected_semantic_task。
5. `tests/optimizers/test_llm_decision_summary.py` 或 `test_llm_trace_io.py`
   - summary 输出 semantic task counts/entropy。

验证命令：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_client.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_prompt_projection.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_decision_summary.py
```

若聚焦测试通过，再跑 S5 10×5 smoke 检查 task-level distribution；最后再跑 S5 20×10 GPT 验证是否超过 raw/union。
