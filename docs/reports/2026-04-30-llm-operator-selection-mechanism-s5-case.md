# LLM 算子选择链路与机制分析

日期：2026-04-30

关联案例：`scenario_runs/s5_aggressive15/0430_1140__llm_gpt_20x10_adaptive_sink_gate`

## 1. 核心结论

当前 `nsga2_llm` 路线不是让 LLM 直接生成布局，也不是让 LLM 直接输出 32 维决策向量。它的准确角色是：

> 在与 `union` 相同的 primitive operator 支持集上，LLM 作为 representation-layer controller，为每一次 offspring proposal 选择一个本地算子。

也就是说，真实链路是：

```text
NSGA-II 父代选择
-> 构造 ControllerState
-> policy kernel 识别阶段并生成软策略标注
-> prompt projection 压缩上下文
-> LLM 只选择 selected_operator_id
-> 本地 OperatorDefinition.propose() 生成数值候选
-> repair / duplicate filtering / cheap constraints / PDE solve / evaluation
-> trace 与 artifact 记录
```

其中 `llm` 相对 `union` 的差异只在 controller：

- `union`：同一套算子池，由 `random_uniform` 等非 LLM controller 调度。
- `llm`：同一套算子池，由 LLM 读取结构化上下文后调度。

S5 最新 run 的 trace 也验证了这一点：184 次 LLM request/response 中，每次原始候选池和有效候选池都是 9 个，`fallback=0`，`retry=0`。LLM 的输出始终只是候选算子 ID，后续候选向量由本地算子代码产生。

## 2. 入口与运行配置

### 2.1 CLI 入口

LLM 路线通过 optimizer CLI 进入：

- `optimizers/cli.py`
- `optimizers/drivers/union_driver.py`
- `optimizers/adapters/genetic_family.py`

`run-llm` 会要求 optimization spec 中存在：

```yaml
operator_control:
  controller: llm
```

并通过 LLM profile 把具体 provider 信息临时映射到统一运行时环境变量：

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

profile 定义在 `llm/openai_compatible/profiles.yaml`。当前 `gpt` / `default` profile 都映射到 `gpt-5.4`。

### 2.2 S5 spec 的关键含义

案例 spec：`scenarios/optimization/s5_aggressive15_llm.yaml`

关键配置是：

```yaml
algorithm:
  family: genetic
  backbone: nsga2
  mode: union
  population_size: 20
  num_generations: 10
  seed: 7

operator_control:
  controller: llm
  registry_profile: primitive_structured
```

这里容易误读的一点是：`algorithm.mode` 仍然是 `union`。这是因为 LLM 路线复用 union adapter，只把 `operator_control.controller` 换成 `llm`。`run.yaml` 中展示的 `mode: llm` 是 suite/reporting 视角下的模式标签，不表示优化主干变成了一个新算法。

案例 run manifest：

- run root：`scenario_runs/s5_aggressive15/0430_1140__llm_gpt_20x10_adaptive_sink_gate`
- benchmark seed：11
- algorithm seed：7
- population：20
- generations：10
- legality policy：`projection_plus_local_restore`
- wall seconds：`797.3507333419984`

## 3. 候选算子池与公平性边界

S5 使用 `primitive_structured` registry profile。该 profile 定义在 `optimizers/operator_pool/primitive_registry.py`，候选算子为 9 个：

| operator | 语义角色 |
| --- | --- |
| `vector_sbx_pm` | NSGA-II 原生 SBX + polynomial mutation 锚点 |
| `component_jitter_1` | 单组件局部扰动 |
| `anchored_component_jitter` | 与 sink/热点语义耦合的局部扰动 |
| `component_relocate_1` | 单组件重定位 |
| `component_swap_2` | 两组件交换 |
| `sink_shift` | 保持 span 的 sink 平移 |
| `sink_resize` | sink span/窗口形状调整 |
| `component_block_translate_2_4` | 2 到 4 个组件块平移 |
| `component_subspace_sbx` | 子空间结构化重组 |

这个边界是论文比较的关键：

