# msfenicsx

**面向卫星热控布局的语义化多目标优化研究平台**

`msfenicsx` 针对卫星板级组件布局优化问题——散热资源受限、非线性辐射散热边界、昂贵 PDE 评估——提出一种将大语言模型（LLM）作为语义控制器嵌入进化算法的优化范式。LLM 不直接生成设计解，而是在每次 offspring generation 中读取热状态与搜索阶段，对候选热设计动作做语义排序，由确定性框架执行最终选择。

## 问题定义

卫星热布局不是一般的连续优化问题。它具有典型的航天热控特征：

- **散热资源不可无限扩展**：散热器窗口有固定跨度预算，组件移动同时改变热点位置、热梯度和散热器耦合关系
- **强耦合约束**：组件位置、散热器窗口、热源簇、热点偏移、局部拥挤、散热预算之间相互制约
- **昂贵物理评估**：每步评估需求解 2D 稳态热传导 PDE（FEniCSx 有限元求解），预算严格受限
- **阶段化设计决策**：尚未可行时优先减少违反；可行后需在保持与扩展之间切换；热点偏离散热窗口时需对准调整

传统进化算法（如 NSGA-II）在数值空间做无解释扰动，无法区分"散热器没对准"和"热源簇太拥挤"。

## 核心方法

### 结构化热设计算子基底

将传统 `x/y/sink_start/sink_end` 决策空间提升为一组带热控语义的 primitive actions：

| 算子类别 | 热设计语义 |
|---------|-----------|
| `sink_alignment` | 对准散热窗口 |
| `sink_budget_shape` | 调整散热预算分配 |
| `semantic_block_move` | 迁移热源簇 |
| `semantic_subspace_recombine` | 子空间重组 |
| `local_polish` | 局部拥挤缓解 |
| `global_layout_expand` | 全局布局扩展 |
| `baseline_reset` | 可行基线重置 |

算法搜索的不再是无解释扰动，而是可解释的热设计动作。

### LLM 语义排序控制器

LLM 的角色是 **semantic policy estimator**，而非优化器本体：

- **语义压缩**：将高维搜索状态压缩为热控语义任务（sink alignment、block movement、local polish 等）
- **上下文匹配**：读取当前搜索阶段、可行率、Pareto 停滞、热点-散热器偏移、近期算子历史，将状态与算子角色对齐
- **风险排序**：对每个候选算子给出 score / risk / confidence，而非仅选最激进动作

PDE solver 负责物理真值，NSGA-II 负责种群选择，repair / cheap constraints 负责合法性——LLM 只做软判断。

### 确定性护栏

可靠性来自"LLM 只做软判断，硬边界由程序控制"：

- 候选算子为固定白名单，LLM 不能发明非法动作
- 输出为结构化 JSON ranking，有 schema validation
- 最终选择经 `semantic_ranked_pick` 确定性选取，含 rolling operator cap、semantic task cap、generation cap
- fallback 为 `random_uniform`，确保可复现

## 消融实验设计

`raw` → `union` → `llm` 严格消融链，隔离语义控制贡献：

**raw** — 原生 NSGA-II 骨干基线

直接使用 NSGA-II 内置变异和交叉算子，不引入额外算子池或语义信息。

**union** — 固定随机算子选择

引入相同的结构化算子池，但以固定随机策略选择算子。这是 LLM 控制器的消融对照组：相同的算子能力，但没有语义引导。`union` 的意义不是更强 baseline，而是证明"更多动作不必然带来更好搜索"——没有状态判断时，丰富的算子池反而扩大了错误选择空间。

**llm** — LLM 语义控制器

在相同的算子池、repair、cheap constraints 和 PDE budget 基础上，替换为语义控制策略。因此改进可归因到 LLM 的 representation-layer semantic control，而非额外算子、额外预算或不同求解器。

## 基准场景

三个规模递进的卫星板级基准场景，组件以对抗性策略放置，制造多瓶颈热耦合：

