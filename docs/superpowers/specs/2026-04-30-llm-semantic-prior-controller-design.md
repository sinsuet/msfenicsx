# LLM Semantic Prior Controller 设计

## 背景

两份 2026-04-30 分析已经把当前 LLM 算子选择链路和失败机制拆清楚：

- `docs/reports/2026-04-30-llm-operator-selection-mechanism-s5-case.md`：说明 `llm` 路线不是让模型生成布局，而是在与 `union` 相同的 primitive operator substrate 上，由 LLM 作为 representation-layer controller 选择本地算子。
- `docs/reports/2026-04-30-s5-llm-optimization-chain-review-and-strategy.md`：说明 `scenario_runs/s5_aggressive15/0429_2007__raw_union_llm` 中，LLM 失败的直接机制是 direct selector 造成 operator portfolio collapse。`llm` 在后半程几乎坍缩成 `component_subspace_sbx + sink_shift`，而随机 `union` 由于保持广覆盖，在同一 substrate 上取得更好目标值和 hypervolume。

随后讨论形成了新的论文边界：不把方法扩展成完整 AOS / bandit 系统，不引入重的在线 credit assignment，也不让机制盖过 LLM 语义理解。主方法应突出：

> LLM 将热布局优化状态解释为语义搜索意图，并输出 semantic task / operator prior；一个轻量、LLM 专属的 constrained sampler 只负责把 prior 稳定落成实际算子，防止小预算下的先验坍缩。

这个设计保留 `raw` 和 `union` 的主线干净：

- `raw` 不动。
- `union` 不动，仍是 `random_uniform` over shared primitive operator pool。
- 新机制只进入 `operator_control.controller: llm` 的 LLM 路径。
- 本轮不实现 `llm_direct` 或 `uniform_prior_sampler` 额外 baseline。论文当前比较仍先保持 `raw / union / new_llm`。

## 目标

实现 `LLM Semantic Prior Controller`：

1. LLM 不再在新策略下直接输出最终 `selected_operator_id`，而是输出：
   - `semantic_task_priors`
   - `operator_priors`
   - per-operator `risk`
   - per-operator 或整体 `confidence`
   - compact `rationale`
2. LLM 专属 sampler 根据这些 priors 进行概率采样，而不是 argmax。
3. sampler 只包含必要稳定化机制：
   - legality candidate mask：只在当前候选 operator pool 中采样。
   - generation cap：防止单个 operator 在同一 generation 中垄断。
   - rolling exposure cap：防止最近窗口重复选择同一 operator 或 semantic task。
   - entropy / probability floor：保证非饱和候选仍有最小探索概率。
   - risk penalty：高风险 operator 降权，而不是完全删除。
4. trace 中完整记录 LLM prior 与 sampler 结果：
   - `llm_operator_priors`
   - `llm_semantic_task_priors`
   - `sampler_probabilities`
   - `selected_probability`
   - `sampler_suppressed_operator_ids`
   - `sampler_config`
5. active paper-facing LLM specs 启用新策略；`raw` / `union` specs 不变。

## 非目标

- 不修改 `nsga2_raw` 和 `nsga2_union` 链路。
- 不改变 shared primitive operator registry。
- 不让 LLM 生成 32D 决策向量。
- 不引入完整 contextual AOS / UCB / Thompson Sampling / EXP3。
- 不实现 `llm_direct` 和 `uniform_prior_sampler` 对照组。
- 不把 S5、seed 11、某个具体 operator 名称写成特调例外。
- 不手工修改已有 `scenario_runs/` artifact。
- 不用 prompt 硬编码“必须选某个 operator”；最终仍由 LLM prior 和通用 sampler 共同决定。

## 当前基础

当前代码已经有可复用基础：

- `optimizers/operator_pool/semantic_tasks.py`
  - 已有 operator -> semantic task mapping。
  - 已有 semantic task entropy/count helpers。
- `optimizers/operator_pool/state_builder.py`
  - 已生成 `semantic_task_panel`。
  - 已提供 `generation_local_memory` 和 `recent_decisions`，可作为 exposure cap 输入。
- `optimizers/operator_pool/policy_kernel.py`
  - 已为 operator annotation 增加 `semantic_task_status`、`operator_portfolio_status`、`portfolio_priority`。
  - 已实现 adaptive sink gate。
- `optimizers/operator_pool/llm_controller.py`
  - 已构造 prompt metadata、decision axes、request/response trace。
  - 当前仍以 `OpenAICompatibleDecision.selected_operator_id` 作为最终动作。
- `llm/openai_compatible/client.py`
  - 当前只支持 `request_operator_decision()`，解析单个 selected operator。
