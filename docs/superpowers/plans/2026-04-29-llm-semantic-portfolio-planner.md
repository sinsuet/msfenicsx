# LLM semantic portfolio planner implementation plan

## Context

S5 GPT 20×10 run `scenario_runs/s5_aggressive15/0429_2007__raw_union_llm` 证明当前工程链路稳定，但 LLM 没赢 `union`。根因是 LLM 决策从 preserve/local cleanup 偏置变成了 `component_subspace_sbx + sink_shift` 双算子坍缩：它在 prompt 中看到了 bounded structured/sink exploration，却没有一个明确的 semantic task / portfolio 编排层。

本计划实现 design spec `docs/superpowers/specs/2026-04-29-llm-semantic-portfolio-planner-design.md`，目标是让 LLM 先选择语义任务，再选择 primitive operator，并在 trace/summary 中可诊断。

## Implementation Steps

### 1. 新增 semantic task taxonomy

新增文件 `optimizers/operator_pool/semantic_tasks.py`：

- 定义 `SEMANTIC_TASK_BY_OPERATOR`。
- 定义 `SEMANTIC_TASK_LABELS` 或 compact task descriptions。
- 提供 helper：
  - `semantic_task_for_operator(operator_id: str) -> str`
  - `semantic_task_counts(rows)`
  - `semantic_task_entropy(counts)`
  - `operators_by_semantic_task(candidate_operator_ids)`

保持 taxonomy 与当前 `primitive_structured` pool 对齐，同时兼容 legacy/native ids。

### 2. 构造 semantic task panel

修改 `optimizers/operator_pool/state_builder.py`：

- 新增 `_build_prompt_semantic_task_panel(...)`。
- 输入：candidate ids、`regime_panel`、`spatial_panel`、`generation_panel`。
- 输出 compact dict：
  - `active_bottleneck`
  - `recommended_task_order`
  - `task_rationales`
  - `task_operator_candidates`
- 在 `build_controller_state()` 组装 `prompt_panels` 时加入 `semantic_task_panel`。

### 3. 投影 semantic task panel 与 operator task fields

修改 `optimizers/operator_pool/prompt_projection.py`：

- 增加 `_SEMANTIC_TASK_PANEL_PROMPT_KEYS`。
- 在 `_project_prompt_panels()` 中投影 `semantic_task_panel`。
- operator panel post-feasible keys 增加：
  - `semantic_task`
  - `semantic_task_status`
  - `operator_portfolio_status`
  - `portfolio_priority`

### 4. 增加 semantic portfolio annotation

修改 `optimizers/operator_pool/policy_kernel.py`：

- 引入 `semantic_task_for_operator`。
- post-feasible annotation 阶段增加 `_annotate_post_feasible_semantic_portfolio(...)`。
- 统计最近窗口：task share、operator share、frontier credit。
- 标记：
  - `semantic_task_status=under_target | balanced | saturated_no_frontier`
  - `operator_portfolio_status=underexposed | balanced | saturated_no_frontier`
  - `portfolio_priority=repay_task_debt | avoid_saturated_repeat | neutral`
- reason codes 新增：
  - `post_feasible_semantic_portfolio_debt`
  - `post_feasible_semantic_portfolio_saturation`

注意：不改 `allowed_operator_ids`，只做 soft policy。

### 5. 升级 decision axes 与 system prompt

修改 `optimizers/operator_pool/llm_controller.py`：

- `_COMPACT_OPERATOR_PANEL_KEYS` 增加 portfolio 字段。
- `_build_decision_axes()` 从 semantic task panel 和 operator panel 中生成：
  - `semantic_portfolio_mode`
  - `active_semantic_tasks`
  - `semantic_task_debts`
  - `semantic_task_saturations`
  - `next_task_preference`
  - `avoid_repeating_operators`
  - `semantic_task_to_operator_candidates`
- `_request_surface_metadata()` 增加相应 flattened trace 字段。
- `_build_system_prompt()` 加 compact semantic planner rule。

### 6. Optional selected_semantic_task

修改：

- `llm/openai_compatible/schemas.py`
- `llm/openai_compatible/client.py`
- `optimizers/operator_pool/llm_controller.py`

行为：

- JSON schema 允许 optional `selected_semantic_task`。
- dataclass `OpenAICompatibleDecision` 增加 `selected_semantic_task`。
- parse 时如果缺失，则由 `semantic_task_for_operator(selected_operator_id)` 推导。
- response trace 和 decision metadata 记录该字段。
- chat/retry prompt 文案说明 optional key。

### 7. Summary 增加 task-level diagnostics

修改：

- `optimizers/llm_summary.py`
- `optimizers/llm_decision_summary.py`

增加：

- `semantic_task_counts`
- `semantic_task_entropy`
- `expand_semantic_task_counts`
- `expand_semantic_task_entropy`
- `semantic_task_by_phase`
- `selected_semantic_task` 写入 `llm_decision_log.jsonl`

### 8. 聚焦测试

新增/更新测试：

- `tests/optimizers/test_llm_client.py`
  - optional `selected_semantic_task` parse/schema。
- `tests/optimizers/test_llm_policy_kernel.py`
  - saturation/debt annotation。
- `tests/optimizers/test_llm_prompt_projection.py`
  - semantic task panel 与 portfolio fields 进入 prompt。
- `tests/optimizers/test_llm_controller.py`
  - decision axes/task preference/prompt compact budget。
- `tests/optimizers/test_llm_decision_summary.py`
  - task-level summary。

## Verification

先只跑聚焦测试：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q tests/optimizers/test_llm_client.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_prompt_projection.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_decision_summary.py
```

如失败，按 root cause 修复，不跳过测试，不扩大到全仓。聚焦通过后再建议用户运行 S5 10×5 smoke 检查 semantic task distribution；未经用户确认不主动消耗 GPT 20×10 预算。
