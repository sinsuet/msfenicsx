# S5 LLM 算子选择链路审查与泛化优化方案

日期：2026-04-30

审查对象：

- 主案例：`scenario_runs/s5_aggressive15/0429_2007__raw_union_llm`
- 代码链路：`raw` / `union` / `llm` 三条 paper-facing NSGA-II optimizer ladder
- 关注问题：为什么 `llm` 算子选择效果弱，甚至不如随机均匀选算子的 `union`，以及如何设计不依赖场景特调模板的泛化 LLM 优化策略。

## 结论先行

本次失败不是“模型不聪明”这个单点问题，而是控制架构把 LLM 放在了错误的位置：当前 LLM 是直接动作选择器，且几乎没有硬 exposure 控制、在线 credit assignment、置信度校准、机会成本惩罚或 bandit 式探索机制。结果是 prompt 中的软偏好会直接变成算子暴露偏置；一旦早期 evidence 偏向某两个 operator，LLM 会自我强化，造成 operator portfolio collapse。

`0429_2007__raw_union_llm` 的证据非常明确：`union` 在同一 primitive operator substrate 上用随机均匀控制器保持了广覆盖，最终显著优于 `raw` 和 `llm`；`llm` 从第 6 代开始几乎只使用 `component_subspace_sbx` 与 `sink_shift`，最终没有把早期局部改善转化成 Pareto/frontier 质量。

建议的方向不是继续写 S5 特调 prompt，而是把 LLM 降级为“语义 prior / 反思解释 / 候选 route 生成器”，最终动作交给带硬预算的 contextual AOS / multi-armed bandit controller。LLM 给先验，AOS 负责在线采样、信用更新和探索-利用平衡。

## 主发现

### Critical 1：LLM 作为直接 selector，导致 operator portfolio collapse

证据：

- `union` operator trace 分布非常均衡：9 个算子均被使用，计数为 `24/23/22/22/20/18/18/17/16`。
- `llm` 选择高度坍缩：`component_subspace_sbx=85`，`sink_shift=69`，其余算子合计仅 40 次；实际 applied trace 中 `component_subspace_sbx=71`，`sink_shift=69`。
- 第 6 到第 10 代，`llm` 每代实际几乎固定为 `component_subspace_sbx=10` 与 `sink_shift=10`；同期 `union` 每代仍覆盖多种局部、全局、sink 和 structured operators。

相关代码：

- `optimizers/operator_pool/llm_controller.py:247-248`：LLM 使用 `build_policy_snapshot()` 给出的 `allowed_operator_ids` 作为候选池。
- `optimizers/operator_pool/policy_kernel.py:655-658`：当前 `allowed_operator_ids=candidate_ids` 且 `suppressed_operator_ids=()`，实际没有硬过滤。
- `optimizers/operator_pool/random_controller.py:13-24`：`union` 的随机控制器简单均匀采样，因此天然保持 exposure diversity。

根因判断：

LLM 当前没有被一个概率控制器包住。它每次被要求输出单个 `selected_operator_id`，所以 prompt 中任何“可信 evidence”“exact match”“bounded structured/sink exploration”都会直接转成重复动作，而不是转成可校准的概率先验。

### Critical 2：policy / guardrail 大多是软提示，不是搜索控制

证据：

- `policy_kernel` 虽然计算了 phase、risk、route family、exposure 等 annotation，但返回候选仍是全量 pool。
- dominance guardrail 会记录 `discouraged_operator_ids`，但没有改变可采样集合，也没有控制 rolling-window cap。

相关代码：

- `optimizers/operator_pool/llm_controller.py:249-264`：计算 recent / generation-local dominance guardrails。
- `optimizers/operator_pool/llm_controller.py:2498-2538`：guardrail 合并后主要落到 `discouraged_operator_ids` / `soft_advice_operator_ids`。
- `optimizers/operator_pool/llm_controller.py:764-772`：system prompt 明确声明“Policy is soft unless candidates change”，并且加入了会强化 exact-positive 和 structured/sink repeat 的语言。

根因判断：

