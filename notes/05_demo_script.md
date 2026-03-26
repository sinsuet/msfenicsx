# 老师演示脚本

## 1. 演示目标

本次演示的目标不是证明大模型“神奇地一下子找到最优解”，而是展示一个完整、可解释、可复现的闭环 workflow：

1. 定义热仿真问题
2. 说明初始设计不满足约束
3. 运行一轮真实 LLM 优化
4. 展示预先跑好的 10 轮官方数据
5. 讲清每轮修改、合法性和效果
6. 展示最终中文 Beamer

## 2. 现场建议顺序

### 第一步：介绍问题

先说明当前案例：

- 二维稳态导热教学模型
- 左右冷端边界温度 `25 degC`
- 约束：`chip_max_temperature <= 85 degC`
- 初始热点大约 `89.3 degC`

### 第二步：说明 LLM 不直接改代码

强调：

- LLM 不改 Python 脚本
- LLM 只改结构化 `state`
- 所有提案都要经过合法性校验

### 第三步：现场跑 1 轮

建议命令：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python examples/03_optimize_multicomponent_case.py --real-llm --max-iters 1
```

现场重点讲：

- 这轮看到的当前温度场
- 这轮 LLM 修改了哪些参数
- proposal 为什么先不直接等于“效果”

### 第四步：切到官方 10 轮数据

官方数据位置：

- `demo_runs/official_10_iter/`

建议先展示：

- `demo_summary.md`
- `figures/chip_max_trend.png`
- `figures/delta_trend.png`
- `figures/category_timeline.png`

### 第五步：讲 10 轮里的关键转折

推荐重点讲这几轮：

- `run_0001 ~ run_0005`
  - LLM 持续提高 `spreader conductivity`
  - 温度持续下降，但下降幅度越来越小
- `run_0006`
  - 非法提案
  - 想继续加导热率，但超过上界 `500`
  - 说明系统不会盲目接受 LLM 输出
- `run_0007`
  - 开始尝试几何变量 `width`
  - 但效果几乎没有改善
- `run_0008`
  - 多变量联动提案非法
  - 说明联动虽然更激进，但要受几何合法性约束
- `run_0009`
  - 策略切换到 `base_material.conductivity`
  - 芯片热点从约 `89.26` 明显降到 `58.61`
  - 这是整套 10 轮里最明显的转折点
- `run_0010`
  - 已经满足约束后继续优化
  - 这是为了演示固定 10 轮而启用的 demo 模式

### 第六步：解释 run 和 iteration

一定要明确说：

- `run_0001` 是目录编号
- 真正的轮次看 `decision.json` 里的 `iteration`
- proposal 的效果通常在下一轮 evaluation 才体现

## 3. 最适合老师提问时强调的话

### 为什么不是直接让大模型改代码

因为结构化 state 更可控：

- 能追踪
- 能回滚
- 能验证合法性
- 能比较每轮效果

### 为什么 10 轮里有非法提案

这是优点，不是缺点。

因为它说明：

- LLM 会探索
- 系统有边界
- 非法修改会被拒绝并留下记录

### 为什么后面出现“可行后继续优化”

因为这是老师演示版模式。

目标是：

- 固定展示 10 轮完整 workflow
- 即使约束已经满足，也继续优化 objective

## 4. 演示中建议打开的文件

- `demo_runs/official_10_iter/demo_summary.md`
- `demo_runs/official_10_iter/figures/chip_max_trend.png`
- `demo_runs/official_10_iter/figures/delta_trend.png`
- `demo_runs/official_10_iter/figures/category_timeline.png`
- `slides/demo_workflow_beamer.tex`

## 5. 一句话总结

这套系统展示的不是“LLM 直接替代仿真软件”，而是“LLM 在受约束、可验证、可追踪的工程闭环里参与决策”。