- `llm/openai_compatible/schemas.py`
  - 当前 structured output schema 只强制 `selected_operator_id`。

因此本次不是重建 LLM controller，而是在现有 semantic portfolio layer 上增加 “prior advice -> constrained sampling” 的选择路径。

## 设计

### 1. 新增 LLM prior advice contract

新增一个与现有 direct decision contract 并行的 contract：

```json
{
  "phase": "post_feasible_expand",
  "rationale": "当前可行性稳定但 Pareto 扩展停滞，应保留局部修复和结构扩展的混合概率，降低已饱和 subspace/sink repeat。",
  "semantic_task_priors": [
    {
      "semantic_task": "local_polish",
      "prior": 0.24,
      "risk": 0.20,
      "confidence": 0.55
    },
    {
      "semantic_task": "semantic_block_move",
      "prior": 0.20,
      "risk": 0.38,
      "confidence": 0.45
    }
  ],
  "operator_priors": [
    {
      "operator_id": "anchored_component_jitter",
      "prior": 0.22,
      "risk": 0.25,
      "confidence": 0.55,
      "rationale": "local gradient cleanup with bounded geometry disruption"
    },
    {
      "operator_id": "component_block_translate_2_4",
      "prior": 0.18,
      "risk": 0.40,
      "confidence": 0.42,
      "rationale": "frontier diversification without repeating saturated subspace"
    }
  ]
}
```

约束：

- `operator_id` 必须来自 `candidate_operator_ids`。
- `prior`、`risk`、`confidence` 统一 clamp 到 `[0.0, 1.0]`。
- 允许 operator prior 不覆盖全部候选；缺失候选由 sampler 补 0 后再混合 uniform floor。
- `semantic_task_priors` 作为补充信号；如果 operator prior 全缺失或全为 0，可按 task prior 均匀分配到该 task 的 candidate operators。
- `rationale` 必须 compact，目标是可解释，不是长篇 reasoning。

### 2. LLM 专属 constrained sampler

新增 sampler 层，只在 `selection_strategy: semantic_prior_sampler` 时启用。

输入：

- `candidate_operator_ids`
- LLM prior advice
- `ControllerState`
- sampler config
- rng

输出：

- `selected_operator_id`
- `selected_probability`
- `sampler_probabilities`
- `suppressed_operator_ids`
- `cap_reasons`
- `normalized_operator_priors`

采样流程：

1. 归一化 LLM operator priors。
2. 若 operator priors 不可用，用 semantic task priors 展开到 operators。
3. 对每个 operator 应用 risk penalty：

   ```text
   adjusted_weight = prior * max(0, 1 - risk_penalty_weight * risk)
   ```

4. 若所有 adjusted weights 为 0，退回 uniform over candidates。
5. 与 uniform mix 混合：

   ```text
   mixed_weight = (1 - uniform_mix) * adjusted_probability + uniform_mix * uniform_probability
   ```

6. 应用 generation cap：
   - 使用 `state.metadata["generation_local_memory"]["operator_counts"]`。
   - 如果某 operator 在当前 generation 的 accepted count 达到 `ceil(target_offsprings * generation_operator_cap_fraction)`，将其暂时 suppress。
   - 如果 suppress 后没有候选，则取消该 cap，保持可运行。
7. 应用 rolling exposure cap：
   - 使用 `state.metadata["recent_decisions"]` 的最近窗口。
   - 如果某 operator 的 rolling share 超过 `rolling_operator_cap_fraction`，暂时 suppress。
   - 如果某 semantic task 的 rolling share 超过 `rolling_semantic_task_cap_fraction`，暂时 suppress 该 task 中没有强 positive evidence 的 operators。
   - 如果 suppress 后没有候选，则取消该 cap。
8. 对剩余 active candidates 应用 probability floor：
   - `min_probability_floor` 只给未 suppress 的候选。
   - floor 后重新归一化。
9. 用 rng 按最终概率采样。

默认配置建议：

```yaml
selection_strategy: semantic_prior_sampler
semantic_prior_sampler:
  uniform_mix: 0.15
  min_probability_floor: 0.03
  generation_operator_cap_fraction: 0.35
  rolling_operator_cap_fraction: 0.40
  rolling_semantic_task_cap_fraction: 0.55
  rolling_window: 16
  risk_penalty_weight: 0.50
```

这些参数只进入 LLM controller，不影响 `union` 的 `random_uniform`。

### 3. Prompt 改造

`selection_strategy=semantic_prior_sampler` 时使用 prior-specific system prompt：

