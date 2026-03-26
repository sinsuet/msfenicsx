# 大模型驱动的热仿真闭环工作流

## 1. 这一步升级了什么

现在项目不再只是“运行一个固定脚本”，而是开始具备一个最小可用的闭环优化骨架：

```text
state.yaml
-> 编译几何 / 网格 / 物理问题
-> 运行 FEniCSx
-> 生成可视化与结构化指标
-> 评估是否满足约束
-> 生成下一轮修改建议
-> 保存完整 run 记录
```

这一步的核心价值不是让大模型直接改 Python，而是让它改“结构化设计状态”。

这样做的好处是：

- 每一轮输入都可重复
- 每一轮输出都可比较
- 每一轮决策都能记录
- 后续更容易做回滚和分支优化

## 2. 当前的关键目录

项目里现在和闭环优化最相关的是这几块：

- `states/`
  - 保存设计状态，例如 `baseline_multicomponent.yaml`
- `src/compiler/`
  - 把状态编译成可运行的热仿真问题
- `src/evaluator/`
  - 根据仿真结果判断是否满足约束
- `src/llm_adapters/`
  - 负责把状态和评估报告交给 DashScope `qwen3.5-plus`
- `src/orchestration/`
  - 负责 run 目录、回滚和多轮循环
- `runs/`
  - 保存每一轮的快照和结果

## 3. 一轮优化里实际发生了什么

以 `examples/03_optimize_multicomponent_case.py` 为例，一轮流程固定为：

1. 读取当前 `state.yaml`
2. 创建新的 `run_0001/`
3. 保存当前状态快照
4. 调用状态驱动求解器跑一次热仿真
5. 生成布局、网格、分区、温度场和总览 HTML
6. 提取结构化指标
7. 用 evaluator 判断是否违反约束
8. 若不满足约束，则生成下一轮修改建议
9. 把本轮的状态、评估和提案全部写入 run 目录

## 4. `runs/` 目录怎么读

当前每轮至少会生成：

```text
runs/
  run_0001/
    state.yaml
    evaluation.json
    proposal.json
    decision.json
    next_state.yaml
    outputs/
      figures/
      data/
```

这些文件分别代表：

- `state.yaml`
  - 本轮仿真实际使用的输入状态
- `evaluation.json`
  - 本轮是否满足约束、违反了什么、目标值是多少
- `proposal.json`
  - 下一轮准备怎么改
- `decision.json`
  - 本轮是否采用提案、状态是什么
- `next_state.yaml`
  - 把提案应用到当前状态后得到的下一轮候选状态

## 5. 当前支持的约束与目标

当前 MVP 先支持最基础、最稳定的一类指标：

- 全局最高温 / 最低温
- 各组件的 `min / max / mean`
- 网格单元数量

当前 baseline 里最重要的约束已经升级成工程化教学阈值：

- `chip_max_temperature <= 85 degC`

当前 baseline 同时使用：

- 冷端边界温度 `25 degC`
- SI 风格单位语义
- 等效体热源

因此当芯片最高温超过 `85 degC` 时，评估器会把这一轮标记为不可行。

## 6. DashScope `qwen3.5-plus` 在哪里接入

接入点在：

- `src/llm_adapters/dashscope_qwen.py`

它负责三件事：

- 构造 prompt
- 调用 DashScope 兼容接口
- 解析并校验结构化 JSON 提案

系统提示词在：

- `prompts/plan_changes_system.md`

当前默认从环境变量读取密钥：

```bash
export DASHSCOPE_API_KEY=你的密钥
```

然后正常运行优化示例即可。

## 7. 现在怎么运行

在项目根目录执行：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python examples/03_optimize_multicomponent_case.py
```

当前示例默认使用：

- `max_iters=1`
- `dry_run_llm=True`

也就是先用一个规则化 stub 代替真实大模型，保证整条闭环链路是通的。

## 8. 怎么切到真实 DashScope

最直接的方式是修改示例调用参数，或者后面我们再给它补命令行参数。

当前代码级入口是：

```python
run_optimization_loop(
    state_path=...,
    runs_root=...,
    max_iters=...,
    dry_run_llm=False,
)
```

当 `dry_run_llm=False` 时，系统会调用 `qwen3.5-plus` 去生成结构化修改建议。

如果你已经在项目根目录放好了 `.env`，并且里面有：

```text
DASHSCOPE_API_KEY=你的真实密钥
```

那么现在可以直接在项目目录执行真实单轮调用：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python examples/03_optimize_multicomponent_case.py --real-llm --max-iters 1
```