- `union` 和 `llm` 使用同一个 operator registry。
- `llm` 不新增专属算子。
- `llm` 不直接写设计变量。
- repair、legality policy、evaluation spec 与主干预算保持一致。

当前 policy kernel 虽然有 “filter / suppression / cooldown” 等命名，但在 paper-facing 当前实现中，`PolicySnapshot.allowed_operator_ids` 保持为原始候选集合，`suppressed_operator_ids=()`。也就是说，策略层主要把阶段、风险、证据、portfolio 债务等信息转成 prompt 软约束和 operator annotations，而不是硬缩小动作空间。`tests/optimizers/test_llm_policy_kernel.py` 中的 `_assert_snapshot_preserves_support()` 也明确断言这一点。

S5 案例的 trace 进一步验证：

```text
184 / 184 request: original_candidate_operator_ids = 9
184 / 184 request: candidate_operator_ids = 9
```

## 4. 每次 LLM 决策的执行链路

一次 LLM 决策发生在 NSGA-II infill/proposal 阶段，不发生在 PDE solve 之后。更细地说：

1. `run_union_optimization()` 读取 spec 和 evaluation spec，初始化单 case optimization problem。
2. `build_genetic_union_algorithm()` 先构建 raw NSGA-II backbone。
3. adapter 保存 raw mating，然后把 `algorithm.mating` 替换成 `GeneticFamilyUnionMating`。
4. 每个 generation 中，NSGA-II selection 先选出父代行。
5. `GeneticFamilyUnionMating._build_event_record()` 构造 `ParentBundle` 和 `ControllerState`。
6. `select_controller_decision()` 调用 `LLMOperatorController.select_decision()`。
7. LLM 返回 `selected_operator_id`。
8. `_event_proposals()` 调用 `get_operator_definition(selected_operator_id).propose(...)`。
9. 本地算子输出 proposal vector。
10. proposal 经过 repair、raw duplicate filtering、repaired duplicate filtering。
11. 只有通过筛选的 offspring 才进入 evaluation。
12. evaluation 先走 cheap constraints，再需要时进入 PDE solve，最后写入 history/artifacts/trace。

关键点：LLM 决策和 expensive evaluation 之间还有本地工程层。LLM 选了某个 operator，并不等价于该次决策一定进入 PDE；如果产生重复、被 batch truncate 或被筛掉，决策会留在 controller/decision outcome 中，但不会形成 operator/evaluation 记录。

S5 案例中：

- LLM decisions：184
- applied decisions：167
- not applied decisions：17
- `operator_trace.jsonl` rows：180

`operator_trace` 行数大于 applied decision 数，是因为 `vector_sbx_pm` 这类原生 SBX 路径可能一次 decision 产生两个 offspring trace rows。

## 5. ControllerState 上下文怎么构造

`ControllerState` 由 `optimizers/operator_pool/state_builder.py` 构造。它不是原始日志拼接，而是从优化历史、父代、空间几何和算子历史中提取结构化摘要。

核心输入包括：

- `parents`：当前 proposal 的父代决策向量。
- `family/backbone`：例如 `genetic/nsga2`。
- `generation_index` / `evaluation_index` / `decision_index`。
- `candidate_operator_ids`。
- `controller_trace` / `operator_trace`：过去 controller 和实际算子执行记录。
- `history`：已经完成的 optimization evaluation history。
- `recent_window`：S5 spec 中为 16。
- `radiator_span_max`、设计变量 ID、native NSGA-II 参数等。

有历史记录时，会进一步生成：

| state 字段 | 含义 |
| --- | --- |
| `run_state` | evaluations used/remaining、feasible rate、first feasible eval、当前 best objective、sink utilization |
| `parent_state` | 父代可行性、约束、objective、与历史记录的对应关系 |
| `archive_state` | Pareto/frontier、可行/不可行演化、近期 regression/preservation |
| `domain_regime` | 领域阶段、主导约束族、sink budget bucket 等 |
| `progress_state` | post-feasible mode、stagnation、recover/preserve/expand 状态 |
| `spatial_panel` | 热点与 sink 关系、最近间距、紧凑度、sink span bucket |
| `retrieval_panel` | 相似 regime 下的正/负 operator 证据 |
| `operator_summary` | 每个 operator 的选择数、proposal 数、可行进入/保持/回退、frontier 贡献等 |
| `generation_local_memory` | 当前 generation 内已接受 offspring 的局部算子分布 |

