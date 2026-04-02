# 报告三：当前 LLM-union 优化架构方法与细节

Date: 2026-04-01

## 1. 报告目的

本报告详细说明当前主线 `LLM-union` 方法到底做了什么、没有做什么，以及它是如何被实现为一个可追踪、可回退、可复盘的 proposal-layer controller。

第二篇报告已经说明了 `raw / union / llm-union` 的总体比较框架；本报告只聚焦当前主线的 `LLM-union`：

- 算法骨架仍是 `NSGA-II`
- action registry 固定
- repair、evaluation 和 survival 保持不变
- `LLM` 只负责在 proposal-time 选择一个 operator

## 2. 方法定位

当前 `LLM-union` 不是“让大模型直接设计布局”，而是：

- 在固定 action space 上工作的 `LLM`-guided operator hyper-heuristic
- 一个挂在 `NSGA-II` offspring proposal 层的 controller
- 一个严格受 schema、候选集与 fallback 约束的动作选择器

因此，当前方法的核心贡献表达应当是：

- 在 expensive constrained multicase thermal optimization 上，
- 用一个 domain-grounded 的 `LLM` controller，
- 在固定 native-plus-custom action registry 上选择 proposal 动作，
- 并保持 repair、evaluation 和 survival 语义完全匹配。

## 3. `LLM-union` 不做什么

为了避免误解，先明确当前方法没有做的事情：

1. 不直接输出 8 维设计向量；
2. 不修改物理求解器；
3. 不修改 multicase evaluation spec；
4. 不修改 `NSGA-II` 的 survival；
5. 不给 `LLM` 额外动作特权；
6. 不绕过几何 repair；
7. 不使用隐藏的 provider-side conversation state 作为方法定义的一部分。

这几条限制非常重要，因为它们确保 `LLM` 的作用被严格限制在 controller 层。

## 4. 固定混合 action registry

当前 `LLM-union` 使用的动作集合固定为 9 个：

1. `native_sbx_pm`
2. `sbx_pm_global`
3. `local_refine`
4. `hot_pair_to_sink`
5. `hot_pair_separate`
6. `battery_to_warm_zone`
7. `radiator_align_hot_pair`
8. `radiator_expand`
9. `radiator_contract`

### 4.1 动作语义

这些动作可分为三类：

| 类别 | 动作 | 作用 |
| --- | --- | --- |
| 原生基线动作 | `native_sbx_pm` | 保留 `NSGA-II` 原生 `SBX + PM` proposal 语义 |
| 全局探索动作 | `sbx_pm_global` | 更激进地在全向量范围内做 global exploration |
| 领域化局部动作 | 其余 7 个 | 围绕热点位置、电池位置与 radiator 几何做定向调整 |

其中几个动作的工程直觉尤其明确：

- `hot_pair_to_sink`：
  - 把 `processor` 和 `rf_power_amp` 朝上边界 sink 方向推；
- `hot_pair_separate`：
  - 拉开两个高热器件；
- `battery_to_warm_zone`：
  - 把 battery 向更暖区域移动；
- `radiator_align_hot_pair`：
  - 把 radiator 中心对齐热点中心；
- `radiator_expand / contract`：
  - 直接调节 radiator span。

### 4.2 为什么要显式保留 `native_sbx_pm`

把原生动作显式写入 registry，而不是让 custom operators 完全替代 native variation，有两个目的：

1. 保留 `NSGA-II` 身份；
2. 让 `P1` 与 `L1` 的 controller 可以在“继续用原生 proposal”与“切换到领域化动作”之间做明确选择。

这使当前主线不是“抛弃原生算法”，而是“在原生 proposal 之上扩展 action vocabulary”。

## 5. 控制器插入点与执行链

当前 `LLM-union` 的实际执行链为：

```text
population
  -> parent selection
  -> build controller state
  -> candidate shaping / policy kernel
  -> llm chooses one operator
  -> operator emits one proposal vector
  -> shared repair
  -> hot/cold solves
  -> multicase evaluation
  -> NSGA-II survival
```

在 genetic-family 实现中，每次 event 都会：