如果你想真正跑两轮“提案 -> 应用 -> 重跑”的闭环迭代，可以执行：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python examples/03_optimize_multicomponent_case.py --real-llm --max-iters 2
```

可选参数：

- `--model qwen3.5-plus`
- `--enable-thinking`

## 9. 怎么回滚

当前回滚采用的是“快照不改，只切当前指针”的思路。

接口在：

- `src/orchestration/rollback.py`

当前指针文件是：

- `runs/current_run.txt`

回滚本质上就是把这个指针切回旧轮次，而不是删除任何历史结果。

这意味着你后续可以：

- 回到旧轮次继续分析
- 从旧轮次重新分支
- 对比不同优化路线

## 11. 当前真实模型验证到什么程度了

目前这套链路已经实际验证过：

- `.env` 会在 `examples/03_optimize_multicomponent_case.py` 入口自动加载
- 真实 DashScope 调用能成功返回结构化 JSON
- 原始响应会保存到每轮目录下的 `raw_response.json`
- 两轮闭环迭代已经实际跑通过

从当前 baseline 结果看，模型连续两轮都优先建议提高 `spreader_material.conductivity`。

这说明：

- 结构化提案链路是通的
- 状态应用链路是通的
- 第二轮确实是在第一轮修改后的状态上重新仿真

但也说明一个当前 MVP 的局限：

- 还没有“工程可制造性 / 物理合理性”约束检查
- 模型可能持续把导热率往更高数值推

所以后面最值得优先补的是“提案合法性检查”，比如：

- 导热率上下界
- 几何尺寸上下界
- 组件是否重叠
- 修改步长限制

## 12. 现在有哪些真实合法性约束

当前版本已经在 proposal 应用前加入了独立的合法性检查层。

首版规则包括：

- `conductivity` 必须位于 `0.1 ~ 500`
- 组件 `width` 和 `height` 必须大于 0
- `mesh.nx` 和 `mesh.ny` 必须位于 `2 ~ 300`
- 单轮导热率改动最多 `2x`
- 单轮尺寸改动最多 `±50%`
- 单轮位置改动最多当前总包络宽高的 `25%`
- 组件不能重叠
- 组件不能跑出当前外包络

## 13. 非法提案会发生什么

如果模型给出非法提案，系统不会直接偷偷修正，而是会：

1. 保存 `proposal.json`
2. 生成 `proposal_validation.json`
3. 在 `decision.json` 里标记为 `invalid_proposal`
4. 不生成新的合法 `next_state.yaml`

这样你后面分析时可以清楚区分：

- 模型到底提了什么
- 哪些地方不合法
- 为什么这轮没有继续推进

这也更适合后面把“违规原因”重新喂给模型，逼着它逐步学会在真实约束里搜索。

## 14. 非法原因现在会反馈给下一轮模型

从当前版本开始，如果某一轮提案被判定为 `invalid_proposal`，系统会把违规原因加入下一轮的 `history_summary`。

这意味着下一轮 prompt 不再只告诉模型：

- 当前温度约束没满足

还会额外告诉模型：

- 上一轮为什么非法
- 哪条步长限制被触发
- 是否越出了当前几何包络

这一步的意义很大，因为它把系统从“单纯拦截错误”升级成了“把错误变成下一轮可学习的反馈”。

## 15. 现在有显式 design_domain 了

从当前版本开始，几何合法性不再只看“当前组件外包络”，而是看状态里显式定义的 `geometry.design_domain`。

这意味着：

- 组件可以在允许的装配域内部扩展
- 系统不会再因为“高过当前 spreader 顶部”就自动判非法
- 只有真正超出设计域时，才会被几何约束拦下

对当前 baseline，`design_domain` 是一个矩形：

- `x0 = 0.0`
- `y0 = 0.0`
- `width = 1.2`
- `height = 0.5`

它比当前组件总高度略大，专门给后续几何优化留出一点真实可探索空间。

## 16. 多轮历史工作台怎么生成

现在项目里已经有一个单独的历史工作台入口脚本：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python examples/04_build_history_dashboard.py
```

它会扫描当前 `runs/run_xxxx/`，并生成：

- `runs/history_summary.json`
- `runs/history.html`

其中：

- `history_summary.json` 是结构化历史索引
- `history.html` 是可直接打开的多轮分析工作台

首版工作台会集中展示：

- 每轮 `chip_max_temperature` 趋势
- 每轮状态，例如 `proposal_applied` 或 `invalid_proposal`
- 每轮 proposal / validation / decision 摘要
- 跳转到单轮 `overview.html` 和 `temperature.html` 的入口

## 10. 你后续最值得做的事

下一步最有价值的是这几项：

1. 把 `dry_run_llm=True` 切成真实 DashScope 调用
2. 增加更多可改设计变量，例如芯片位置、扩展块尺寸和边界温度
3. 把 `history.html` 做出来，展示每轮指标变化曲线
4. 增加提案合法性检查，避免模型给出越界几何

这样这套系统就会从“可跑的 MVP”逐步升级成真正可实验、可优化、可回溯的设计平台。