这些信息随后被组织成 prompt panels：

```text
run_panel
regime_panel
parent_panel
spatial_panel
retrieval_panel
operator_panel
semantic_task_panel
generation_panel
```

## 6. Policy Kernel：阶段识别与软策略标注

`optimizers/operator_pool/policy_kernel.py` 负责把 ControllerState 转成 `PolicySnapshot`。它做三件事：

1. `detect_search_phase()` 判断当前阶段。
2. `score_operator_evidence()` 给每个 operator 计算 evidence/role/risk。
3. 各类 `_annotate_*()` 函数把阶段策略、portfolio 暴露、route family、semantic task 债务、sink gate 等信息写入 candidate annotations。

常见阶段包括：

- `cold_start`
- `prefeasible_progress`
- `prefeasible_stagnation`
- `prefeasible_convert`
- `post_feasible_recover`
- `post_feasible_preserve`
- `post_feasible_expand`

post-feasible 阶段的主要策略含义：

| phase | 控制意图 |
| --- | --- |
| `post_feasible_recover` | 可行域刚出现或近期回退压力高，优先保护可行集 |
| `post_feasible_preserve` | 已有可行解，优先稳定可行性，降低 regression |
| `post_feasible_expand` | 可行性较稳定时，允许有边界的 frontier 扩展 |

当前实现的重点不是硬过滤，而是生成 prompt 可读的信号，例如：

- `post_feasible_stable_low_success_cooldown`
- `post_feasible_semantic_portfolio_debt`
- `post_feasible_semantic_portfolio_saturation`
- `post_feasible_bounded_exploration_exposure`
- `post_feasible_preserve_low_regression_bias`
- `post_feasible_recover_preserve_bias`
- `post_feasible_preserve_positive_credit_visibility`

这些 reason code 会进入 `phase_policy.reason_codes` 和 request/response trace，LLM 看到的是 “为什么当前阶段应该偏向某类选择”。

## 7. Prompt 结构

Prompt 由两部分组成：

```text
system_prompt: 固定策略说明 + 当前 phase/policy guidance
user_prompt: JSON 压缩后的 ControllerState projection
```

### 7.1 System prompt 的职责

`LLMOperatorController._build_system_prompt()` 的核心约束是：

- 只选择一个 operator。
- 返回值必须来自 `candidate_operator_ids`。
- 不返回 design vector。
- 优先使用 `metadata.decision_axes`。
- 再结合 `operator_panel` evidence、intent、phase、objective balance、frontier/preserve pressure、applicability、retrieval、risk。
- policy 是 soft，除非候选集真的变化。
- sink-budget 算子只在 sink bottleneck 活跃时优先。
- 先选 semantic task，再选 operator。

因此 LLM 的任务不是“优化布局”，而是“在当前上下文下调度一个本地 proposal operator”。

### 7.2 User prompt 的结构

`user_prompt` 是 JSON，字段大致为：

```json
{
  "family": "genetic",
  "backbone": "nsga2",
  "generation_index": 10,
  "evaluation_index": 190,
  "parent_count": 2,
  "vector_size": 32,
  "candidate_operator_ids": ["..."],
  "metadata": {
    "phase_policy": {},
    "intent_panel": {},
    "decision_axes": {},
    "prompt_panels": {}
  }
}
```

其中最重要的是 `decision_axes`，它把大量 panel 信息再压成面向选择的决策轴，例如：

- `objective_balance_pressure`
- `preferred_effect`
- `stagnant_objectives`
- `improving_objectives`
- `peak_improve_candidates`
- `gradient_improve_candidates`
- `regression_risk`
- `preserve_score`
- `frontier_score`
- `active_semantic_tasks`
- `next_task_preference`
- `semantic_task_debts`
- `semantic_task_saturations`
- `avoid_repeating_operators`
- `exact_positive_match_operator_ids`
- `route_family_mode`
- `generation_dominant_operator_id`