搜索过程中的“不能再让某类算子主导”是控制约束，不应该只是 prompt advice。现在 guardrail 的语义像仪表盘警告灯，而不是刹车或限速器。

### Critical 3：credit assignment 太粗，早期正反馈会自我强化

证据：

`g006-e0102-d80` 是典型样本。该决策处于 `post_feasible_expand`，`decision_axes` 同时显示：

- `exact_positive_match_mode=prefer_exact_match`
- `exact_positive_match_operator_ids=["component_subspace_sbx"]`
- `regression_risk=high`
- `stagnant_objectives=["temperature_max","gradient_rms"]`
- `gradient_improve_candidates=["anchored_component_jitter","component_swap_2"]`
- `peak_improve_candidates=["component_jitter_1","component_relocate_1","sink_shift","component_block_translate_2_4"]`

LLM 最终仍选 `component_subspace_sbx`，rationale 是 exact-match structured subspace diversify。这里的错误不是它没有读上下文，而是系统没有让“高 regression risk、近期 exposure、替代算子机会成本、样本置信度”进入最终采样机制。

相关代码：

- `optimizers/operator_pool/state_builder.py:1083-1188`：构建了 `operator_summary`、`generation_local_memory`、`run_panel`、`operator_panel`、`semantic_task_panel` 等上下文。
- `llm/openai_compatible/schemas.py:9-32`：结构化输出只强制 `selected_operator_id`。
- `llm/openai_compatible/client.py:127-160`：解析时只校验 operator id 是否在候选集合中；没有 top-k、概率、置信区间或可用于 bandit 更新的预测字段。

根因判断：

上下文很丰富，但反馈闭环不够统计化。当前机制更像“让 LLM 读一份复杂报告然后拍板”，不是“把报告转成受约束的在线决策问题”。

### High 1：prompt 的默认偏置与 S5 失败模式同向

关键 prompt 片段在 `optimizers/operator_pool/llm_controller.py:764-772`：

- 强调 exact positive retrieval matches strongest。
- 要求 small-Pareto stagnation 时 repeat bounded structured/sink exploration before local cleanup。

这两个偏置与 `0429_2007` 的坍缩结果完全同向：后半程 `component_subspace_sbx` 与 `sink_shift` 垄断，局部 cleanup、relocate、swap、native baseline、sink resize 基本被排挤。

根因判断：

这种 prompt 对某个场景可能偶尔有效，但不是泛化优化策略。它把“阶段性经验”写成了全局优先级，且没有用在线 empirical reward 来纠偏。

### High 2：LLM 选择 schema 无法表达不确定性，系统也无法做稳健采样

当前 schema 只要求单个 `selected_operator_id`，可选字段只有 `selected_intent`、`selected_semantic_task`、`phase`、`rationale`。这意味着：

- LLM 无法表达“top-3 都可行，但 A 风险高、B 置信低、C 适合探索”。
- 控制器无法把 LLM 输出转成 prior distribution。
- 无法在 prompt 侧要求 calibrated expected value，例如 `P(feasible)`、`E[delta HV]`、`duplicate risk`、`repair collapse risk`。

根因判断：

把 LLM 输出设计成 single argmax 会放大语言模型过度自信的问题。泛化控制器需要的是排序和概率先验，不是一次性拍板。

### Medium：LLM JSONL trace 的 accepted 状态存在落盘时序问题

证据：

- `llm_response_trace.jsonl` 中 `accepted_for_evaluation=False` 出现在全部 194 条 response。
- 但 `analytics/decision_outcomes.csv` 显示 `applied=True` 为 180 条，`applied=False` 为 14 条，且未 applied 全部是 `component_subspace_sbx`。

相关代码：

- `optimizers/operator_pool/llm_controller.py:663-708`：request/response JSONL 在 LLM 返回时立即 append。
- `optimizers/adapters/genetic_family.py:949-1020`：后续 `_sync_llm_decision_statuses()` 更新的是内存中的 request/response row，但已经 append 的 JSONL 不会被重写。

影响：

