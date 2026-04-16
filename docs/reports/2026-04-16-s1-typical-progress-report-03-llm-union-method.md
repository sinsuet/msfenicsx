# 报告三：`llm` 方法与一个真实优化决策例子

Date: 2026-04-16

## 1. 先把 LLM 的角色说准确

当前 `llm` 路线不是“让大模型直接输出最终布局”，而是：

> 在共享动作池上，让 LLM 选择“这一轮应该调用哪个 operator 来产生下一个候选”。

因此，它是一个 proposal-time controller，而不是一个直接生成 32 维设计向量的黑盒。

## 2. `union` 和 `llm` 共享同一套 operator registry

当前共享动作池包含 10 个 operator：

| operator | 角色 |
| --- | --- |
| `native_sbx_pm` | 原生 `NSGA-II` 基线 proposal |
| `global_explore` | 全局探索 |
| `local_refine` | 局部细化 |
| `move_hottest_cluster_toward_sink` | 热点簇向散热窗口靠近 |
| `spread_hottest_cluster` | 打散热点簇 |
| `smooth_high_gradient_band` | 平滑高梯度带 |
| `reduce_local_congestion` | 缓解局部拥挤 |
| `repair_sink_budget` | 修正散热窗口预算 |
| `slide_sink` | 平移散热窗口 |
| `rebalance_layout` | 全局重平衡 |

这里的关键点是：

> `union` 和 `llm` 用的是同一个动作词表，所以它们比较的是“动作选择能力”，而不是“动作特权”。

## 3. LLM 实际读入的不是原始日志，而是结构化状态

当前 controller 在每次决策前，会把运行状态压缩成结构化输入，核心包括：

- 当前 phase
- 最近是否停滞
- 哪个目标在改善，哪个目标在停滞
- 哪些 operator 在当前 phase 更可信
- guardrail 是否过滤了一部分动作
- 当前还允许 LLM 在哪些候选 operator 之间做选择

所以，LLM 不是在看一整堆原始历史文本，而是在消费一个已经结构化过的状态摘要。

## 4. 在 LLM 之前，policy kernel 先做了什么

当前实现里，LLM 不会直接面对所有 10 个动作，而是先经过一层 policy kernel 和 guardrail：

1. 根据当前运行状态判断 phase
2. 把不适合当前 phase 的动作过滤掉
3. 只把剩余候选动作交给 LLM 选择

这层设计很重要，因为它保证了：

- LLM 不是无限制地“自由发挥”
- controller 行为有明确工程边界
- 每一步决策都可以事后复盘

## 5. 一个真实的 LLM 决策例子

下面使用 `scenario_runs/s1_typical/0416_0110__llm` 中 `evaluation_index = 108` 的真实记录来说明一次完整决策。

这一步之所以值得讲，是因为它直接对应了本次汇报的一个核心证据：

> LLM 在第 108 次评估时，就已经达到并超过了 raw / union 最终 knee 区域的平衡质量。

### 5.1 决策时的候选集合

原始候选动作池是 10 个，但经过 phase guardrail 之后，只剩下 3 个候选：

```json
["native_sbx_pm", "global_explore", "local_refine"]
```

也就是说，这一步不是“LLM 随意从 10 个动作里乱选”，而是先被限制在当前更可信的 3 个动作上。

### 5.2 当时的 prompt 关键信号

当时的状态摘要里，最关键的几项信号是：

```json
{
  "policy_phase": "post_feasible_expand",
  "objective_balance_pressure": "medium",
  "stagnant_objectives": ["temperature_max", "gradient_rms"],
  "peak_improve_candidates": ["local_refine"],
  "preferred_effect": "balanced"
}
```

这说明当时 controller 看到的是：

- 已经进入可行域之后的扩展阶段
- 两个目标都出现了停滞
- 需要在保持可行性的前提下重新推动前沿
- 如果想显式改善峰值温度，`local_refine` 是唯一有明确信号的候选

### 5.3 LLM 给出的真实选择

该次响应返回：

```json
{
  "selected_operator_id": "local_refine",
  "phase": "post_feasible_expand",
  "rationale": "Both objectives are stagnant, and local_refine has trusted expand-fit with positive frontier evidence plus the only explicit peak-improve signal..."
}
```

该次决策的核心逻辑是：

> 在“双目标都停滞”的情况下，LLM 选择了当前唯一明确带有峰值温度改善信号、同时又不至于破坏可行性的 `local_refine`。

### 5.4 这一步带来了什么结果

在这一步之前，`evaluation_index = 97` 的代表状态大约是：

| eval | `T_max` | `grad_rms` |
| --- | ---: | ---: |
| 97 | `308.404` | `14.460` |

到 `evaluation_index = 108` 时，结果变成：

| eval | `T_max` | `grad_rms` |
| --- | ---: | ---: |
| 108 | `305.431` | `12.597` |

也就是说，这一步把两个目标都明显向下推进了，并且已经达到：

- 优于 raw 最终 knee 的平衡区间
- 优于 union 最终 knee 的平衡区间

## 6. 这个例子说明了什么

这个例子恰好把 LLM controller 的价值讲得很清楚：

### 6.1 它不是直接“生成布局”

真正发生的链条是：

```text
结构化状态 -> phase / guardrail -> 缩小后的候选动作集
-> LLM 选 operator -> operator 生成候选 -> repair -> PDE solve -> evaluation
```

### 6.2 它体现的是调度能力

这个例子里，LLM 的价值不在于创造了新动作，而在于：

- 理解当前是 `post_feasible_expand`
- 理解两个目标都停滞
- 理解哪个动作同时更可信且更有机会改善峰值温度

### 6.3 它可以被完整复盘

这一步之所以具有代表性，是因为整条链都有留痕：

- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `controller_trace.json`
- `operator_trace.json`

因此，这条方法线不是“感觉像更聪明”，而是有具体行为证据可查。

## 7. 本报告结论

关于 LLM 方法的结论可表述为：

> 当前 `llm` 路线是在共享动作空间上的受限 controller，它不直接输出最终布局，而是根据结构化状态选择下一步最合适的 operator，并把这一选择完整记录下来供复盘分析。
