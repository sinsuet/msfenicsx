# 四组满 10 轮 LLM 优化对照实验

## 1. 实验目标

这次实验不再采用默认的 `max_invalid_proposals=2`，而是把它提高到 `10`，目的是：

- 强制每组都完整保留 10 轮窗口
- 对比 4 组独立真实 LLM 优化在同一案例上的温度改善轨迹
- 对比每组使用的优化策略是否一致
- 判断关键策略转折是否稳定复现

---

## 2. 统一实验设置

- state：`states/baseline_multicomponent.yaml`
- 约束：`chip_max_temperature <= 85 degC`
- 模型：DashScope `qwen3.5-plus`
- `--real-llm`
- `--max-iters 10`
- `--max-invalid-proposals 10`
- `--continue-when-feasible`

实验目录：

- `demo_runs/consistency_4x10_fullwindow_20260326/`

---

## 3. 最重要结论

这次 4 组满 10 轮实验的核心结论是：

> **前期策略高度一致，但“是否能在 10 轮内识别到底板导热率这个关键杠杆”并不一致。**

更直白地说：

- 4 组前半段都先调 `spreader conductivity`
- 后面都会碰到边界、几何尝试和非法 proposal
- 只有 `group_03` 在 10 轮窗口内真正走出了 `base_material.conductivity` 这个关键转折并兑现成大幅降温
- `group_02` 直到 `run_0010` 才第一次提出 `base_k`，但它的效果还没来得及在 10 轮窗口内体现
- `group_01` 和 `group_04` 在 10 轮内都没有走到 `base_k`

因此：

- **局部前期策略一致性：强**
- **关键突破策略一致性：弱**
- **10 轮内实际温度改善一致性：明显不一致**

---

## 4. 四组结果总表

| 组别 | run 数 | valid | invalid | 初始芯片峰值 | 第 10 轮芯片峰值 | 10 轮总改善量 |
| --- | --- | --- | --- | --- | --- | --- |
| `group_01` | `10` | `6` | `4` | `89.301304` | `89.256247` | `-0.045056` |
| `group_02` | `10` | `7` | `3` | `89.301304` | `89.256238` | `-0.045066` |
| `group_03` | `10` | `7` | `3` | `89.301304` | `58.612856` | `-30.688447` |
| `group_04` | `10` | `7` | `3` | `89.301304` | `89.256238` | `-0.045066` |

### 4.1 统计量

- 第 10 轮芯片峰值均值：`81.59539477717534`
- 第 10 轮芯片峰值标准差：`13.268974704789697`
- 10 轮总改善量均值：`-7.705908959040965`
- 10 轮总改善量标准差：`13.268974704789697`

这个标准差已经很大，说明：

- 4 组的最终表现 **不一致**
- 差异主要来自 `group_03` 是否在窗口内成功触发关键策略切换

---

## 5. 每组的策略序列

为了便于比较，把每一轮 proposal 的主要修改变量压缩成一行：

- `group_01`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> width -> spreader_k -> width -> width`
- `group_02`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> width+height+spreader_k -> spreader_k -> base_k`
- `group_03`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> width -> base_k -> spreader_k -> width -> spreader_k`
- `group_04`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> spreader_k -> width -> height`

从这些序列可以看到：

- 第 1 到第 4 轮，4 组几乎完全一致
- 后面开始围绕 `width`、`height` 和 `spreader_k` 在局部空间内打转
- 只有 `group_03` 在第 7 轮把 `base_k` 提上来
- `group_02` 虽然第 10 轮也提出了 `base_k`，但效果还未兑现

---

## 6. 温度改善对比

### 6.1 `group_01`

- 最佳已实现芯片峰值：`89.25623754213548`
- 出现在：`run_0006`
- 之后没有进一步实质改善

### 6.2 `group_02`

- 最佳已实现芯片峰值：`89.25623754213548`
- 出现在：`run_0006`
- 到 `run_0010` 才首次提出 `base_k`
- 因为 `run_0011` 不存在，所以该提案的效果还没兑现

### 6.3 `group_03`