这不是性能失败的主因，但会污染后续 trace replay / 诊断。如果分析脚本直接读 `llm_response_trace.jsonl` 的 accepted 字段，会得出错误结论。应以 `decision_outcomes.csv` 或重写后的 final trace 为准。

## raw / union / llm 链路对比

### raw 链路

`raw` 走原生 NSGA-II：

- `optimizers/drivers/raw_driver.py:51-62`：构造 raw algorithm 后直接 `pymoo.optimize.minimize()`。
- `optimizers/raw_backbones/nsga2.py:17-24`：使用 `CleanBaselineSampling()`、SBX crossover 与 polynomial mutation。
- 没有 operator pool，也没有 controller；operator trace 是后处理生成的 native trace。

raw 的意义是 native backbone baseline：少了 union primitive operators 的结构化移动能力，也没有 controller 引入额外偏置。

### union 链路

`union` 先构造同一 raw NSGA-II，然后替换 mating：

- `optimizers/drivers/union_driver.py:75-90`：构造 `build_genetic_union_algorithm()` 后运行同样的 `minimize()`。
- `optimizers/adapters/genetic_family.py:1027-1074`：以 raw algorithm 为底座，替换 `algorithm.mating = GeneticFamilyUnionMating(...)`。
- `scenarios/optimization/s5_aggressive15_union.yaml:145-158`：controller 是 `random_uniform`，registry 是 `primitive_structured`，operator pool 为 9 个共享 primitive/structured 算子。

union 的优势不是“随机很聪明”，而是它在小预算下保持了 operator exposure diversity。对于 S5 这种 aggressive constrained layout，早期不知道哪个 operator 真有效，随机均匀反而避免了过早坍缩。

### llm 链路

`llm` 与 `union` 使用同一 union adapter、同一 legality policy、同一 operator pool：

- `scenarios/optimization/s5_aggressive15_llm.yaml:137-176`：`algorithm.mode=union`，`operator_control.controller=llm`，`registry_profile=primitive_structured`。
- `optimizers/adapters/genetic_family.py:519-542`：每个 mating event 构建 `ControllerState`，然后调用 controller 选一个 operator。
- `optimizers/operator_pool/state_builder.py:1083-1188`：把 run、parent、archive、spatial、retrieval、operator、semantic task、generation memory 投影成 prompt panels。
- `optimizers/operator_pool/llm_controller.py:238-270`：LLM controller 取 policy snapshot、构造 prompt、调用 OpenAI-compatible client。
- `optimizers/adapters/genetic_family.py:560-577`：根据 LLM 选中的 operator 调用 `get_operator_definition(...).propose()` 生成候选，然后走 repair、duplicate filtering、evaluation。

因此 `llm` 与 `union` 的公平差异主要是 controller，不是 operator substrate。`0429_2007` 中 `llm` 输给 `union`，主要就是 controller 让同一 substrate 的暴露分布劣化了。

## `0429_2007__raw_union_llm` 结果证据

限制说明：以下是 `s5_aggressive15`、benchmark seed 11、algorithm seed 7、20×10 budget 的单 run-root 证据。它足以定位这次链路失败的直接机制，但不能单独替代跨 seed / 跨场景统计结论。后续方案必须用 S5/S6/S7 与多 seed matrix 验证。

### 终局指标

来自 `comparisons/tables/summary_table.csv`：

| mode | PDE evals | skipped | feasible_rate | best T_max | best grad_rms | final HV |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| raw | 156 | 44 | 0.420 | 326.750 | 20.813 | 0.000 |
| union | 160 | 40 | 0.595 | 323.614 | 16.521 | 265.708 |
| llm | 162 | 38 | 0.550 | 327.651 | 20.786 | 0.000 |

同一 PDE cutoff=156 时：

| mode | best T_max | best grad_rms | feasible_rate |
| --- | ---: | ---: | ---: |
| raw | 326.750 | 20.813 | 0.420 |
| union | 323.614 | 16.521 | 0.587 |
| llm | 328.043 | 20.990 | 0.536 |

说明：`llm` 的 PDE 预算没有吃亏，feasible rate 也不比 raw 差；真正的问题是可行解质量和 frontier 改善不足。

