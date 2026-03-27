# R58 面向 MsGalaxy 论文创新点的 LLM 算子策略与仿真流程优化正式报告（2026-03-26）

## 1. 报告目的

本报告承接 [R57_llm_operator_policy_research_plan_20260325.md](./R57_llm_operator_policy_research_plan_20260325.md)，但目标更聚焦于论文写作本身，而不是泛泛的研究综述。

本报告试图回答四个问题：

- 在近三年真实可考证的高质量文献中，哪些工作最能支撑 MsGalaxy 当前的论文主张。
- 以当前 `mass` 主线为基础，传统 `pymoo + proxy/COMSOL` 流程的关键痛点到底是什么。
- LLM 最合理的插入层在哪里，哪些能力应该交给 LLM，哪些能力必须留给数值优化器和物理求解器。
- 如何形成一条可信、可复现、符合当前代码真相的论文叙事，使“加入 LLM 后优于传统方法”成为可验证结论。

本报告只以当前仓库真实实现为边界，不将尚未稳定落地的目标能力误写为已实现事实。

## 2. 当前系统真相与论文边界

截至 `2026-03-26`，与论文主张直接相关的仓库真相以以下文档为准：

- [HANDOFF.md](../../HANDOFF.md)
- [AGENTS.md](../../AGENTS.md)
- [0016-mass-search-space-mode-hybrid-operator-integration.md](../adr/0016-mass-search-space-mode-hybrid-operator-integration.md)
- [0007-vop-maas-verified-operator-policy-experimental-mode.md](../archive/adr/0007-vop-maas-verified-operator-policy-experimental-mode.md)
- [R21_l1_l4_algo_llm_campaign_20260306.md](../archive/reports/R21_l1_l4_algo_llm_campaign_20260306.md)

当前必须诚实坚持的边界如下：

- 活跃稳定主线仍是 `mass`。
- 默认稳定搜索空间仍是 `position_only`。
- `operator_program / hybrid` 已接回 `mass` 主线，但生命周期仍是 `experimental`。
- 当前已经有：
  - `position_only` 的重复 real-chain evidence；
  - `operator_program` 的单 seed 受控 real-chain evidence；
  - `hybrid` 的 `seed=42,43,44` 三次受控 real-chain evidence。
- 当前还没有：
  - `matched budget + 多 seed + 统计显著性` 的 LLM 优效结论；
  - “LLM 已稳定优于传统方法”的发布级证据；
  - “MP-OP-MaaS v3 完整落地”的实现事实。

因此，论文不能写成：

- “LLM 直接生成最终物理可行布局”
- “LLM 替代 NSGA-II / NSGA-III / MOEA/D”
- “当前系统已经证明 LLM 全面优于传统方法”

论文真正能够安全承载的主命题应当是：

> 在合同保护与多保真物理反馈下，LLM 作为语义化算子策略控制器与仿真流程调度器，可以提升混合搜索空间中的搜索效率和高保真预算效率。

## 3. 报告结论先行

本报告的核心判断如下：

1. MsGalaxy 最值得写成论文创新点的，不是“LLM 替代传统优化器”，而是“LLM 控制传统优化器如何使用领域算子与多保真仿真预算”。
2. 当前流程中的最大缺口，不是算子不够多，而是缺少一个能根据 `dominant violation + component semantics + historical trace + fidelity budget` 动态调度算子的上层策略器。
3. 近三年高质量文献最成功的共同范式，几乎都不是让 LLM 端到端替代求解器，而是让 LLM 做：
   - 策略生成；
   - 工具调用；
   - 工作流编排；
   - 启发式或超启发式控制；
   - 反思与再规划。
4. 因此，MsGalaxy 论文的最强主创新，应收敛为：

> **Verified LLM Operator-Policy for Contract-Safe Hybrid Search under Multi-Fidelity Physics Feedback**

对应中文表达可写为：

> **面向合同安全混合搜索与多保真物理反馈的可验证 LLM 算子策略控制框架**

## 4. 近三年高质量文献调研结论

本节只保留对 MsGalaxy 论文真正有帮助的文献。筛选原则如下：

- 近三年为主，必要时保留极少量 2023 年底到 2024 年初的奠基文献。
- 只保留真实可访问的一手来源。
- 优先保留期刊、顶会、官方出版页或官方论文页。

### 4.1 第一组：LLM 作为优化建模器、优化器或超启发式控制器