| 场景 | 组件数 | 决策变量数 | PDE 评估预算 |
|------|--------|-----------|-------------|
| S4   | 10     | 22        | 512         |
| S5   | 15     | 32        | 1280        |
| S6   | 20     | 42        | 2016        |

每个场景包含异构组件族（核心计算模块、功率器件、I/O 板、传感器、连接器等），带有语义放置提示和最小间距约束。散热器窗口位于顶边，跨度有限，其起止位置作为决策变量。所有组件仅优化 x/y 位置。

## 最终实验结构

当前论文实验固定为主实验和四个诊断/上下文 block：

| Block | 实验 | 作用 |
|------|------|------|
| Main | S4/S5/S6，5 seeds，`raw` vs `llm_deepseek_v4_flash` | 验证主方法在规模递增场景上稳定优于 raw |
| Semantic Ablation | S4，5 seeds，`raw / union / llm` | 隔离语义控制贡献，说明不是多算子池本身带来的 |
| Mechanism / Feedback-Off Diagnostic | S6 seed23，raw vs feedback-off DeepSeek；LLM root 为 `scenario_runs/s6_aggressive20/0510_1239__llm-deepseek_v4_flash/llm-deepseek-v4-flash/seeds/seed-23` | 作为 single-seed mechanism ablation / negative control，检验 operator-level PDE feedback 闭环必要性 |
| Model Sensitivity | S5 seed11，DeepSeek/Qwen/GPT-5.5/MiMo | 说明机制不是单一模型特例，但不做强统计 claim |
| Algorithm Baseline | S5，5 seeds，NSGA-II/SPEA2/MOEA/D raw | 说明 raw baseline 不是因为 NSGA-II 太弱 |

当前 paper-facing seed policy：

- S4 main 与 S4 semantic ablation 使用 seeds `[11, 13, 17, 19, 23]`，正式归档为 `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed`。
- S5 main 使用 seeds `[11, 19, 23, 37, 41]`，正式归档为 `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5`。
- S5 algorithm baseline 使用 seeds `[11, 23, 31, 37, 41]`。
- S5 model sensitivity 使用 seed `11`，GPT-5.5 按正常有效 profile 结果呈现。
- S6 main 使用 seeds `[11, 13, 19, 21, 23]`，正式归档为 `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed`。
- S6 seed23 mechanism / feedback-off diagnostic 为 diagnostic-only，不纳入 S6 main aggregate；其 LLM 机制消融源 run 是旧跑 `scenario_runs/s6_aggressive20/0510_1239__llm-deepseek_v4_flash/llm-deepseek-v4-flash/seeds/seed-23`。

## 当前 Stage A 结果口径

Stage A 已完成 S4/S5/S6 main、S4 semantic ablation、S6 seed23 mechanism / feedback-off diagnostic、S5 model sensitivity 和 S5 raw-only algorithm baseline 的 paper experiment database。主统计看每个 registered block 内的 multi-seed aggregate mean；paper-facing nIGD 使用 `block_archive_dense_nigd`，即基于现有 PDE evaluation trace 的 block-level empirical archive dense reference，不重跑实验。在三个 main block 中，DeepSeek LLM 相比 raw 在 mean nIGD、mean hypervolume、mean gradient RMS、mean peak temperature 和 feasible rate 上均占优。S6 seed23 mechanism / feedback-off diagnostic 只作为 single-seed 机制消融证据，不替代 multi-seed aggregate 统计。

## 快速上手

### 环境安装

FEniCSx 求解器栈（dolfinx、basix、ffcx、ufl、PETSc、mpi4py）依赖系统级 MPI 和 C 库，必须通过 conda-forge 安装；其余 Python 依赖通过 pip 安装。两条路径：

**全新安装（推荐）**

```bash
git clone <repo-url> && cd msfenicsx
conda env create -f environment.yml
conda activate msfenicsx
```

`environment.yml` 会创建 `msfenicsx` 环境，先装 FEniCSx 全家桶，再 `pip install -e ".[llm,dev]"` 装所有 Python 依赖（含 LLM 客户端和测试工具）。

**已有 FEniCSx 环境**