### 逐代 best feasible 进展

| generation | raw best T / grad | union best T / grad | llm best T / grad |
| ---: | --- | --- | --- |
| 1 | 332.599 / 24.070 | 328.959 / 22.056 | 330.589 / 22.050 |
| 3 | 331.213 / 23.542 | 328.692 / 20.485 | 328.251 / 21.155 |
| 6 | 328.734 / 21.650 | 324.703 / 17.269 | 328.047 / 21.000 |
| 9 | 326.750 / 20.813 | 323.614 / 16.521 | 327.651 / 20.786 |

关键观察：

- `union` 在第 6 代出现大幅跃迁，并在第 9 代继续改善。
- `llm` 在第 3 代后基本进入弱改善，后半程没有形成有效 basin escape 或 Pareto 扩展。

### 算子暴露分布

`union` applied operator counts：

| operator | count |
| --- | ---: |
| sink_shift | 24 |
| anchored_component_jitter | 23 |
| component_relocate_1 | 22 |
| component_jitter_1 | 22 |
| vector_sbx_pm | 20 |
| component_block_translate_2_4 | 18 |
| component_swap_2 | 18 |
| component_subspace_sbx | 17 |
| sink_resize | 16 |

`llm` response selected counts：

| operator | count |
| --- | ---: |
| component_subspace_sbx | 85 |
| sink_shift | 69 |
| anchored_component_jitter | 23 |
| component_swap_2 | 7 |
| component_relocate_1 | 7 |
| component_jitter_1 | 2 |
| component_block_translate_2_4 | 1 |
| vector_sbx_pm | 0 |
| sink_resize | 0 |

`llm` applied operator counts：

| operator | count |
| --- | ---: |
| component_subspace_sbx | 71 |
| sink_shift | 69 |
| anchored_component_jitter | 23 |
| component_swap_2 | 7 |
| component_relocate_1 | 7 |
| component_jitter_1 | 2 |
| component_block_translate_2_4 | 1 |
| vector_sbx_pm | 0 |
| sink_resize | 0 |

从第 6 代到第 10 代，`llm` applied trace 每代几乎固定为：

- `component_subspace_sbx`: 10
- `sink_shift`: 10

这就是 `llm` 输给随机 `union` 的核心实证解释。

## 为什么整体效果不好

### 1. 当前 LLM 控制器优化的是“看起来合理的解释”，不是“受约束的期望改进”

Prompt panels 给了大量上下文，但最终 schema 只问一个 operator id。LLM 会自然偏向语义上最容易解释的动作，例如“structured subspace diversify”“sink alignment”，而不是计算：

- 这个 operator 最近窗口的边际收益是否还显著？
- 它的样本数是否足以支撑 trusted label？
- 重复使用的 opportunity cost 是多少？
- 同一 generation 内 exposure 是否已经过高？
- 这个动作是否会被 repair collapse 成重复 candidate？
- 当前最缺的是 feasibility、peak、gradient、HV 还是 population diversity？

### 2. prompt policy 与 controller policy 混在一起

控制规则应该分三层：

1. Hard legality / safety：不可选、必须选、cap、floor。
2. Statistical selection：依据 credit 和 uncertainty 采样。
3. LLM semantic guidance：解释状态、给 route prior、提出探索假设。

当前系统把 1 和 2 的很多职责塞进了 3。只要 LLM 忽略 soft advice，系统没有第二道控制。

### 3. 没有在线 AOS 的基本闭环

成熟 AOS 至少需要：

- action exposure 统计；
- reward / credit 定义；
- sliding-window 或 decay；
- exploration floor；
- dominance cap；
- delayed outcome update；
- 与随机 baseline 的持续对照。

当前 trace 有 operator history，但最终选择不是由 credit model 控制，而是由 LLM 一次性读取摘要后选择。

### 4. 小预算下过早相信 early positive evidence 风险很高

`0429_2007` 总预算是 20×10 量级，早期每个 operator 的有效样本数很少。这个阶段把某个 operator 标成 trusted / exact positive，很容易把噪声当规律。随机 `union` 的广覆盖反而更稳。