`operator_panel` 在传输前会被压缩成 columns/rows，避免重复 JSON key 导致 prompt 过长。S5 案例中 prompt 总字符数：

| 指标 | 数值 |
| --- | ---: |
| min | 10582 |
| avg | 12275.1 |
| median | 12292.5 |
| max | 13427 |

## 8. 模型调用、schema、retry 和 fallback

LLM transport 位于：

- `llm/openai_compatible/config.py`
- `llm/openai_compatible/client.py`
- `llm/openai_compatible/schemas.py`

S5 spec 使用：

```yaml
provider: openai-compatible
capability_profile: chat_compatible_json
performance_profile: balanced
max_output_tokens: 128
temperature: 0.7
retry:
  max_attempts: 2
  timeout_seconds: 35
fallback_controller: random_uniform
```

输出 schema 的最小必需字段是：

```json
{
  "selected_operator_id": "one candidate id"
}
```

可选字段包括：

- `selected_intent`
- `selected_semantic_task`
- `phase`
- `rationale`

client 会做以下校验：

1. 去掉 markdown code fence。
2. JSON parse。
3. 兼容旧字段 `operator_id -> selected_operator_id`。
4. 校验 `selected_operator_id in candidate_operator_ids`。
5. 如果响应文本中唯一出现了某个候选 ID，可尝试 recover。
6. 仍非法则 retry。
7. retry 耗尽或请求异常，则 fallback 到 `random_uniform`。

S5 案例运行结果：

| 指标 | 数值 |
| --- | ---: |
| request | 184 |
| response | 184 |
| model | `gpt-5.4` |
| fallback | 0 |
| retry | 0 |
| latency min | 1718.88 ms |
| latency avg | 2511.95 ms |
| latency median | 2180.82 ms |
| latency max | 10568.99 ms |

## 9. 算子执行、repair 和 evaluation

LLM 选择结束后，执行权回到本地代码：

```text
selected_operator_id
-> get_operator_definition(selected_operator_id)
-> OperatorDefinition.propose(parents, state, variable_layout, rng)
-> proposal vector
```

随后统一走：

- `repair`
- duplicate filtering
- assisted repaired-key screening
- accepted trace append
- cheap constraints
- PDE solve
- evaluation report
- Pareto/history update

这解释了两个现象：

1. LLM 可以选择 `sink_resize`，但如果生成的候选与已有修复后向量重复，仍可能不进入 evaluation。
2. LLM 的 rationale 不能直接证明目标改善；真正的效果必须看后续 `operator_trace.jsonl`、`evaluation_events.jsonl`、`optimization_result.json` 和 rendered analytics。

S5 案例的 not-applied 统计：

| operator | not applied decisions |
| --- | ---: |
| `sink_resize` | 15 |
| `component_subspace_sbx` | 2 |

`sink_resize` 不进入 evaluation 的比例较高，说明在该 run 的后段，sink span 已经经常贴近 budget 上限，resize 更容易生成重复或无效的修复后候选。这不表示 LLM 调用失败，而是本地 proposal/repair/filter 层拒绝了部分候选。

## 10. Trace 与可审计性

案例 run 的关键文件：

| 文件 | 作用 |
| --- | --- |
| `traces/llm_request_trace.jsonl` | 每次 LLM 调用前的候选池、policy phase、reason codes、system/user prompt |
| `traces/llm_response_trace.jsonl` | LLM 返回的 operator、semantic task、intent、rationale、latency、fallback/retry |
| `traces/controller_trace.jsonl` | controller 层摘要：decision id、phase、operator selected、prompt ref、digest |
| `traces/operator_trace.jsonl` | 实际进入 evaluation 的 operator proposal rows |
| `traces/evaluation_events.jsonl` | 每次 evaluation 的 objective、constraint、solver status |
| `traces/generation_summary.jsonl` | generation 级聚合 |
| `analytics/decision_outcomes.csv` | decision 是否 applied、latency、hypervolume 字段 |
| `optimization_result.json` | 完整 history、Pareto front、representatives |
| `prompts/*.md` | prompt store 保存的可复盘 prompt/response 片段 |

