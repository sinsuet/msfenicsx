# 当前单案例实现总览

## 1. 文档目的

这份文档用于归纳当前仓库里这组二维稳态导热案例的完整实现状态，覆盖：

- 问题定义
- 几何与组件建模
- 组件最初摆放
- 初始仿真结果
- LLM 参与优化的闭环 workflow
- 官方 10 轮演示数据的主要结果

这份文档可以直接作为老师演示前的总览材料，也可以作为后续整理中文 Beamer 的上位说明。

---

## 2. 问题定义

当前案例是一个 **二维稳态导热** 教学模型，采用 SI 风格单位：

- 长度单位：`m`
- 温度单位：`degC`
- 导热率单位：`W/(m*K)`
- 热源单位：`W/m^3`

核心目标是解决这样一个问题：

> 在一个由底板、芯片和热扩展块组成的二维结构中，给定材料导热率、边界温度和等效体热源后，求解温度场，并通过 LLM 对设计参数进行结构化修改，使芯片最高温度满足约束。

当前最重要的约束是：

- `chip_max_temperature <= 85 degC`

当前冷端边界条件是：

- 左右边界为 `25 degC`
- 其他边界为零通量 Neumann 边界

在数学上，这个案例求解的是稳态热传导方程：

```text
-div(k grad(T)) = q
```

其中：

- `T` 是温度场
- `k` 是各子区域材料导热率
- `q` 是芯片所在区域的等效体热源

---

## 3. 组件建模与最初摆放

当前几何定义在 `states/baseline_multicomponent.yaml` 中，设计域为：

- `x0 = 0.0`
- `y0 = 0.0`
- `width = 1.2`
- `height = 0.5`

共有 3 个矩形组件：

| 组件 | 左下角 `(x0, y0)` | 尺寸 `(width, height)` | 材料 | 导热率 |
| --- | --- | --- | --- | --- |
| `base_plate` | `(0.0, 0.0)` | `(1.2, 0.2)` | `base_material` | `12.0` |
| `chip` | `(0.45, 0.2)` | `(0.3, 0.12)` | `chip_material` | `45.0` |
| `heat_spreader` | `(0.25, 0.32)` | `(0.7, 0.1)` | `spreader_material` | `90.0` |

热源定义：

- `chip` 上施加等效体热源 `15000 W/m^3`

### 3.1 初始布局图

![初始组件布局](../outputs/02_multicomponent_steady_heat/figures/layout.png)

这张图展示了三层矩形组件的最初摆放关系：

- 底板在最下方，承担主要传热路径
- 芯片位于中上部，是发热源
- 热扩展块位于芯片上方，用于改善横向热扩散

### 3.2 网格图

![有限元网格](../outputs/02_multicomponent_steady_heat/figures/mesh.png)

当前求解使用三角形网格离散，函数空间采用：

- 温度场：`Lagrange P1`
- 材料场和热源场：`DG0`

### 3.3 子区域划分图

![子区域划分](../outputs/02_multicomponent_steady_heat/figures/subdomains.png)

这张图对应组件分区标签。不同区域拥有不同的导热率和热源赋值，这一步是将“几何组件”映射为“物理参数场”的关键。

---

## 4. 初始仿真结果

当前 baseline 的初始求解结果约为：

- `temperature_min = 25.0 degC`
- `chip_max_temperature = 89.3013 degC`

因此它 **不满足** 当前约束：

- `89.3013 degC > 85.0 degC`

这正好构成了后续 LLM 优化的起点。

### 4.1 初始温度场

![初始温度场](../outputs/02_multicomponent_steady_heat/figures/temperature.png)

从图上可以直观看到：

- 高温区集中在芯片及其上方热扩展块附近
- 左右冷端边界将温度拉回到 `25 degC`
- 整个结构存在明显的温度梯度

---

## 5. 当前实现的整体 workflow

当前实现不是“让大模型直接改脚本”，而是让它参与一个 **状态驱动、可验证、可回滚** 的工程闭环。

整体流程如下：