### 5. trace 可复盘性还不够强

`decision_outcomes.csv` 可以判断 applied 与否，但 request/response JSONL 的 accepted 字段在旧 run 中是 stale。后续如果要训练/replay controller，必须把 `decision_id -> proposal -> repaired -> accepted -> evaluated -> objectives -> HV contribution` 串成一个 authoritative event table。

## 文献调研给出的原则

以下不是逐条照搬，而是抽取对本项目最相关的设计原则。

### LLM-as-optimizer 文献：LLM 适合提案与反思，不适合无约束拍板

- OPRO（Large Language Models as Optimizers, arXiv 2309.03409）把 LLM 用作生成新候选的优化器，但核心闭环是“候选 + 分数”进入下一轮上下文，而不是只靠一次解释选动作。链接：https://arxiv.org/abs/2309.03409
- FunSearch（Nature 2024）把 LLM 生成程序与自动 evaluator、evolutionary selection 结合。关键是可验证评估与选择循环，而不是信任语言解释。链接：https://www.nature.com/articles/s41586-023-06924-6
- Eureka（arXiv 2310.12931）强调 LLM 生成 reward code，经环境反馈和 evolutionary improvement 修正；其价值在于跨任务反馈闭环，而不是任务特调模板。链接：https://arxiv.org/abs/2310.12931
- Voyager（arXiv 2305.16291）强调 skill library、environment feedback、self-verification。对我们对应的是：controller memory 应该存可复用、可验证的 operator outcome，而不是只存自然语言 rationale。链接：https://arxiv.org/abs/2305.16291

### LLM + evolutionary / hyper-heuristic 文献：LLM 通常被包在 evolutionary evaluator 里

- ReEvo（NeurIPS 2024）把 LLM 作为 language hyper-heuristic，并用 reflective evolution 提供 verbal gradient；LLM 负责产生/改写 heuristic，外层 evolution 负责选择。链接：https://arxiv.org/abs/2402.01145
- LLaMEA（arXiv 2405.20132 / IEEE TEVC 2025）让 LLM 自动生成和 refinement metaheuristics，但仍基于 performance metrics 和 runtime feedback 做选择；还强调未见维度上的泛化测试。链接：https://arxiv.org/abs/2405.20132
- AlphaEvolve（Google DeepMind 2025）同样是 LLM + automated evaluator + evolutionary framework，用 evaluator 验证和筛选候选。链接：https://arxiv.org/abs/2506.13131
- “Evolutionary Computation in the Era of Large Language Model: Survey and Roadmap” 总结了 LLM 与 EA 的协作空间，适合把 LLM 看成生成、解释、辅助建模组件，而不是替代全部 selection dynamics。链接：https://arxiv.org/abs/2401.10034

### AOS / bandit 文献：operator selection 是在线信用分配问题

- FRRMAB / MOEA/D-AOS（IEEE TEVC 2014）把 AOS 定义为根据近期 operator performance 在线调整应用率，并使用 sliding window 与 bandit 机制跟踪动态。链接：https://repository.essex.ac.uk/11564/
- 近年的 DDQN-AOS（Neurocomputing 2024）继续把 adaptive operator selection 表述为基于状态和 reward 的在线选择问题，并强调多目标优化中的 reward/state 设计。链接：https://www.sciencedirect.com/science/article/abs/pii/S0925231224002625

对本项目的直接启发：

- LLM 的输出应是 prior / feature / hypothesis；
- operator 应由 AOS/bandit 在硬约束下采样；
- credit 必须来自真实 evaluation outcome；
- replay 和 ablation 必须以随机 `union` 为基本 baseline。

## 泛化 LLM 优化策略

### 目标架构：LLM-advised Contextual AOS

将当前：

`state -> LLM -> selected_operator_id -> proposal -> repair -> evaluation`

改为：

`state -> hard policy kernel -> outcome feature builder -> LLM prior advisor -> contextual AOS sampler -> selected_operator_id -> proposal -> repair -> evaluation -> credit update`

职责拆分：