这套 trace 能回答三类问题：

- LLM 当时看到了什么上下文？
- LLM 为什么选择该 operator？
- 该 operator 是否真的产生了 evaluated offspring，并对 Pareto/history 有什么影响？

## 11. S5 最新 run 总体复盘

### 11.1 运行规模

案例：`scenario_runs/s5_aggressive15/0430_1140__llm_gpt_20x10_adaptive_sink_gate`

| 项 | 数值 |
| --- | ---: |
| population | 20 |
| generations | 10 |
| optimization history rows | 201 |
| feasible rows | 96 |
| first feasible eval | 14 |
| Pareto front size | 1 |
| LLM decisions | 184 |
| applied decisions | 167 |
| not applied decisions | 17 |
| operator trace rows | 180 |

最终 Pareto 只有 1 个点：

| eval | `summary.temperature_max` | `summary.temperature_gradient_rms` |
| ---: | ---: | ---: |
| 190 | 324.6697231912805 | 18.60929017834291 |

对应 representative 满足所有 active constraints，`case.total_radiator_span = 0.34999999999999987`，刚好贴住 `radiator_span_budget <= 0.35`。

### 11.2 LLM 选择分布

LLM response 中的 operator 选择次数：

| operator | selected |
| --- | ---: |
| `sink_resize` | 32 |
| `anchored_component_jitter` | 28 |
| `sink_shift` | 24 |
| `component_relocate_1` | 23 |
| `component_subspace_sbx` | 21 |
| `component_block_translate_2_4` | 18 |
| `component_swap_2` | 16 |
| `vector_sbx_pm` | 14 |
| `component_jitter_1` | 8 |

applied decision 中的 operator 分布：

| operator | applied decisions |
| --- | ---: |
| `anchored_component_jitter` | 28 |
| `sink_shift` | 24 |
| `component_relocate_1` | 23 |
| `component_subspace_sbx` | 19 |
| `component_block_translate_2_4` | 18 |
| `sink_resize` | 17 |
| `component_swap_2` | 16 |
| `vector_sbx_pm` | 14 |
| `component_jitter_1` | 8 |

注意：`operator_trace.jsonl` 以 offspring row 记录，`vector_sbx_pm` 在 row 级别是 27 行，因为部分 SBX event 产生两个 offspring；上表按 unique applied decision 统计。

### 11.3 阶段分布

LLM response 的 policy phase：

| phase | count |
| --- | ---: |
| `post_feasible_preserve` | 75 |
| `post_feasible_recover` | 64 |
| `post_feasible_expand` | 45 |

这说明该 run 在 first feasible 之后大部分时间处于 “保护可行集 / 从回退中恢复” 的模式，只有 45 次进入 expand。

semantic task 分布：

| semantic task | count |
| --- | ---: |
| `global_layout_expand` | 39 |
| `local_polish` | 36 |
| `sink_budget_shape` | 32 |
| `sink_alignment` | 24 |
| `semantic_subspace_recombine` | 21 |
| `semantic_block_move` | 18 |
| `baseline_reset` | 14 |

这与 S5 aggressive 的物理状态一致：组件密度高，sink span 贴近预算，布局 spacing 与 thermal limit 都会反复成为主导压力。

### 11.4 主要 policy reason codes

| reason code | count |
| --- | ---: |
| `post_feasible_semantic_portfolio_debt` | 64 |
| `post_feasible_stable_low_success_cooldown` | 63 |
| `post_feasible_preserve_low_regression_bias` | 56 |
| `post_feasible_semantic_portfolio_saturation` | 55 |
| `post_feasible_recover_positive_credit_visibility` | 45 |
| `post_feasible_bounded_exploration_exposure` | 36 |
| `post_feasible_recover_preserve_bias` | 19 |
| `post_feasible_preserve_positive_credit_visibility` | 19 |
| `post_feasible_preserve_plateau_cooldown` | 1 |