1. 从 parent rows 中构造 `ParentBundle`；
2. 构造当前 decision 的 `ControllerState`；
3. 交给 controller 选择 `selected_operator_id`；
4. 调用对应 operator 生成 proposal；
5. 记录 `controller_trace` 与 `operator_trace`；
6. 再进入统一 repair 和评价流程。

因此，`LLM` 的输出只是一条“本次该用哪个 operator”的决策。

## 6. `ControllerState` 是如何构造的

当前 controller state 并不是原始日志堆叠，而是一个经过压缩和结构化的 domain-grounded state。

### 6.1 state 的核心组成

当前实现中，`build_controller_state` 会把以下信息放入 state metadata：

| 模块 | 作用 |
| --- | --- |
| `run_state` | 运行进度、预算位置、是否已出现第一可行解 |
| `parent_state` | 当前 parent 的向量与历史关联信息 |
| `archive_state` | 现有可行前沿与 archive 摘要 |
| `domain_regime` | 当前处于哪种热-约束 regime |
| `progress_state` | 最近是否停滞、是否进入 near-feasible 等 |
| `recent_decisions` | 近期 controller 选择历史 |
| `operator_summary` | 各 operator 的 outcome 统计摘要 |
| `recent_operator_counts` | 近期 operator 频次信息 |

### 6.2 为什么不用原始全量历史

当前实现没有把所有历史记录原样塞给模型，原因很明确：

1. token 成本过高；
2. 不利于多 model 对照；
3. 难以复盘；
4. 容易把一次性的噪声改善误判为稳定证据。

因此，当前 controller 设计强调的是：

- compact state
- evidence summary
- phase-aware abstraction

而不是“无上限记忆”。

### 6.3 近期窗口

当前 live route 的 controller parameters 中显式声明：

- `memory.recent_window = 32`
- `memory.reflection_interval = 1`

在实现上，状态构造会利用最近窗口内的：

- controller decisions
- operator outcomes
- feasible entry / preservation / regression
- dominant violation relief

来构造紧凑摘要。

## 7. policy kernel：在 LLM 之前先做什么

当前实现不是把所有候选 operator 原样交给模型，而是先通过一个可解释的 policy kernel 做 phase-aware candidate shaping。

### 7.1 phase 检测

`policy_kernel` 当前会根据 `progress_state`、`domain_regime` 和历史进展把搜索状态划分为：

- `cold_start`
- `prefeasible_progress`
- `prefeasible_convert`
- `post_feasible_expand`
- `post_feasible_preserve`
- `post_feasible_recover`

这意味着当前 controller 不是“永远用同一套 prompt 规则”，而是一个带显式 search phase 语义的 controller。

### 7.2 evidence annotation

对每个 candidate operator，policy kernel 会构造注释，包括：

- `operator_family`
- `role`
- `exploration_class`
- `evidence_level`
- `entry_evidence_level`
- `feasible_entry_count`
- `feasible_preservation_count`
- `feasible_regression_count`
- `pareto_contribution_count`
- `dominant_violation_relief_count`
- `near_feasible_improvement_count`

换句话说，当前 controller 并不是“根据 operator 名字硬编码决策”，而是先看每个动作在当前 regime 下积累了多少证据。

### 7.3 cold-start 策略

在 `cold_start` 阶段，policy kernel 会优先保留稳定 family，避免一开始就把搜索带进 speculative custom action 的混乱区域。

核心思想是：

- 先用稳定动作做 bootstrap
- 再逐步允许更激进的 custom exploration

### 7.4 prefeasible 策略

在 `prefeasible` 阶段，policy kernel 更强调：

- 可信证据
- 稳定 role 多样性
- 对 dominant violation 的针对性 relief

尤其在 `prefeasible_convert` 模式下，系统会把重点从“继续乱试”切换为“尽快跨过第一可行门槛”。

### 7.5 post-feasible 策略

一旦已经进入可行域，策略会切换为：

- `expand`：
  - 增强前沿扩展；
- `preserve`：
  - 保持可行性同时稳步改进；
- `recover`：
  - 当最近 feasible regressions 增多时，收缩到更可信的 preserve family。

这使当前 `LLM-union` 不是单一目标 controller，而是一个会在“进可行域之前”和“进可行域之后”切换行为模式的 controller。

## 8. guardrail 机制

当前实现中，真正送给 `LLM` 的候选集还会进一步经过 guardrail 处理。