- 最佳已实现芯片峰值：`58.612856424134335`
- 出现在：`run_0008`
- 这是唯一一组在 10 轮窗口内真正实现大幅降温的实验

### 6.4 `group_04`

- 最佳已实现芯片峰值：`89.25623754213548`
- 出现在：`run_0007`
- 后续主要在 `width / height / spreader_k` 周围打转

---

## 7. 关键策略转折分析

### 7.1 共同点

所有组一开始都把：

- `materials.spreader_material.conductivity`

当作第一优先级杠杆。

这说明：

- 对这个 baseline，LLM 的“第一反应”高度一致

### 7.2 差异点

真正决定结果分化的，不是前几轮，而是：

- 有没有在 10 轮窗口内切换到 `materials.base_material.conductivity`

具体表现：

- `group_03`
  - 在 `run_0007` 提出 `base_k`
  - `run_0008` 立刻把芯片峰值拉到 `58.61 degC`
- `group_02`
  - 到 `run_0010` 才提出 `base_k`
  - 但 10 轮窗口结束，效果尚未体现
- `group_01`
  - 没有提出 `base_k`
- `group_04`
  - 没有提出 `base_k`

所以真正的分化点是：

> LLM 是否能在足够早的轮次，把注意力从热扩展块局部杠杆切换到底板散热路径。

---

## 8. 非法 proposal 的作用

虽然这次提高了 `max_invalid_proposals`，保证了 10 轮窗口完整保留，但非法 proposal 仍然很多。

各组 invalid 数如下：

- `group_01`：`4`
- `group_02`：`3`
- `group_03`：`3`
- `group_04`：`3`

这意味着：

- 10 轮里并不是每一轮都在推进合法状态
- 一部分轮次只是保留了“尝试但失败”的提案记录
- 这也是为什么有些组虽然跑满 10 轮，但温度曲线在后半段几乎不再变化

---

## 9. 为什么 `group_02` 和 `group_03` 看起来有点像，但结果差很多

这是这次实验最值得强调的点。

### `group_03`

- 在 `run_0007` 就提出 `base_k`
- 该 proposal 被应用后
- `run_0008` 立即看到大幅降温

### `group_02`

- 在 `run_0010` 才提出 `base_k`
- 由于 proposal 的效果总是滞后一轮体现
- 它需要 `run_0011` 才能看到实际降温
- 但实验窗口只到 `run_0010`

所以：

> `group_02` 可能已经“想到正确方向”，但在 10 轮窗口内来不及兑现；而 `group_03` 则在窗口内既想到、又兑现了。

---

## 10. 当前问题的直接答案

如果问题是：

> 同一个例子、同样条件和约束，独立跑 4 组各 10 轮真实 LLM 优化后，每组温度提升和策略是否一致？

那么现在的答案是：

> **不完全一致。**

更准确地说：

- 前 4 到 5 轮的局部策略非常一致
- 但 10 轮内是否出现关键突破并不一致
- 4 组里只有 1 组在窗口内实现了显著降温
- 另外 1 组在第 10 轮才提出关键突破方向，但尚未兑现
- 剩下 2 组始终停留在局部优化平台

---

## 11. 当前最合理的解释

这组结果说明，当前系统在这个案例上的真实行为更像是：

> LLM 对“局部最直观杠杆”的判断相当稳定，但对“更高层瓶颈识别”的触发时机还不稳定。

因此：

- 你可以说系统具有 **较强的局部策略一致性**
- 但不能说它已经具有 **稳定的全局最优策略一致性**

---

## 12. 实验结果位置

- 总目录：
  - `demo_runs/consistency_4x10_fullwindow_20260326/`
- 每组 summary：
  - `group_01/demo_summary.md`
  - `group_02/demo_summary.md`
  - `group_03/demo_summary.md`
  - `group_04/demo_summary.md`
- 每组 figures：
  - `group_01/figures/`
  - `group_02/figures/`
  - `group_03/figures/`
  - `group_04/figures/`

---

## 13. 一句话结论

这次满 10 轮的 4 组对照实验表明：

> LLM 在同一热案例上的前期局部优化策略相当稳定，但关键突破策略在 10 轮窗口内并不能稳定复现，因此最终温度改善并不一致。