这组 reason code 说明：controller 不是单纯追求某个 operator 的局部成功率，而是在 “可行保持、低回退、semantic portfolio 覆盖、正向证据可见性” 之间做调度。

## 12. 两个具体决策例子

### 12.1 早期 post-feasible recover：`g002-e0022-d00`

该决策来自：

- request trace：`traces/llm_request_trace.jsonl`
- response trace：`traces/llm_response_trace.jsonl`
- operator trace：`traces/operator_trace.jsonl`

当时状态：

| 字段 | 值 |
| --- | --- |
| generation | 2 |
| evaluation index | 22 |
| phase | `post_feasible_recover` |
| feasible rate | 0.05 |
| first feasible eval | 14 |
| pareto size | 1 |
| current peak temperature | 332.7429353854893 |
| current gradient rms | 24.085823549755602 |
| dominant violation family | `thermal_limit` |
| recent frontier stagnation | 7 |
| sink budget utilization | 0.9999999999999997 |

policy reason codes：

```text
post_feasible_bounded_exploration_exposure
post_feasible_semantic_portfolio_debt
post_feasible_recover_preserve_bias
```

`decision_axes` 给出的重要信号：

- `preferred_effect = balanced`
- `stagnant_objectives = ["temperature_max", "gradient_rms"]`
- `regression_risk = medium`
- `next_task_preference = sink_alignment`
- `semantic_portfolio_mode = repay_debt`
- bounded exploration targets 包括 `sink_shift`、`sink_resize`、`component_block_translate_2_4`、`component_subspace_sbx`

LLM 返回：

```json
{
  "selected_operator_id": "sink_shift",
  "selected_semantic_task": "sink_alignment",
  "selected_intent": "sink_alignment_adjust",
  "rationale": "Recover phase favors trusted bounded sink alignment diversification."
}
```

解释：

此时刚进入可行域不久，feasible rate 很低，recover phase 要优先保护可行集。但两个目标都停滞，同时 sink 已经满预算，直接扩大 sink span 不一定有效。`sink_shift` 保持 span、调整窗口位置，是比 `sink_resize` 更温和的 sink 语义动作，符合 recover 阶段的 “bounded alignment diversification”。

### 12.2 最终 Pareto 点前的 preserve 决策：`g010-e0190-d171`

该决策对应最终 Pareto 点 `eval=190`，LLM 选择：

```json
{
  "selected_operator_id": "anchored_component_jitter",
  "selected_semantic_task": "local_polish",
  "selected_intent": "component_local_gradient_cleanup",
  "rationale": "Preserve-first gradient improvement with strongest positive retrieval evidence."
}
```

当时状态：

| 字段 | 值 |
| --- | --- |
| generation | 10 |
| evaluation index before decision | 190 |
| phase | `post_feasible_preserve` |
| evaluations used | 189 |
| evaluations remaining | 12 |
| feasible rate | 0.43333333333333335 |
| first feasible eval | 14 |
| prompt-time pareto size | 5 |
| prompt-time peak temperature | 326.8558007649195 |
| prompt-time gradient rms | 20.90077476335764 |
| dominant violation family | `layout_spacing` |
| preservation pressure | `high` |
| frontier pressure | `medium` |
| preferred effect | `gradient_improve` |
| stagnant objective | `gradient_rms` |
| improving objective | `temperature_max` |
| sink budget bucket | `full_sink` |

spatial context：

- hotspot 不在 sink window 内。
- hotspot offset 为 `-0.37654017859609323`。
- nearest neighbor gap min 为 `0.06641566887008984`。
- layout spacing 是主导约束族。

`decision_axes` 给出的核心选择压力：

- `gradient_improve_candidates = ["anchored_component_jitter", "component_swap_2"]`
- `regression_risk = high`
- `preserve_score = 3`
- `frontier_score = 2`
- `preferred_effect = gradient_improve`

retrieval panel 中，`anchored_component_jitter` 有 positive match：