### 8.1 recent dominance guardrail

`llm_controller` 中实现了“近期 operator dominance”防护。

默认阈值是：

- 最近窗口至少 `6` 次有效选择
- 同一 operator 至少出现 `5` 次
- 占比至少 `0.75`

满足后，会把这个“近期过于支配的 operator”临时从候选集中移除。

这样做的目的不是禁止重复，而是防止模型因为最近短期反馈而塌缩到单一动作。

### 8.2 prefeasible zero-credit custom dominance

在第一可行解尚未出现之前，如果一个“没有任何 feasible credit 的 custom operator”在短窗口里形成支配，guardrail 会用更严格的预可行阈值提前介入。

这类阈值更偏向：

- 不让零证据 speculative custom action 在 pre-feasible 阶段形成 monopoly。

### 8.3 progress-reset 窗口

当近期长期无进展时，policy kernel 会激活 reset window，要求 controller 回到更可信的稳定角色组合，避免在 no-progress streak 中继续加大投机性。

这类 reset 的目标是：

- 不让模型在局部失败模式里越陷越深；
- 在恢复阶段强调 baseline / global explore / local cleanup 之间的稳定多样性。

## 9. prompt projection：真正给模型看的是什么

当前 `LLM-union` 并不会把整个 Python 对象或 trace 原样交给模型，而是先把状态投影为一个结构化 JSON payload。

### 9.1 prompt payload 的主字段

发给模型的 user payload 主要包含：

- `family`
- `backbone`
- `generation_index`
- `evaluation_index`
- `parent_count`
- `vector_size`
- `candidate_operator_ids`
- `metadata`

而 `metadata` 内部又包含：

- `search_phase`
- `run_state`
- `parent_state`
- `archive_state`
- `domain_regime`
- `progress_state`
- `recent_decisions`
- `recent_operator_counts`
- `operator_summary`
- `phase_policy`
- `decision_guardrail`

### 9.2 phase-scoped 投影

`prompt_projection` 不同 phase 下会裁剪不同信息。例如：

- 在 pre-feasible 阶段，会弱化 post-feasible 专属的前沿扩张统计；
- 在 post-feasible 阶段，则保留更多 archive 和 frontier 贡献信息。

这说明当前 prompt 不是只在“文案”层面做 phase-aware，而是在“给模型看什么数据”这一层也做了 phase-aware。

## 10. system prompt 的策略约束

当前实现中的 system prompt 不是通用聊天提示，而是高度约束的 controller instruction。

它至少明确要求模型：

1. 只能从给定 `candidate_operator_ids` 里选一个；
2. 不能输出 raw decision vector；
3. 不要盲目复制最近 dominant operator；
4. 在 pre-feasible 阶段优先稳定、可信、可复现的证据；
5. 在 phase policy 给出的 regime 下遵守相应行为偏置。

因此，`LLM` 不是自由 agent，而是一个高度受控的 action selector。

## 11. OpenAI-compatible transport 边界

当前 live 路径采用 OpenAI-compatible transport，而不是把 provider-specific 逻辑散落在 optimizer core 中。

### 11.1 当前 live spec 的关键参数

当前主线 live spec 中 controller parameters 关键项为：

- `provider = openai-compatible`
- `capability_profile = chat_compatible_json`
- `performance_profile = balanced`
- `model = GPT-5.4`
- `api_key_env_var = OPENAI_API_KEY`
- `base_url = https://llmapi.paratera.com/v1`
- `max_output_tokens = 256`
- `temperature = 1.0`
- `retry.max_attempts = 2`
- `retry.timeout_seconds = 45`
- `fallback_controller = random_uniform`

### 11.2 支持的 capability profiles

当前 transport 层显式区分：

- `responses_native`
- `chat_compatible_json`

当前 live route 使用的是 `chat_compatible_json`，即：

- 通过 OpenAI-compatible chat/completions 发送请求；
- 要求返回 JSON object；
- 再由 repository 端进行 schema 与语义校验。

## 12. structured output 与双层校验

当前实现对模型输出做了双层约束。

### 12.1 schema 层

结构化 schema 要求输出必须包含：

- `selected_operator_id`
- `phase`
- `rationale`

其中 `selected_operator_id` 必须枚举在当前候选集中。