- Hard policy kernel：只处理确定性约束，例如 legality、operator pool、rolling cap、generation cap、minimum exploration floor、known repair-collapse suppression。
- LLM prior advisor：读取压缩 prompt，输出 semantic route priors、top-k operator priors、risk estimates、uncertainty、rationale。
- AOS sampler：把 empirical credit、uncertainty、LLM prior、exposure budget 合成概率分布，再采样 operator。
- Credit updater：在 expensive evaluation 或 cheap rejection 后更新 operator / route / phase 的 credit。

### hard policy：先防坍缩

建议引入 scenario-agnostic exposure rules：

- Per-generation cap：任一 operator 不超过 `ceil(0.35 * generation_target_offsprings)`，除非只剩少数合法算子。
- Rolling-window cap：最近 `W=16` 个 applied decisions 中，任一 operator share 超过 `0.40` 后降权或暂时 suppress。
- Route-family cap：structured、sink、local、native 等 route family 同样有 cap，避免同族不同 operator 轮流垄断。
- Exploration floor：每个 still-applicable operator 在 rolling horizon 内有最小曝光机会，例如 `epsilon_floor=0.03-0.08`。
- Duplicate / repair collapse gate：近期 repair-collapsed duplicate rate 高的 operator 进入 cooldown。

这些规则不含 S5 名称，不含具体 component id，不是模板特调。

### reward / credit 设计

每个 operator decision 应产生多通道 reward，而不是单一成功/失败：

- Cheap pass reward：通过 cheap constraints 得小正反馈，cheap skip 得负反馈。
- Feasibility reward：从 infeasible 到 feasible、violation 降低、保持 feasible 分开计分。
- Objective reward：`delta temperature_max`、`delta gradient_rms` 按当前 archive scale 归一化。
- Pareto reward：frontier add、non-dominated rank 改善、hypervolume contribution。
- Diversity reward：population/archive decision-space crowding 或 novelty 改善。
- Cost penalty：PDE cost、LLM latency、duplicate、repair collapse、batch truncation。
- Regression penalty：feasible -> infeasible、objective 显著恶化、HV 无贡献且高 exposure。

建议 credit 结构：

```text
credit(op, phase, route) =
  w_feas * feasible_reward
  + w_obj * normalized_objective_delta
  + w_hv * hv_gain
  + w_div * novelty_gain
  - w_dup * duplicate_penalty
  - w_reg * regression_penalty
```

权重可按 phase 变化，但 phase 规则必须是通用的，例如 pre-feasible 更重 feasibility，post-feasible 更重 HV/objective/diversity。

### sampler：不要 argmax，要受约束采样

推荐两种可实现路线：

1. Thompson Sampling / Bayesian bandit：
   - 每个 `(phase, route_family, operator)` 维护 reward posterior；
   - LLM prior 作为先验均值的小权重项；
   - empirical evidence 随样本数增长逐步压过 LLM prior。

2. EXP3 / UCB hybrid：
   - 非平稳、小样本、噪声大时更稳；
   - 分数由 `empirical_credit + uncertainty_bonus + llm_prior - exposure_penalty` 组成；
   - softmax 后套 floor/cap，再采样。

示意：

```text
score_i =
  empirical_mean_i
  + beta * uncertainty_bonus_i
  + gamma * llm_prior_i
  - lambda * exposure_penalty_i
  - mu * duplicate_risk_i

p_i = constrained_softmax(score_i, floor, cap, route_cap)
selected_operator = sample(p_i)
```

关键点：LLM 只能影响 `llm_prior_i`，不能绕过 floor/cap 和 empirical credit。

### Prompt 与 schema 改造

把当前 single-action schema 改成 advisory schema：

```json
{
  "phase_assessment": "post_feasible_expand",
  "semantic_route_priors": [
    {"route_family": "stable_local", "prior": 0.35, "risk": 0.25},
    {"route_family": "sink", "prior": 0.25, "risk": 0.40}
  ],
  "operator_priors": [
    {
      "operator_id": "anchored_component_jitter",
      "prior": 0.28,
      "expected_effect": {"peak": "neutral", "gradient": "improve", "feasibility": "preserve"},
      "risk": 0.30,
      "confidence": 0.45,
      "reason": "..."
    }
  ],
  "avoid_reasons": [
    {"operator_id": "component_subspace_sbx", "reason": "recent exposure saturated"}
  ]
}
```

