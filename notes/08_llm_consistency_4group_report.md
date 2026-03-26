# 四组独立 LLM 优化一致性对照实验

## 1. 实验目的

验证在 **同一个二维稳态导热案例**、**同样的 baseline**、**同样的约束**、**同样的真实 LLM 配置** 下，独立重复运行 4 组优化时，LLM 的优化轨迹和最终效果是否一致。

这次实验关注的是：

- 每组是否会做出相同方向的修改
- 每组是否会在相同轮次出现策略切换
- 每组最终温度是否接近
- 每组是否都能稳定跑满 10 轮

---

## 2. 实验设置

统一使用：

- state：`states/baseline_multicomponent.yaml`
- 模型：DashScope `qwen3.5-plus`
- 真实 LLM：开启
- 最大轮次：`10`
- 保持可行后继续优化：开启 `--continue-when-feasible`
- 约束：`chip_max_temperature <= 85 degC`

执行命令等价于：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python examples/03_optimize_multicomponent_case.py \
  --state-path states/baseline_multicomponent.yaml \
  --runs-root demo_runs/consistency_4x10_20260326/group_01 \
  --real-llm \
  --max-iters 10 \
  --continue-when-feasible
```

只是把 `group_01` 改成 `group_02`、`group_03`、`group_04` 分别独立重跑。

结果目录：

- `demo_runs/consistency_4x10_20260326/`

---

## 3. 最重要的总体结论

这 4 组实验的结论可以概括成一句话：

> **局部轨迹高度一致，但都没有稳定走到官方 `official_10_iter` 中那种“第 9 轮识别到底板瓶颈并显著降温”的阶段。**

更具体地说：

- 4 组都从同一个 baseline 起步
- 前 4 到 5 轮几乎都优先提高 `spreader conductivity`
- 在热扩展块导热率接近或达到上界后，开始出现轻微分叉
- 分叉后的主要方向是尝试 `width`
- 随后都因连续非法 proposal 提前终止
- 4 组都没有触发像官方 `run_0009` 那样的 `base_material.conductivity` 策略切换

因此：

- **“前半段一致性”很强**
- **“后半段全局策略切换一致性”不强**
- **最终效果数值几乎一致，但都只停留在一个局部改进平台上**

---

## 4. 四组结果总表

| 组别 | 实际 run 数 | valid 数 | invalid 数 | 初始芯片峰值 | 最后芯片峰值 | 总改善量 |
| --- | --- | --- | --- | --- | --- | --- |
| `group_01` | `7` | `5` | `2` | `89.301304` | `89.256247` | `-0.045056` |
| `group_02` | `8` | `6` | `2` | `89.301304` | `89.256238` | `-0.045066` |
| `group_03` | `8` | `6` | `2` | `89.301304` | `89.256228` | `-0.045075` |
| `group_04` | `7` | `5` | `2` | `89.301304` | `89.256238` | `-0.045066` |

### 4.1 量化一致性指标

- 最终芯片峰值均值：`89.25623778165073`
- 最终芯片峰值标准差：`6.651055518696865e-06`
- 总改善量均值：`-0.0450659545655796`
- 总改善量标准差：`6.651055518696865e-06`
- 实际 run 数均值：`7.5`
- 实际 run 数标准差：`0.5`

这说明：

- 如果只看最终停下来的温度数值，4 组结果几乎完全一致
- 但如果看“是否能继续探索到更高层策略切换”，一致性并不好，因为都在较早阶段被非法 proposal 卡住了

---

## 5. 每组的修改轨迹

为了便于比较，把每组每一轮的主要修改变量压缩成一行：

- `group_01`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> width -> spreader_k`
- `group_02`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> width -> spreader_k`
- `group_03`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> spreader_k -> width+height`
- `group_04`
  - `spreader_k -> spreader_k -> spreader_k -> spreader_k -> width -> spreader_k -> width`

从这些序列可以看到：

- 前 4 轮几乎完全一致
- 到第 5 轮左右开始出现分叉
- 这些分叉都还局限在 `spreader conductivity` 和 `heat_spreader width/height`
- 没有一组切换到 `base_material.conductivity`

---

## 6. 为什么四组会“数值几乎一致，但没有明显突破”

这次实验揭示了一个非常关键的现象：

### 6.1 LLM 在这个 baseline 上的“默认直觉”高度一致

前几轮，4 组都认为最直接的手段是：

- 提高热扩展块导热率

这说明模型对这个案例的第一反应具有较强一致性。

### 6.2 这个杠杆本身就不是主瓶颈

虽然前几轮一直在改 `spreader conductivity`，但最终总改善量只有大约：