```text
state.yaml
-> 编译几何 / 网格 / 物理问题
-> FEniCSx 求解
-> 生成图像、HTML 和结构化指标
-> evaluator 判断是否满足约束
-> LLM 生成结构化修改提案
-> validator 检查提案是否合法
-> 生成 next_state.yaml
-> 进入下一轮
```

实现上可以概括为 5 层：

1. `thermal_state`
   - 管理 `state.yaml` 的 schema 与 load/save
2. `compiler`
   - 从 state 编译几何、网格、材料场、热源场和 PDE
3. `evaluator`
   - 从仿真结果提取 `chip_max_temperature` 等指标，并判断是否违反约束
4. `llm_adapters`
   - 调用 DashScope `qwen3.5-plus`，要求输出结构化 JSON 提案
5. `orchestration`
   - 管理每轮 run 目录、proposal 校验、回滚和多轮循环

---

## 6. 当前 LLM 可以修改的参数

当前 LLM 只允许修改注册表中明确列出的参数，不能直接改 Python 脚本。

| 路径 | 当前 baseline 值 | 范围 | 类别 | 角色 | 推荐方向 |
| --- | --- | --- | --- | --- | --- |
| `materials.spreader_material.conductivity` | `90.0` | `20.0 ~ 500.0` | `material` | `primary` | `increase` |
| `materials.base_material.conductivity` | `12.0` | `5.0 ~ 250.0` | `material` | `supporting` | `increase` |
| `components.2.width` | `0.70` | `0.20 ~ 1.00` | `geometry` | `primary` | `increase` |
| `components.2.height` | `0.10` | `0.05 ~ 0.18` | `geometry` | `primary` | `increase` |
| `components.2.x0` | `0.25` | `0.0 ~ 0.5` | `geometry` | `supporting` | `move_toward_chip_center` |
| `components.2.y0` | `0.32` | `0.20 ~ 0.40` | `geometry` | `supporting` | `move_toward_chip_with_clearance` |
| `heat_sources.0.value` | `15000.0` | `5000.0 ~ 50000.0` | `load` | `scenario` | `decrease` |

额外限制：

- 导热率单步变化不能超过 `2.0x`
- 尺寸单步变化不能超过 `1.5x`
- 位置移动不能超过设计域宽高的 `25%`
- 组件不能重叠
- 组件不能超出设计域

---

## 7. run 与 iteration 的区别

这是后续展示时最容易混淆的一点。

### 7.1 `run_0001` 是什么

`run_0001`、`run_0002` 这类名字是 **run 目录编号**。

每个 `run_xxxx/` 目录只对应一次 iteration，目录里会保存：

- `state.yaml`
- `evaluation.json`
- `proposal.json`
- `proposal_validation.json`
- `decision.json`
- `next_state.yaml`
- `outputs/`

### 7.2 真正的循环轮次看哪里

真正的“这是本次优化中的第几轮”，看：

- `decision.json` 里的 `iteration`

### 7.3 proposal 的效果为什么常常要看下一轮

因为：

- `run_N/evaluation.json` 描述的是当前状态的仿真结果
- `run_N/proposal.json` 描述的是“准备给下一轮用的修改”
- 所以这次修改的效果通常在 `run_{N+1}/evaluation.json` 里才体现出来

这也是为什么后面做演示总结时，我们需要把“本轮修改”和“下一轮效果”自动串起来。

---

## 8. 官方 10 轮演示数据

当前已经生成了一套老师演示专用数据集：

- `demo_runs/official_10_iter/`

这套数据是为了老师演示专门重跑的，和开发阶段旧 `runs/` 分开。

### 8.1 10 轮总体趋势

![热点温度趋势](../demo_runs/official_10_iter/figures/chip_max_trend.png)

### 8.2 每轮改善量

![每轮改善量](../demo_runs/official_10_iter/figures/delta_trend.png)

### 8.3 修改类别时间线

![修改类别时间线](../demo_runs/official_10_iter/figures/category_timeline.png)

从这 3 张图可以看出：

- 前 5 轮主要在调材料导热率
- 中间出现了非法提案
- 后面开始尝试几何变量
- 第 9 轮出现显著策略切换并带来最大改善

---