| 文献 | 来源 | 与 MsGalaxy 的关系 | 本报告结论 |
| --- | --- | --- | --- |
| [Large Language Models as Optimizers](https://openreview.net/forum?id=Bb4VGOWELI) | ICLR 2024 | 代表性“LLM 参与优化”方法论文 | 说明 LLM 可以做 proposal-based optimization，但更像高层启发式，不适合直接替代工程数值求解内核 |
| [Chain-of-Experts: When LLMs Meet Complex Operations Research Problems](https://openreview.net/forum?id=HobyL1B9CZ) | ICLR 2024 | OR 领域与 LLM 结合的重要证据 | 支持“LLM 更适合做结构化分工、问题拆解与策略生成，而非裸做精确求解” |
| [ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution](https://arxiv.org/abs/2402.01145) | NeurIPS 2024 Workshop / arXiv | 与“LLM 调算子、调启发式”最接近的方法论文之一 | 强力支持把 LLM 放在 hyper-heuristic / operator policy 层 |
| [OptiBench Meets ReSocratic: Measure and Improve LLMs for Optimization Modeling](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3deb687c44d3687ace0729e5db3b4efd-Abstract-Conference.html) | ICLR 2025 | 优化建模基准与改进方法 | 提醒我们 LLM 在优化建模上仍需要验证、纠错与 solver 回路，不能神化其直接求解能力 |
| [Decision Information Meets Large Language Models: The Future of Explainable Operations Research](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a48e5877c7bf86a513950ab23b360498-Abstract-Conference.html) | ICLR 2025 | OR + 可解释决策的重要综述/立场论文 | 非常适合支撑“违规-算子-结果”证据图与可解释工作流叙事 |

#### 4.1 结论

这组文献共同支持以下判断：

- LLM 可以参与优化，但最稳妥的位置不是“替代 solver”。
- LLM 的强项在于：
  - 结构化策略生成；
  - 启发式更新；
  - 反思式改进；
  - 与外部求解器组成闭环。
- 这与 MsGalaxy 当前“必须保留 `pymoo + proxy/COMSOL` 真值链”的技术边界是完全一致的。

### 4.2 第二组：LLM 负责工具调用、实验编排与科学工程闭环

| 文献 | 来源 | 与 MsGalaxy 的关系 | 本报告结论 |
| --- | --- | --- | --- |
| [Autonomous chemical research with large language models](https://www.nature.com/articles/s41586-023-06792-0) | Nature 2024 | LLM + 工具 + 实验闭环的标志性工作 | 最核心启发是：LLM 的价值在于调用工具、规划步骤、读取反馈，而不是替代实验平台 |
| [ChemCrow: Augmenting large-language models with chemistry tools](https://www.nature.com/articles/s42256-024-00832-8) | Nature Machine Intelligence 2024 | 工具增强型 LLM 代表工作 | 强烈支持“LLM 做工具编排器”的路线，与我们要做的 solver/proxy/COMSOL orchestration 高度同构 |
| [Opportunities for retrieval and tool augmented large language models in scientific facilities](https://www.nature.com/articles/s41524-024-01423-2) | npj Computational Materials 2024 | 检索增强与设施级工具闭环 | 支持我们在 LLM 策略层引入 evidence graph、检索和工具选择逻辑 |
| [An automatic end-to-end chemical synthesis development platform powered by large language models](https://www.nature.com/articles/s41467-024-54457-x) | Nature Communications 2024 | 端到端科学研发流程自动化 | 直接支撑“LLM 优化的是流程本身，而不仅是单次推理输出” |
| [Reasoning-agent-driven process simulation, optimization, carbon accounting and decarbonization of distillation](https://www.nature.com/articles/s44172-025-00583-3) | Communications Engineering 2026 | 与“仿真流程优化”最接近的最新工程案例之一 | 支持将 LLM 写成 process simulation / optimization workflow controller，而不是直接替代求解器 |

#### 4.2 结论

这组文献最重要的共同点是：

- LLM 成功的前提是接入外部工具链；
- LLM 真正优化的是工作流、决策顺序与试验/仿真资源配置；
- 这恰好对应 MsGalaxy 中最稀缺但最有价值的那一层，即：
  - 算子策略控制；
  - 多保真调度；
  - 失败反思与再规划。

### 4.3 第三组：与工程优化、调度、设计工作流最接近的相邻工作

| 文献 | 来源 | 与 MsGalaxy 的关系 | 本报告结论 |
| --- | --- | --- | --- |
| [Leveraging large language models for efficient scheduling in Human-Robot collaborative flexible manufacturing systems](https://www.nature.com/articles/s44334-025-00061-w) | npj Advanced Manufacturing 2025 | LLM 进入制造调度闭环 | 很适合支撑“LLM 不直接替代优化器，而是生成/更新调度策略”的工程叙事 |
| [MASC: Large language model-based multi-agent scheduling chain for flexible job shop scheduling problem](https://www.sciencedirect.com/science/article/pii/S1474034625004203) | Advanced Engineering Informatics 2025 | 多 agent + 调度 + 工程求解近邻 | 支持“多步策略链 + 传统求解模块”的工程工作流路线 |
| [A Large Language Model-based Multi-Agent Framework to Autonomously Design Algorithms for Earth Observation Satellite Scheduling Problem](https://www.sciencedirect.com/science/article/pii/S2095809925006654) | Engineering 2025 | 与航天任务调度最邻近 | 说明“航天/卫星问题 + LLM 设计策略/算法”已是可发表方向 |
| [Integrating large models with topology optimization for conceptual design realization](https://www.sciencedirect.com/science/article/pii/S1474034625004173) | Advanced Engineering Informatics 2025 | 与“保留优化内核，仅让 LLM 做概念/策略层”高度接近 | 是 MsGalaxy 论文叙事的重要近邻证据 |
| [Development of an intelligent design and simulation aid system for heat treatment processes based on large language model](https://www.sciencedirect.com/science/article/pii/S0264127524008815) | Materials & Design 2025 | LLM 进入工程设计与仿真辅助 | 支持把 LLM 写成 design/simulation aid system，而不是直接数值求解器 |

#### 4.3 结论

工程领域最新文献已经给出一个很明确的方向：

- LLM 可以进入设计、调度、仿真与优化流程；
- 但最成功的模式，几乎都保留了外部优化器、仿真器或实验平台；
- 这正是 MsGalaxy 应当遵循的研究路线。

## 5. 当前传统方法的关键问题

如果按当前代码真相来定义“传统方法”，至少包括两条基线：

- `position_only + pymoo`
- `hybrid/operator_program + static pymoo`

这两类方法分别有不同短板。

### 5.1 `position_only` 的问题

`position_only` 的优点是稳定、简单、真实证据最完整，但它存在明显的语义表达力瓶颈：

- 只在连续坐标空间中试错。
- 很难表达高阶卫星工程动作。
- 难以直接表达：
  - 热扩散类动作；
  - 结构支撑附加动作；
  - 电源/总线邻近关系调整；
  - mission keep-out 语义级推离。

因此，`position_only` 更像是：

> 一个稳定但语义盲的坐标搜索器。

### 5.2 `operator_program / hybrid` 的问题

`operator_program / hybrid` 提供了更强的语义表达力，但同时把搜索问题变得更难：

1. **混合搜索空间异构**
   - 连续位置变量与离散动作变量混合；
   - 统一交叉/变异并不天然适配这种语义差异。

2. **算子组合爆炸**
   - `family × component scope × axis × magnitude × slot count` 很快膨胀；
   - 动作槽位数一增加，组合复杂度陡增。

3. **搜索空间割裂**
   - 位置搜索和动作搜索不是同一种地形；
   - 同一代中不同个体可能在完全不同的表型机制上竞争。

4. **投影碎裂与 aliasing**
   - `PlacementContractGuard` 会把大量基因投影到合法边界；
   - 不同基因型可能映射到相同或相近表型；
   - 导致评估预算被花在“不同编码、相近物理状态”的候选上。

5. **静态策略问题**
   - 当前优化器本身不知道：
     - 当前主导违规是什么；
     - 哪类组件正在主导热/质心/结构失败；
     - 下一阶段更该推几何算子、热算子还是结构算子。

因此，当前缺的不是“更多 operator family”，而是：

> 一个能根据运行轨迹、违规模式和预算状态动态控制算子使用方式的上层策略器。

### 5.3 多保真仿真预算问题

当前真实工程闭环同时依赖 `proxy` 和 `COMSOL`，这天然引出三个问题：

- 什么时候应该继续 proxy search。
- 什么时候值得把候选升级到真实 COMSOL。
- 什么时候应当停止高保真调用并回到 cheaper search。

如果没有专门的调度器，传统方法通常会出现：

- 过早上高保真，浪费预算；
- 长时间停留在 cheap proxy，错过真实物理判定；
- 难以系统性优化 `COMSOL_calls_to_first_feasible`。

## 6. LLM 最合理的插入层

本报告推荐只让 LLM 进入“策略层”和“流程控制层”，而不是底层求解层。

### 6.1 插入点 A：搜索前的语义先验生成

输入：

- requirement / BOM
- archetype / semantic zones
- 当前 active constraints
- 当前 search space contract

输出：

- `search_space_mode` 偏置
- operator family prior
- component scope prior
- action slot template
- 初始候选程序或 warm-start seeds

目标：

- 在真正进入 `pymoo` 前，先对混合搜索空间做一次语义裁剪；
- 缩小无意义的组合空间；
- 提升 first-feasible 的起点质量。

### 6.2 插入点 B：搜索中的在线算子策略控制

输入：

- generation summary
- feasible ratio trend
- dominant violation breakdown
- operator usage trace
- contract guard hit reasons
- remaining evaluation budget

输出：

- 下一阶段优先启用的 operator family
- 重点组件子集
- mode bias
- slot count bias
- 值得升格高保真的 candidate shortlist

目标：

- 让 `hybrid/operator_program` 从“静态搜索空间”升级为“trajectory-conditioned operator policy”。

### 6.3 插入点 C：失败反思与多保真调度

输入：

- infeasible diagnosis
- `first_feasible_eval`
- `COMSOL_calls_to_first_feasible`
- proxy-real gap
- shell contact / thermal audit

输出：

- 是否继续 proxy search
- 是否转向另一类 operator family
- 是否需要 bounded relaxation
- 是否对候选做高保真升级

目标：

- 优化高保真预算；
- 提升真实闭环效率；
- 降低无价值 COMSOL 调用。

### 6.4 明确禁止 LLM 越界的内容

LLM 不应直接负责：

- 直接输出最终布局坐标并跳过 `pymoo`
- 跳过 `PlacementContractGuard`
- 跳过 hard constraint contract
- 替代 `proxy / COMSOL` 作为真实性 evaluator

这四条边界必须在论文中写得非常清楚。

## 7. 论文最值得主打的创新点

### 7.1 创新点 1：可验证的语义算子策略控制器

提出一个 **verified operator-policy controller**，让 LLM 输出：

- operator family 排序；
- component scope；
- action template；
- search mode bias；
- fidelity promotion suggestion。

但这些输出必须经过：

- schema validation；
- allowlist filtering；
- screening / cheap proxy checking；
- fallback to deterministic baseline。

这比“LLM 直接出布局”更可信，也更贴合当前实现架构。

### 7.2 创新点 2：面向优化闭环的违规-算子-结果证据图

建议把本地现有 observability 进一步组织成一个正式的方法构件，例如：

- `Violation-Operator-Provenance Graph`
- 或 `Constraint-Operator-Outcome Evidence Graph`

核心节点可包括：

- dominant violation family
- component set
- operator family
- contract guard reason
- proxy outcome
- real outcome
- budget usage

这个图结构有两个价值：

- 让 LLM 的策略生成有明确的结构化输入；
- 让论文的可解释性和 attribution 更强。

### 7.3 创新点 3：反馈感知的多保真仿真调度

把 LLM 从“文本分析器”提升为：

> **multi-fidelity workflow controller**

其核心职责不是预测精确温度值，而是决定：

- 哪些候选值得上 COMSOL；
- 哪些阶段应继续 cheap proxy；
- 哪些失败模式值得触发第二轮 reflective replanning。

这条创新点非常契合当前仓库对以下指标的重视：

- `first_feasible_eval`
- `COMSOL_calls_to_first_feasible`
- `real_feasible`

### 7.4 创新点 4：面向 action-level attribution 的评测协议

当前仓库已经有较强 observability 基础。论文可以进一步把它提升为方法贡献的一部分：

- action-level observability
- contract guard hit attribution
- policy validity / fallback attribution
- real-vs-proxy efficiency attribution

这会使论文结论不只停留在“结果更好”，而是可以回答：

- 为什么更好；
- 哪一类策略起作用；
- 何时起作用；
- 是否只是靠增加高保真预算“堆”出来的改进。

## 8. 推荐的论文叙事逻辑

本报告推荐论文引言和方法主线按以下逻辑组织。

### 8.1 第一层：传统位置搜索稳定但语义盲

- `position_only` 可靠；
- 但只能在连续坐标空间中试错；
- 缺少面向热、结构、电源和任务语义的高阶动作表达。

### 8.2 第二层：混合搜索空间表达更强但也更难搜

- `operator_program / hybrid` 引入了语义动作；
- 但同时造成：
  - 搜索空间割裂；
  - 组合爆炸；
  - contract projection aliasing；
  - 多保真预算难题。

### 8.3 第三层：真正缺的是策略器，不是更多算子

- 仅增加 operator family 不会自动提升效率；
- 真正的缺口是：
  - 如何根据当前失败模式选择合适动作；
  - 如何决定何时改变搜索模式；
  - 如何把昂贵仿真预算花在更值得的候选上。

### 8.4 第四层：LLM 负责策略，MOEA 负责执行，物理求解器负责验真

- LLM 负责策略生成、工作流调度和 reflective control；
- `pymoo` 负责数值搜索；
- `proxy + COMSOL` 负责真实性与多保真闭环。

这是论文最稳的结构。

### 8.5 第五层：最终收益叙事

论文最可信的收益主张，不应优先写成“所有最终目标都更优”，而应优先写成：

- 更快到达 `first feasible`
- 更少 `COMSOL_calls_to_first_feasible`
- 更高 feasible rate / real-feasible rate
- 更低 best CV / AOCC-CV
- 更少无意义 contract-guard 浪费

这组指标更符合当前问题结构，也更容易建立因果解释。

## 9. 整体研究方案

### 9.1 阶段划分

#### Phase S0：冻结基线与可观测口径

目标：

- 固定 baseline；
- 固定场景；
- 固定指标；
- 固定 budget 和 seed protocol。

建议冻结：

- `B0 = position_only + NSGA-II`
- `B1 = hybrid/operator_program + static policy`
- `seed >= 3` 为最低论文门槛；
- 更稳妥建议 `seed >= 5`。

#### Phase S1：离线 LLM 先验

只让 LLM 负责：

- operator family prior
- component scope prior
- search-space warm-start

不做在线控制。

目标：

- 验证 LLM 是否能做 search-space pruning；
- 验证 first-feasible 是否更快。

#### Phase S2：在线 LLM 算子策略控制

引入在线 controller，读取轨迹摘要并动态更新：

- operator family；
- component focus；
- slot bias；
- candidate promotion priority。

目标：

- 证明 LLM 作为 trajectory-conditioned controller 的价值。

#### Phase S3：多保真调度与 reflective replanning

加入 fidelity planner：

- 何时上 COMSOL；
- 何时继续 proxy；
- 何时触发 bounded replanning。

目标：

- 证明方法不仅更会“找解”，也更会“花预算”。

### 9.2 对照实验矩阵

建议至少包含以下组别：

- `B0`: `position_only + NSGA-II`
- `B1`: `hybrid + static operator space + NSGA-II`
- `B2`: `hybrid + heuristic rule controller`
- `B3`: `hybrid + static LLM prior`
- `B4`: `hybrid + online LLM operator policy`
- `B5`: `hybrid + online LLM operator policy + fidelity scheduler`

建议的关键 ablation：

- `B4 - evidence graph`
- `B4 - screening`
- `B5 - fidelity planner`
- `B5 - reflection`

### 9.3 指标体系

建议统一记录：

- `proxy_feasible_rate`
- `real_feasible_rate`
- `first_feasible_eval`
- `COMSOL_calls_to_first_feasible`
- `best_cv`
- `AOCC-CV`
- feasible hypervolume
- `contract_guard_hit_rate`
- `contract_guard_reason_distribution`
- operator family usage distribution
- proxy-real gap

### 9.4 公平对照要求

所有 improvement claim 必须满足：

- matched budget
- 相同 seeds
- 相同 active constraints
- 相同 proxy/real 配置
- 相同场景和 BOM
- 相同 solver family

否则论文中的增益叙事不成立。

## 10. 需要优先建设的系统能力

### 10.1 `LLMOperatorPolicyService`

职责：

- 输入轨迹摘要与违规模式；
- 输出结构化 operator policy。

### 10.2 `TrajectoryDigestBuilder`

职责：

- 将代际轨迹压缩成 LLM 可消费摘要；
- 避免直接把海量原始日志喂给模型。

建议摘要字段：

- dominant violations
- feasible ratio trend
- operator effectiveness
- contract guard reasons
- budget usage
- proxy-real inconsistency

### 10.3 `FidelityPromotionPolicy`

职责：

- 结合硬规则与 LLM policy；
- 决定哪些候选值得升格到 COMSOL。

### 10.4 `PolicyObservabilityContract`

论文级实现必须稳定落盘：

- `policy_prompt_version`
- `policy_inputs_digest`
- `policy_outputs`
- `policy_validation_status`
- `policy_screening_status`
- `policy_fallback_reason`
- `policy_applied_generation`

否则无法做严格 attribution。

## 11. 论文可安全主张与不可过度主张的内容

### 11.1 可安全主张

- LLM 被用于控制而非替代数值优化内核。
- 方法在混合搜索空间中提升了 search efficiency。
- 方法在多保真闭环中提升了 high-fidelity budget efficiency。
- 增益主要体现在：
  - `first_feasible_eval`
  - `COMSOL_calls_to_first_feasible`
  - feasible rate
  - real-feasible rate

### 11.2 不可过度主张

- “LLM replaces NSGA-II”
- “LLM directly generates physically valid layouts”
- “LLM universally outperforms traditional optimizers”
- “operator_program / hybrid 已经在当前系统中稳定获得真实 validated gain”

## 12. 本报告最终建议

本报告最终建议如下：

1. 论文主创新点锁定为：`verified LLM operator-policy controller`。
2. 次创新点锁定为：`feedback-aware multi-fidelity scheduler`。
3. 论文主叙事写成：

> 传统位置搜索稳定但语义盲；混合搜索空间表达更强却更难搜索；LLM 不替代优化器，而是作为语义算子策略器和仿真流程控制器，在合同保护与多保真物理反馈下提升搜索效率与真实可行性闭环效率。

4. 第一阶段实验优先证明：
   - 更快 first-feasible；
   - 更少 COMSOL calls；
   - 更低 CV；
   - 更高 real-feasible efficiency。
5. 在没有 matched-budget、多 seed、strict-real 对照之前，不做“LLM 已全面优于传统方法”的强结论。

## 13. 参考文献与链接

### 优化、OR 与超启发式

- Large Language Models as Optimizers  
  https://openreview.net/forum?id=Bb4VGOWELI
- Chain-of-Experts: When LLMs Meet Complex Operations Research Problems  
  https://openreview.net/forum?id=HobyL1B9CZ
- ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution  
  https://arxiv.org/abs/2402.01145
- OptiBench Meets ReSocratic: Measure and Improve LLMs for Optimization Modeling  
  https://proceedings.iclr.cc/paper_files/paper/2025/hash/3deb687c44d3687ace0729e5db3b4efd-Abstract-Conference.html
- Decision Information Meets Large Language Models: The Future of Explainable Operations Research  
  https://proceedings.iclr.cc/paper_files/paper/2025/hash/a48e5877c7bf86a513950ab23b360498-Abstract-Conference.html

### 科学工具编排与工作流闭环

- Autonomous chemical research with large language models  
  https://www.nature.com/articles/s41586-023-06792-0
- ChemCrow: Augmenting large-language models with chemistry tools  
  https://www.nature.com/articles/s42256-024-00832-8
- Opportunities for retrieval and tool augmented large language models in scientific facilities  
  https://www.nature.com/articles/s41524-024-01423-2
- An automatic end-to-end chemical synthesis development platform powered by large language models  
  https://www.nature.com/articles/s41467-024-54457-x
- Reasoning-agent-driven process simulation, optimization, carbon accounting and decarbonization of distillation  
  https://www.nature.com/articles/s44172-025-00583-3

### 工程设计、调度与仿真相邻工作

- Leveraging large language models for efficient scheduling in Human-Robot collaborative flexible manufacturing systems  
  https://www.nature.com/articles/s44334-025-00061-w
- MASC: Large language model-based multi-agent scheduling chain for flexible job shop scheduling problem  
  https://www.sciencedirect.com/science/article/pii/S1474034625004203
- A Large Language Model-based Multi-Agent Framework to Autonomously Design Algorithms for Earth Observation Satellite Scheduling Problem  
  https://www.sciencedirect.com/science/article/pii/S2095809925006654
- Integrating large models with topology optimization for conceptual design realization  
  https://www.sciencedirect.com/science/article/pii/S1474034625004173
- Development of an intelligent design and simulation aid system for heat treatment processes based on large language model  
  https://www.sciencedirect.com/science/article/pii/S0264127524008815