- route family：`stable_local`
- feasible preservation count：4
- feasible regression count：0
- similarity score：4

解释：

这一步不是选择大幅扩展的 operator，而是在高 preservation pressure 下选择低幅本地扰动。`anchored_component_jitter` 同时满足三点：

- 是 `local_polish` 语义任务候选。
- 在 operator panel 中有 `expected_gradient_effect = improve`。
- 在相似 regime 下有最强正向保持证据。

最终该 evaluated offspring 成为 run 的唯一 Pareto 点：

```text
summary.temperature_max = 324.6697231912805
summary.temperature_gradient_rms = 18.60929017834291
```

## 13. 关于 adaptive sink gate 的澄清

run 名称包含 `adaptive_sink_gate`，代码中也确实存在 adaptive sink gate 机制。位置在 `optimizers/operator_pool/policy_kernel.py`：

```text
_post_feasible_sink_budget_shape_deprioritized()
```

严格触发条件是：

- phase in `{post_feasible_expand, post_feasible_preserve}`
- 当前没有 active sink-budget pressure
- `feasible_rate >= 0.50`
- `recent_frontier_stagnation_count >= 6`

触发后，`sink_budget_shape` 的 semantic target 会被降权：

- `target_low = 0.0`
- `target_high <= 0.05`

但在本次 S5 run 的 request trace 中，严格条件触发次数为 0。主要原因是 prompt-time `run_feasible_rate` 没有达到 `0.50`。例如最终 Pareto 前的 `g010-e0190-d171`，`run_feasible_rate = 0.43333333333333335`，不满足 gate threshold。

本次 run 中仍能看到 sink 任务的 portfolio saturation 标注：

| `sink_resize` semantic_task_status | count |
| --- | ---: |
| `balanced` | 159 |
| `under_target` | 18 |
| `saturated_no_frontier` | 7 |

因此，本次案例应表述为：

> 代码具备 adaptive sink gate 机制，但该 run 的严格 gate 条件没有在 request 面触发；实际可见的是 semantic portfolio saturation/avoid repeat 对 `sink_budget_shape` 的软标注。

不要把这次 run 解读成 “adaptive sink gate 大量触发并主导结果”。

## 14. 机制边界与论文表述建议

### 14.1 可以确认的事实

- LLM 只选择 operator，不直接输出 layout 或 design vector。
- `llm` 与 `union` 使用同一套 primitive operator support。
- 当前 policy snapshot 不硬缩候选池，主要提供软策略上下文。
- LLM 输出经过 JSON/schema/candidate 校验。
- 失败时有 `random_uniform` fallback，但 S5 案例中没有触发。
- 是否进入 expensive evaluation 由本地 proposal/repair/filter 决定。
- 最终性能证据来自 evaluated history/Pareto，而不是 LLM rationale 本身。

### 14.2 不应夸大的点

- 不应说 LLM “生成了最优布局”。
- 不应说 LLM “拥有更多算子”。
- 不应把 prompt 中的 soft policy 描述成硬约束过滤。
- 不应把未触发的 adaptive sink gate 当成本次结果主因。
- 不应把单个 Pareto 点说成整体 Pareto front 多样性改善。

### 14.3 推荐表述

可以这样描述当前 LLM 方法：

> `nsga2_llm` uses the same primitive operator substrate as `nsga2_union`. The LLM is a representation-layer scheduling controller: for each NSGA-II offspring event, it receives a compact structured state containing phase, archive, spatial, retrieval, operator-evidence, semantic-task, and generation-local panels, then returns a validated operator id. The selected local operator produces the numeric candidate, which is then processed by the same repair, legality, cheap-constraint, PDE, and evaluation pipeline as the union baseline.

中文论文/报告可以表述为：

> LLM 路线不是黑盒生成设计，而是在共享算子支撑集上的上下文感知调度器。它利用结构化 prompt 中的阶段、目标压力、空间热点、历史证据和 semantic portfolio 状态，在每次 proposal 前选择一个本地算子；候选生成、修复、约束检查和 PDE 评价仍由确定性的优化平台执行。