```bash
pip install -e ".[llm,dev]"
```

可选的 extras 分组：

| 安装命令 | 包含内容 |
|---------|---------|
| `pip install -e .` | 核心依赖（numpy、scipy、matplotlib、pymoo 等） |
| `pip install -e ".[llm]"` | 核心 + OpenAI LLM 客户端 |
| `pip install -e ".[dev]"` | 核心 + pytest 测试工具 |
| `pip install -e ".[llm,dev]"` | 全部 |

### 最小示例：从模板到求解

```bash
# 1. 验证场景模板
conda run -n msfenicsx python -m core.cli.main validate-scenario-template \
  --template scenarios/templates/s5_aggressive15.yaml

# 2. 生成测试用例
conda run -n msfenicsx python -m core.cli.main generate-case \
  --template scenarios/templates/s5_aggressive15.yaml \
  --seed 11 \
  --output-root ./scenario_runs/generated_cases/s5_aggressive15/seed-11

# 3. 求解用例
conda run -n msfenicsx python -m core.cli.main solve-case \
  --case ./scenario_runs/generated_cases/s5_aggressive15/seed-11/s5_aggressive15-seed-0011.yaml \
  --output-root ./scenario_runs

# 4. 评估求解结果
conda run -n msfenicsx python -m evaluation.cli evaluate-case \
  --case ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/case.yaml \
  --solution ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/solution.yaml \
  --spec scenarios/evaluation/s5_aggressive15_eval.yaml \
  --output ./evaluation_report.yaml \
  --bundle-root ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011
```

### 优化运行

```bash
# 单模式 smoke 测试（小预算，workers=2 仅用于快速检查）
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml \
  --mode raw \
  --benchmark-seed 11 \
  --algorithm-seed 1011 \
  --population-size 2 \
  --num-generations 1 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs

# 正式 Main block：S4/S5/S6 raw vs DeepSeek LLM
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s4_main_raw_llm_deepseek_budgeted.yaml

conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s5_main_raw_llm_deepseek_budgeted.yaml

conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s6_main_raw_llm_deepseek_budgeted.yaml

# S4 semantic ablation
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s4_semantic_ablation_budgeted.yaml

# 单 seed LLM smoke 调参（小预算）
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --mode llm \
  --llm-profile deepseek_v4_flash \
  --benchmark-seed 11 \
  --algorithm-seed 1011 \
  --population-size 5 \
  --num-generations 2 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

`run-benchmark` 是 optimizer 的唯一公开运行入口，自动执行 leaf 后处理、渲染分析图表、LLM trace 诊断，并在 campaign 内生成 seed-aware comparison。

正式 overnight/budgeted 运行不要沿用 smoke 的 `--evaluation-workers 2`。S4/S5/S6 paper-facing batch 使用 batch spec 中的 `max_concurrent_leaves=4`、`leaf_evaluation_workers=32`；正式单 leaf LLM/profile 补跑通常使用 `--evaluation-workers 32`。

## 项目结构

| 模块 | 职责 |
|------|------|
| `core/` | 模型定义、几何引擎、网格生成、FEniCSx 求解器、产物 I/O、CLI |
| `evaluation/` | 评估规范、指标计算、评估报告 |
| `optimizers/` | 决策编码、修复、约束检查、raw/union/llm 驱动、统一 benchmark runner、分析与可视化资产 |
| `llm/` | OpenAI 兼容的 LLM 控制器客户端 |
| `visualization/` | 图表生成（Pareto 前沿、温度场、梯度场、超体积、布局演化、算子热力图） |
| `scenarios/` | 场景模板、评估规范、优化规范 |
| `tests/` | 自动化测试 |
| `docs/` | 设计文档、计划、报告 |

## 文档

- `CLAUDE.md` — Claude Code 会话指南（CLI 全集、LLM 配置、工程规范）
- `AGENTS.md` — Codex 会话指南
- `docs/superpowers/specs/` — 详细设计文档
- `docs/superpowers/plans/` — 实施计划
- `docs/reports/` — 分析报告

## 许可

本项目为学术研究用途。