```text
Return semantic/operator priors, not a final selected operator.
Estimate which semantic tasks and candidate operators should receive probability mass.
Keep priors calibrated: low evidence means low confidence.
Penalize saturated recent operators and saturated semantic tasks.
The downstream sampler will enforce exposure caps and sample from your priors.
Return JSON only.
```

删除 direct selector 中容易诱导坍缩的强表述在 prior prompt 中不再出现：

- 不说 `Treat exact positive retrieval matches strongest`。
- 不说 `repeat bounded structured/sink exploration before local cleanup`。
- 不把“exact positive”作为压倒性规则，只作为 `confidence` 的一个来源。

direct decision strategy 可保留旧 prompt 以保持 legacy path，但 active LLM specs 应切换到 prior strategy。

### 4. Controller 集成

`LLMOperatorController.select_decision()` 按策略分流：

```text
selection_strategy == "direct_operator"
  -> 旧 request_operator_decision path

selection_strategy == "semantic_prior_sampler"
  -> request_operator_prior_advice
  -> semantic prior sampler
  -> ControllerDecision(selected_operator_id=sampled_operator)
```

返回的 `ControllerDecision.metadata` 需要包含：

- LLM advice 原始 payload。
- LLM semantic task priors。
- LLM operator priors。
- sampler probabilities。
- sampled operator 的 probability。
- cap/floor 是否触发。
- sampled operator 对应的 `selected_semantic_task`。

`controller_trace.jsonl` 仍保留 `operator_selected` 字段，值为 sampler 最终选中的 operator，这样下游 trace / render / compare 不需要重写。

### 5. Spec 配置边界

只更新 active paper-facing LLM specs：

- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/s2_staged_llm.yaml`
- `scenarios/optimization/s3_scale20_llm.yaml`
- `scenarios/optimization/s4_dense25_llm.yaml`
- `scenarios/optimization/s5_aggressive15_llm.yaml`

不修改：

- `*_raw.yaml`
- `*_union.yaml`
- `profiles/*_raw.yaml`
- `profiles/*_union.yaml`

`max_output_tokens` 需要从 128 提高到能容纳 prior JSON 的值。建议 active LLM specs 设为 `512`，并通过 prompt 要求每个 operator rationale 保持短句，避免 response 过长。

### 6. Trace 与总结

现有 `llm_summary.py` 和 `llm_decision_summary.py` 已有 semantic task 统计。本次新增 prior/sampler 字段后，最小要求是：

- response trace 可看到 LLM prior 与 sampler final probability。
- decision log 可看到 `selected_semantic_task`。
- 不要求本轮新增复杂图表。

后续如果需要，可以再把 `sampler_probabilities` 聚合成 operator probability heatmap，但不作为本次目标。

## 论文叙事

主方法命名建议：

> LLM Semantic Prior over a Shared Primitive Operator Substrate

核心表述：

> LLM does not generate design vectors or replace NSGA-II. It interprets optimization state into semantic search priors over a shared primitive operator substrate. A lightweight constrained sampler only prevents prior collapse under small evaluation budgets.

中文表述：

> LLM 不直接生成解，也不替代优化器；它把热布局优化状态解释为语义搜索先验。采样器只是稳定化层，用来防止小预算下先验过度集中。

这能避免 reviewer 认为贡献来自复杂 AOS / bandit，同时比 direct LLM selector 更稳。

## 验证

聚焦测试：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_semantic_prior_sampler.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_s5_aggressive15_specs.py
```

基础合同测试：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -q \
  tests/optimizers/test_algorithm_ladder_contracts.py \
  tests/optimizers/test_operator_pool_contracts.py
```

运行验证建议：

1. 先跑 S5 10×5 本地 smoke，确认 trace 中有 `llm_operator_priors` 与 `sampler_probabilities`，并检查 operator distribution 不再出现第 6-10 代双算子坍缩。
2. 再跑 S5 GPT 20×10，与 `scenario_runs/s5_aggressive15/0429_2007__raw_union_llm` 和 `scenario_runs/s5_aggressive15/0430_1140__llm_gpt_20x10_adaptive_sink_gate` 做机制解释对比。
3. 若 S5 稳定，再扩展到 S1/S2/S3/S4，比较仍以 `raw / union / new_llm` 为主，不引入额外 baseline。

成功标准：

- `raw` / `union` artifact 和 spec 无变更。
- LLM trace 明确显示 prior -> sampler -> selected operator 的链路。
- LLM operator entropy 高于 direct selector 坍缩 run。
- S5 20×10 不再后半程固定在 `component_subspace_sbx + sink_shift`。
- 性能报告只对具体 run-root 做结论，不用单 seed 夸大统计显著性。