### 12.2 repository 语义层

即使 provider 支持 JSON 格式，repository 仍会做语义校验：

1. 选中的 operator 是否在当前 registry 内；
2. 是否属于当前 candidate set；
3. 如模型输出不合规，是否能安全恢复；
4. 否则进入 retry 或 fallback。

此外，当前实现还支持一类温和恢复：

- 如果模型文本里只唯一提到了某个合法 operator ID，可以尝试 recover；
- 如果仍不满足约束，则视为无效响应。

## 13. retry 与 fallback

当前 `LLM-union` 的稳定性并不建立在“模型永远正确”这个假设上，而是建立在：

- retry
- semantic validation
- fallback controller

三者联合形成的 guardrail 上。

### 13.1 retry

当输出无效时，controller 会：

1. 记录当前 attempt；
2. 构造 retry system prompt；
3. 要求模型重新给出严格 JSON；
4. 最多重试到 `max_attempts`。

### 13.2 fallback

如果最终仍失败，controller 不会让优化 run 崩掉，而是回退到：

- `random_uniform`

这保证：

- provider 问题不会毁掉整个优化实验；
- `LLM` route 的失败也仍可被显式统计与分析。

### 13.3 runtime metrics

`llm_metrics.json` 会记录：

- `request_count`
- `response_count`
- `fallback_count`
- `retry_count`
- `invalid_response_count`
- `schema_invalid_count`
- `semantic_invalid_count`
- `elapsed_seconds_total`
- `elapsed_seconds_avg`
- `elapsed_seconds_max`

这些指标对后续稳定性诊断非常重要。

## 14. trace 设计

当前 `LLM-union` 最大的优势之一，是它不仅有结果，还有机制 trace。

### 14.1 `controller_trace.json`

这一层记录：

- 每次 decision 的 generation/evaluation index
- candidate operator 集合
- 最终选中的 operator
- provider/model/capability metadata
- guardrail 相关元数据
- proposal kind
- fallback 是否发生

### 14.2 `operator_trace.json`

这一层记录：

- parent vectors
- proposal vector
- repaired vector
- operator_id
- decision_index
- sibling/proposal metadata

这使“controller 选了什么”和“operator 具体怎么改了向量”可以分层分析。

### 14.3 `llm_request_trace.jsonl` 与 `llm_response_trace.jsonl`

这两条 trace 用来记录：

- 实际送给模型的 prompt payload
- 返回的原始 payload
- policy phase
- guardrail
- attempt / retry 信息

这使当前 `LLM-union` 成为一个可 replay、可诊断、可机制分析的 controller 系统，而不是黑盒。

## 15. 当前方法已经验证到什么程度

从“方法实现”角度说，当前 `LLM-union` 已经实现了：

1. 固定 action registry；
2. phase-aware state building；
3. policy kernel candidate shaping；
4. OpenAI-compatible structured transport；
5. schema + semantic validation；
6. retry + fallback；
7. controller/operator/request/response metrics tracing。

但从“论文证据”角度说，仍需保持诚实：

- 当前已经有多条正向 seed 证据；
- 但还不能把当前 controller 写成“稳定全面优于 uniform”；
- 更合理的表述是：
  - 当前已经出现强正向机制证据与强正向 run；
  - controller kernel 的跨 seed 稳定性仍在继续验证中。

## 16. 本报告的结论

当前 `LLM-union` 方法可以概括为：

1. 一个固定 mixed action registry 上的 `LLM`-guided operator hyper-heuristic；
2. 一个 proposal-time controller，而不是 design-vector generator；
3. 一个通过 `ControllerState + policy kernel + prompt projection` 实现的 phase-aware、evidence-aware 决策系统；
4. 一个通过 structured output、语义校验、retry、fallback 与 trace 形成的可控、可诊断实现。

因此，当前主线中真正值得汇报的方法点不是“我们用了大模型”，而是：

- 我们把 `LLM` 严格限定在一个公平、可追踪、可回退、可分析的 controller 角色里，
- 并让它在固定 action space 上与 uniform controller 做直接比较。

后续第四篇报告将基于这一方法实现，详细复盘一个代表性 run 的完整流程，并给出 `raw / union-uniform / llm-union` 的结果对照与当前最好绝对结果快照。