- `0.045 degC`

这和之前我们对官方 10 轮数据的分析一致：

- `spreader conductivity` 只能带来非常有限的改善
- 真正的关键杠杆其实是后面才识别出来的 `base_material.conductivity`

### 6.3 四组都在触碰边界后被连续非法 proposal 提前终止

这 4 组里常见的非法原因主要有两类：

- `spreader conductivity` 超上界，例如试图改到 `700`、`750`、`1000`
- `heat_spreader width` 继续增大后导致几何越界

因此它们没有继续活到更后面的策略切换阶段。

---

## 7. 四组最终停下时的状态

### `group_01`

- `base_k = 12.0`
- `spreader_k = 500.0`
- `width = 0.9`
- `height = 0.1`

### `group_02`

- `base_k = 12.0`
- `spreader_k = 500.0`
- `width = 0.84`
- `height = 0.1`

### `group_03`

- `base_k = 12.0`
- `spreader_k = 500.0`
- `width = 0.8`
- `height = 0.1`

### `group_04`

- `base_k = 12.0`
- `spreader_k = 500.0`
- `width = 0.84`
- `height = 0.1`

可以看到：

- 4 组都把 `spreader_k` 推到了上界 `500`
- 没有一组动到 `base_k`
- 最后差异主要只体现在 `width` 上是 `0.8 / 0.84 / 0.9`

---

## 8. 这次实验说明了什么

这次 4 组对照实验说明：

### 8.1 一致的部分

- 同一个 baseline 下，LLM 的前期优化方向相当稳定
- 都会先盯住热扩展块导热率
- 最终停下来的芯片峰值几乎完全一致

### 8.2 不一致的部分

- 中后期在几何变量上的尝试并不完全一致
- 非法 proposal 出现的具体轮次不完全一致
- 没有稳定复现官方 `run_0009` 那种“切到底板导热率”的关键策略转折

### 8.3 更深一层的结论

这意味着当前系统对这个案例的真实表现更像是：

> LLM 会稳定收敛到一个“热扩展块局部优化平台”，但不一定稳定跨越到“识别全局散热路径瓶颈”的更高层策略。

---

## 9. 和 `official_10_iter` 的关系

官方 10 轮数据中最关键的一步是：

- `run_0009`
  - `materials.base_material.conductivity: 12 -> 24`

然后下一轮热点从约：

- `89.2562`

直接降到：

- `58.6129`

而这次 4 组对照实验中：

- 没有任何一组复现这一步
- 所以没有任何一组出现大幅降温突破

这说明：

- 官方 10 轮里的关键转折是可以出现的
- 但它 **不是当前 prompt + 变量注册表 + 默认 early stop 机制下的稳定必现行为**

---

## 10. 当前结论

如果问题是：

> 对同一个例子、同样条件约束、独立重复运行 4 次真实 LLM 10 轮优化，效果是否一致？

那么当前答案是：

> **前半段方向很一致，最终局部平台值也几乎一致；但无法稳定复现关键策略切换，且在默认设置下甚至不能稳定跑满 10 轮。**

换句话说：

- **局部一致性：强**
- **全局突破一致性：弱**
- **稳定跑满 10 轮：当前默认配置下不满足**

---

## 11. 下一步建议

如果后续要做更严格的对照实验，我建议分成两条线：

### 方案 A：保持当前逻辑，继续做“真实自然一致性”评估

优点：

- 最真实反映当前系统的自然行为

缺点：

- 会被 `invalid_proposal_limit=2` 提前打断
- 不能保证每组都有完整 10 轮可比轨迹

### 方案 B：为了实验而固定 10 轮窗口

建议做法：

- 暴露 `max_invalid_proposals` 为命令行参数
- 把它提高到 `10` 或更大
- 重新跑 4 组

这样可以保证：

- 每组都有完整的 10 次迭代窗口
- 更适合做“逐轮统计一致性”分析

---

## 12. 相关结果位置

- 总实验目录：
  - `demo_runs/consistency_4x10_20260326/`
- 每组 summary：
  - `group_01/demo_summary.md`
  - `group_02/demo_summary.md`
  - `group_03/demo_summary.md`
  - `group_04/demo_summary.md`
- 每组趋势图：
  - `group_01/figures/`
  - `group_02/figures/`
  - `group_03/figures/`
  - `group_04/figures/`

---

## 13. 一句话结论

这 4 组独立实验验证了：

> 当前 LLM 在这个案例上会稳定地做出相似的前期局部优化，但还不能稳定地跨越到能够显著降温的全局策略转折。