Prompt 原则：

- 删除“exact positive strongest”和“repeat structured/sink before cleanup”这类硬编码偏置。
- 告诉 LLM：它提供 prior，不做最终 selection。
- 明确要求校准：低样本必须低 confidence；recent exposure saturation 必须体现在 risk 或 avoid reason 中。
- 输入只保留泛化特征：phase、normalized objectives、constraint family、repair collapse rate、recent exposure、credit confidence、operator behavior class。

### Memory 设计

把 memory 从“近期 rationale”升级为 outcome table：

- key：`operator_id, route_family, phase, constraint_regime, objective_pressure`
- values：`n_trials, n_applied, cheap_skip_rate, feasible_gain_rate, mean_hv_gain, mean_obj_delta, duplicate_rate, repair_collapse_rate, confidence`
- retrieval：只按泛化 regime 检索，不按 scenario id 或 seed。

LLM 可以读取 memory 摘要，但 memory 的数值必须直接进入 sampler。

### Trace / replay 设计

建立 authoritative decision event table：

```text
decision_id
generation
operator_id
route_family
llm_priors
sampler_probabilities
selected_probability
proposal_vector_digest
repaired_vector_digest
cheap_status
accepted_for_evaluation
evaluation_index
feasible
objective_values
constraint_values
hv_delta
credit
```

这张表要从源头落盘，避免 request/response JSONL 后补状态不一致。

### 验证计划

先离线，再 live：

1. Offline replay：
   - 用 `0429_2007` 与 `0430_1140` 等现有 traces 重建 decision event table。
   - 对比 old LLM direct selector、random uniform、hard-cap random、AOS without LLM、LLM-advised AOS。

2. Smoke live：
   - S5/S6/S7 各 20×10，优先从 S5 调试模板开始。
   - 指标必须用 common PDE cutoff。
   - 先要求不劣于 `union` 的 feasible rate 和 operator entropy。

3. Main validation：
   - S5/S6/S7，至少 3 个 optimizer seeds 或 matrix block。
   - 报告：best T、best gradient、HV、feasible rate、operator entropy、route entropy、duplicate/repair collapse rate、LLM cost。

4. Ablation：
   - AOS only
   - LLM prior only without hard cap
   - hard cap + random
   - hard cap + AOS
   - hard cap + LLM-advised AOS

成功标准不应是某个 S5 run 赢，而是：

- 多场景 common cutoff 下不系统性输给 `union`；
- operator entropy 不坍缩；
- LLM prior 在若干 regime 下提供正增益；
- trace 可以解释每次 credit update。

## 建议的实施顺序

1. 修 trace authority：让 `accepted_for_evaluation`、evaluation outcome、credit 能在同一决策表中可靠落盘。
2. 实现 hard exposure governor：先不接 LLM，验证 cap/floor 不伤害 `union`。
3. 实现 AOS baseline：用 empirical credit 选择 operator，对比 `random_uniform`。
4. 改 LLM schema 为 advisory priors：不再直接返回 final operator。
5. 接入 LLM-advised AOS：LLM prior 只作为 sampler score 的一项。
6. 做 replay + smoke + matrix ablation。

## 最终判断

`0429_2007` 不是偶然“LLM 这次选错几个算子”，而是一个典型控制架构问题：同一 operator substrate 下，随机 `union` 因为保留广覆盖而表现更好；LLM direct selector 因为没有硬 budget 和在线 credit，反而把 prompt 偏置放大成后半程 portfolio collapse。

下一步应停止在 S5 prompt 上继续叠加局部规则，转向泛化的 LLM-advised AOS 架构。这样既保留 LLM 对 phase、regime、semantic route 的解释能力，又让真正的 operator selection 回到可验证、可回放、可统计控制的优化框架中。