## 9. 官方 10 轮的关键转折

### 9.1 `run_0001 ~ run_0005`：持续提高热扩展块导热率

这几轮主要修改：

- `spreader conductivity: 90 -> 126 -> 200 -> 300 -> 420 -> 500`

效果：

- 热点从 `89.3013` 逐步下降到约 `89.2562 degC`
- 说明“只靠提高热扩展块导热率”可以改善，但边际收益越来越小

### 9.2 `run_0006`：非法提案

这轮 LLM 想继续把：

- `spreader conductivity: 500 -> 700`

但被 validator 拒绝，因为超过了上界 `500`。

这说明系统不会盲目接受 LLM 的输出，而是会保留提案并明确记录非法原因。

### 9.3 `run_0007 ~ run_0008`：开始尝试几何与联动

这两轮出现了新的方向：

- `run_0007`：改 `components.2.width: 0.70 -> 0.84`
- `run_0008`：试图联动改 `conductivity` 和 `width`

但：

- `run_0007` 的几何调整几乎没有改善
- `run_0008` 因为超过导热率上界和宽度上界而非法

这一步非常适合在演示里说明：

- LLM 并不是一次就能找到好策略
- 多变量联动也必须服从几何和物理边界

### 9.4 `run_0009`：真正的策略切换

这轮的关键修改是：

- `materials.base_material.conductivity: 12.0 -> 24.0`

这是整套 10 轮里最重要的转折点。前面的 LLM 主要盯着热扩展块，但这一轮开始意识到：

- 下游传热路径也可能是瓶颈

而它的效果在下一轮 `run_0010` 中体现得非常明显：

- `chip_max_temperature` 从约 `89.2562` 下降到 `58.6129 degC`

### 9.5 `run_0010`：满足约束后继续优化

`run_0010` 已经满足约束：

- `58.6129 degC < 85.0 degC`

但为了老师演示能够固定展示 10 轮，我们启用了 demo 模式：

- 即使已经可行，也继续优化 objective，直到达到 `max_iters=10`

这不是正常工程停机策略，而是 **老师演示专用模式**。

---

## 10. 代表性图片对比

### 10.1 初始官方 run 温度场

![官方 run_0001 温度场](../demo_runs/official_10_iter/run_0001/outputs/figures/temperature.png)

### 10.2 关键突破后的温度场

这里展示的是 `run_0010` 的温度场，它对应了 `run_0009` 策略切换之后的结果。

![官方 run_0010 温度场](../demo_runs/official_10_iter/run_0010/outputs/figures/temperature.png)

对比可以看到：

- 初始高温区明显集中在芯片和热扩展块附近
- 在提高底板导热率之后，整体温度水平大幅降低
- 这说明瓶颈并不总在热扩展块本身，也可能在更下游的散热路径

---

## 11. 当前实现的优点与局限

### 11.1 优点

- 已经形成完整的状态驱动 workflow
- LLM 修改是结构化、可追踪、可回滚的
- 每轮都有图、有指标、有 proposal、有合法性记录
- 已经具备老师演示专用的官方 10 轮数据集

### 11.2 局限

- 当前仍然是二维稳态教学模型
- 还没有引入对流边界
- 还没有界面热阻
- 还没有瞬态过程
- 还不能等同于真实产品的热认证模型

---

## 12. 当前相关产物位置

最重要的文件如下：

- 初始案例图片：
  - `outputs/02_multicomponent_steady_heat/figures/`
- 官方 10 轮演示数据：
  - `demo_runs/official_10_iter/`
- 官方演示总表：
  - `demo_runs/official_10_iter/demo_summary.md`
- 官方演示趋势图：
  - `demo_runs/official_10_iter/figures/`
- 中文 Beamer 初稿：
  - `slides/demo_workflow_beamer.tex`
- 老师演示脚本：
  - `notes/05_demo_script.md`

---

## 13. 一句话总结

这组实现展示的不是“LLM 直接替代仿真器”，而是：

> LLM 在一个受约束、可验证、可回滚、可追踪的热设计闭环里参与决策，并通过多轮迭代逐步改善设计。
