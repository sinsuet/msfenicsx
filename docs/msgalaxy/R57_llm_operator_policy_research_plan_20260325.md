# R57 面向 Mass 混合搜索空间的 LLM 算子策略研究报告（2026-03-25）

## 1. 目的

本报告面向 MsGalaxy 当前 `mass` 主线，目标不是泛泛讨论“LLM 是否能做优化”，而是回答下面四个更具体的问题：

- 近三年高质量、真实可考证的工程领域 LLM 论文，哪些与我们当前问题最相关。
- 在当前 `position_only / operator_program / hybrid` 主线上，传统方法真正的瓶颈是什么。
- LLM 最合理的插入层在哪里，应该替代什么、不该替代什么。
- 如何形成一条可信的论文叙事，使“加入 LLM 后优于原有传统方法”成为可验证而非口号化的结论。

本报告以当前仓库已落地实现为边界，不把尚未实现的 `MP-OP-MaaS v3` 目标能力误写成已完成事实。

## 2. 当前系统真相与论文边界

截至 `2026-03-25`，仓库中与本报告相关的真实边界如下：

- 活跃主线仍是 `mass` 单栈 scenario runtime。
- 默认稳定搜索空间仍是 `position_only`。
- `operator_program / hybrid` 已正式接入主线，但生命周期仍是 `experimental`。
- `hybrid` 固定语义已落地为：

```text
position -> operator_program -> PlacementContractGuard projection
```

- `operator_program` 与 `hybrid` 都已经具备单场景真实 COMSOL 链路证据。
- 最新真实成功案例中，代表性动作仍主要是 `cg_recenter`。
- 当前还没有完成 `matched budget + 多 seed + 统计对照`，因此不能宣称：
  - `hybrid` 已稳定优于 `position_only`
  - `operator_program` 已获得 validated gain
  - “LLM 加入后一定更好”

因此，论文设计必须建立在下面这个前提上：

> 当前系统已经具备“可执行的混合搜索空间 + 可观测的算子轨迹 + 可落到真实 COMSOL 的多保真闭环”，但尚未拥有一个上层语义策略器去高效调度这些能力。

这正是 LLM 最适合切入的位置。

## 3. 我们的核心问题不是“能不能加 LLM”，而是“LLM 插哪一层最有价值”

如果把当前系统抽象成三层：

1. **数值搜索层**
   - `NSGA-II / NSGA-III / MOEA/D`
   - 操作对象是数值基因
2. **可执行语义层**
   - `operator_program / hybrid codec`
   - `PlacementContractGuard`
   - `proxy evaluator`
3. **物理真值层**
   - `STEP export`
   - `COMSOL`
   - `field export / audit`

那么 LLM 并不适合直接替代第 1 层和第 3 层：

- 不适合直接替代 `NSGA-II` 去做大规模数值搜索；
- 不适合替代 `proxy/COMSOL` 去充当真实性评估器。

LLM 最适合做的是：

> 作为第 0.5 层或 1.5 层的“语义化算子策略控制器”，基于需求语义、运行轨迹、约束违规分解和多保真反馈，去决定接下来该如何使用搜索空间和算子。

这是本报告推荐的主创新方向。

## 4. 近三年高相关文献调研

下面只保留与我们最相关、且对论文叙事真正有帮助的文献。分为三组：

- A 组：LLM 直接参与优化/进化/超启发式
- B 组：LLM 负责工程工作流、工具编排或结构化设计语言
- C 组：工程设计/仿真中的直接相邻工作

### 4.1 A 组：LLM 直接参与优化

| 文献 | 年份/来源 | 与我们的关系 | 对我们的启发 |
| --- | --- | --- | --- |
| [Large Language Models as Optimizers](https://arxiv.org/abs/2309.03409) | 2023, arXiv | 代表性“LLM 直接做优化”路线 | 说明 LLM 可以做 iterative proposal，但更像高层启发式，不适合作为我们主线数值优化器的直接替代 |
| [Large Language Models to Enhance Bayesian Optimization](https://arxiv.org/abs/2402.03921) | 2024, arXiv | LLM 增强 BO 而非替代 evaluator | 很适合支撑“LLM 做 warm-start / surrogate guidance / candidate proposal”这类增强角色 |
| [LLMs for Bayesian Optimization in Scientific Domains: Are We There Yet?](https://aclanthology.org/2025.findings-emnlp.838/) | 2025, Findings of EMNLP | 重要边界论文 | 直接提醒我们：在科学闭环里，不能轻易假设 LLM 直接做优化就优于传统方法。论文主张应是“增强经典优化”，不是“替代经典优化” |
| [Optimization through In-Context Learning and Iterative LLM Prompting for Nuclear Engineering Design Problems](https://arxiv.org/abs/2503.19620) | 2025, arXiv 预印本 | 高风险工程优化中的 LLM 优化尝试 | 说明在高约束工程问题里，LLM 的 iterative reasoning 具有潜力，但仍需要 evaluator 和解析器闭环 |

#### A 组结论

A 组文献告诉我们两件事：

1. 让 LLM 直接参与优化是可行的；
2. 但在真实科学/工程闭环中，LLM 不应被写成“无条件优于传统优化器”。

因此，我们的论文不宜把创新点写成：

- “LLM 替代 NSGA-II”
- “LLM 直接生成最优卫星布局”

更稳妥的写法是：

- “LLM 作为经典优化器的语义策略增强器”

### 4.2 B 组：LLM 负责工作流、工具编排和结构语言

| 文献 | 年份/来源 | 与我们的关系 | 对我们的启发 |
| --- | --- | --- | --- |
| [AFlow: Automating Agentic Workflow Generation](https://arxiv.org/abs/2410.10762) | 2025, ICLR | 方法学最强支撑之一 | 说明“工作流本身可被优化”，非常适合支撑我们做 `operator policy + fidelity scheduler + reflection loop` |
| [A Solver-Aided Hierarchical Language for LLM-Driven CAD Design](https://arxiv.org/abs/2502.09819) | 2025, CGF / arXiv | 与我们最接近的 CAD/DSL 哲学 | 强烈支持“LLM 不直接出几何，而是输出受约束 DSL，再由 solver 落地”这条路线；与我们的 `operator DSL + contract guard` 高度同构 |
| [An investigation on utilizing large language model for industrial computer-aided design automation](https://www.sciencedirect.com/science/article/pii/S2212827124006656) | 2024, Procedia CIRP | 工业 CAD 自动化近邻工作 | 结论支持 LLM 更适合做计算与流程自动化，不适合无约束几何生成 |
| [ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs](https://arxiv.org/abs/2307.14377) | 2023, arXiv | 通用工具使用方法学 | 支撑 LLM 调用外部工程工具链的能力边界，但不是我们论文的主证据 |

#### B 组结论

B 组文献是本报告最看重的一组，因为它们共同支持一个判断：

> 复杂工程系统里，LLM 的价值常常不在“直接求最优解”，而在“生成结构化语言、调用工具、编排求解工作流、控制多步过程”。

这与我们当前系统的真实技术结构高度吻合。

### 4.3 C 组：工程设计/仿真中的相邻工作

| 文献 | 年份/来源 | 与我们的关系 | 对我们的启发 |
| --- | --- | --- | --- |
| [Large Language Model-assisted Surrogate Modelling for Engineering Optimization](https://www.honda-ri.de/pubs/pdf/5711.pdf) | 2024, IEEE CAI | 工程优化 + surrogate 近邻工作 | 支撑“LLM 可以放在 surrogate/workflow/representation 层”，不必直接替代数值优化器 |
| [LLM2TEA: An Agentic AI Designer for Discovery with Generative Evolutionary Multitasking](https://www.honda-ri.de/pubs/pdf/6442.pdf) | 2025, IEEE Computational Intelligence Magazine | 与我们最接近的 engineering discovery 路线之一 | 支撑“LLM + evolutionary search”的混合范式，是我们论文 narrative 的重要正向参照 |
| [Exploring automated energy optimization with unstructured building data: A multi-agent based framework leveraging large language models](https://www.sciencedirect.com/science/article/pii/S0378778824008077) | 2024, Energy and Buildings | 工程优化工作流近邻 | 支撑“从非结构化工程输入到优化流程编排”的价值，和我们的需求/BOM 到 operator prior 非常接近 |
| [GenAI job scheduling system for solving a flexible job shop scheduling problem](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/508C2D5805370719650FC04B2F514197/S0890060425100152a.pdf/genai_job_scheduling_system_for_solving_a_flexible_job_shop_scheduling_problem.pdf) | 2025, AI EDAM | “LLM orchestration + 传统优化器求解”的强相似工作 | 最能支撑我们的 “LLM 编排 + 传统优化执行” 路线 |
| [A Large Language Model-based Multi-Agent Framework for Analog Circuits' Sizing Relationships Extraction](https://arxiv.org/abs/2506.18424) | 2025, arXiv 预印本 | 与“search-space pruning”最相关的证据 | 文中报告搜索空间可被裁剪到原来的 `1/2.32` 到 `1/26.6`，非常适合支撑我们关于“混合搜索空间爆炸”的论证 |
| [iDesignGPT enhances conceptual design via large language model agentic workflows](https://www.nature.com/articles/s41467-026-68672-1) | 2026, Nature Communications | 超前但相关的工程 agentic design 工作 | 支撑“agentic workflow + domain tool integration”优于单次静态 prompting 的总体方向 |

#### C 组结论

C 组告诉我们：

- 工程领域已经出现一批“LLM 不直接替代求解器，而是嵌入工程工作流”的高质量工作；
- 但据我们当前调研，还没有看到一篇与我们完全同构的工作，即：
  - 混合离散-连续 operator search space
  - contract-safe projection
  - multi-fidelity proxy + COMSOL real feedback
  - action-level observability
  - LLM policy controller

这说明我们的创新空间是真实存在的。

## 5. 当前传统方法真正的问题是什么

结合仓库现状，当前“传统方法”至少包含两种基线：

- `position_only + NSGA-II`
- `hybrid/operator_program + static NSGA-II`

这两类基线各有问题。

### 5.1 `position_only` 的问题

`position_only` 的优点是稳定，但它存在明显的表达力瓶颈：

- 只能在坐标空间中搜索；
- 很难表达非几何设计动作；
- 无法直接表达组件间热连接、结构附体等离散拓扑变化；
- 缺少“成组移动”“按语义推离 keep-out”“向中心重排重件”等高阶动作偏置。

因此，`position_only` 更像是：

> 一个稳定但语义盲的坐标搜索器。

### 5.2 `hybrid/operator_program` 的问题

`hybrid/operator_program` 虽然补上了表达力，但也带来新的复杂性：

1. **搜索空间异构**
   - 前半段是连续位置变量；
   - 后半段是离散动作选择 + 连续参数；
   - 用统一数值交叉/变异处理时，语义不完全对齐。

2. **算子组合爆炸**
   - `action family × component selection × axis × magnitude × slot count`
   - 随着 slot 数增加，组合空间迅速膨胀。

3. **投影碎裂**
   - `PlacementContractGuard` 会把大量候选投影回合法边界；
   - 多个不同基因可能映射到同一个实际状态；
   - 搜索地形会变得碎片化、非平滑。

4. **静态策略问题**
   - 当前优化器并不知道：
     - 当前主导失败是热还是 CG；
     - 是 mission keep-out 还是 mount axis lock；
     - 应该优先启用几何动作还是结构/热动作。
   - 因此算子使用策略本质上仍是“静态的”。

5. **多保真预算问题**
   - proxy 便宜但不等于 real；
   - COMSOL 代价高；
   - 当前没有一个智能控制器决定“哪些候选值得上真实求解”。

因此，当前系统真正缺的不是“更多算子”，而是：

> 一个能根据需求语义、运行轨迹、违规分解和预算状态，动态调度搜索空间与算子的高层策略器。

## 6. LLM 最合理的插入层

基于上述文献和系统现状，本报告推荐把 LLM 插在下面三个位置。

### 6.1 插入点 A：初始化前的语义先验生成

输入：

- requirement
- BOM
- semantic zones
- active constraints
- archetype / task-face 信息

输出：

- `search_space_mode` 初始偏置
- operator family prior
- component scope prior
- action slot template
- 初始 seed programs

目标：

- 在真正开始 `NSGA-II` 之前，对混合搜索空间做一次语义裁剪和 warm-start。

这一层最容易落地，也最适合作为第一阶段论文结果。

### 6.2 插入点 B：搜索中的在线算子策略控制

输入：

- generation records
- feasible ratio
- best CV curve
- dominant violation breakdown
- operator usage trace
- contract guard hit reasons
- proxy-real gap
- 剩余评估预算

输出：

- 下一阶段应优先启用的 operator family
- 重点组件子集
- action slot 数和模板
- mode bias：更偏 `position_only` 还是 `hybrid`
- promotion candidate：哪些候选值得上 COMSOL

目标：

- 让搜索从“静态 operator space”变成“trajectory-conditioned operator policy”。

这一层是本报告推荐的**论文主创新点**。

### 6.3 插入点 C：失败反思与多保真调度

输入：

- infeasible diagnosis
- first-feasible statistics
- COMSOL call budget
- proxy-real inconsistency
- shell contact / component thermal audit

输出：

- 是否应继续 proxy search
- 是否应升格到 real COMSOL
- 是否应转向另一类 operator family
- 是否应做 bounded relaxation

目标：

- 减少无价值 COMSOL 调用；
- 提高 `COMSOL_calls_to_first_feasible` 的效率。

这一层是很强的工程创新点，但建议放在第二阶段推进。

## 7. 本报告推荐的主创新点

### 7.1 不推荐的创新点写法

下面这几种写法风险很高，不建议作为论文主张：

- “LLM 直接替代 NSGA-II 做卫星布局优化”
- “LLM 直接生成最终可行布局”
- “LLM 比传统多目标优化器更强”

原因：

- 文献并不稳定支持这种强替代叙事；
- 当前仓库实现也不适合这样主张；
- 容易被 reviewer 追问泛化性、数值稳定性和科学真实性。

### 7.2 推荐的主创新点写法

本报告推荐的主创新点是：

> **LLM-guided semantic operator policy for contract-safe hybrid satellite layout optimization under multi-fidelity physics feedback**

中文可表述为：

> **面向合同安全与多保真物理反馈的 LLM 语义算子策略卫星布局优化**

这一定义的关键点有四个：

1. `LLM-guided`
   - LLM 是高层策略器，不是底层数值求解器。

2. `semantic operator policy`
   - LLM 输出的是算子策略、组件范围、动作模板、模式偏置，而不是直接输出最终坐标。

3. `contract-safe hybrid optimization`
   - 系统始终受 `PlacementContractGuard` 和场景合同保护。

4. `multi-fidelity physics feedback`
   - 最终闭环基于 `proxy + COMSOL`，而不是纯文本自洽。

## 8. 论文叙事建议

本报告建议的论文叙事逻辑如下。

### 8.1 第一段：传统坐标搜索的局限

- 传统 `position_only` 搜索稳定，但只能在坐标空间中试错；
- 它缺乏面向热、结构、电源、任务语义的高层动作表达。

### 8.2 第二段：混合搜索空间虽然更强，但更难搜

- `hybrid/operator_program` 提供了更强的表达力；
- 但同时引入：
  - 离散-连续混合空间；
  - 动作组合爆炸；
  - contract projection aliasing；
  - 多保真预算约束。

### 8.3 第三段：缺口不在算子数量，而在策略调度

- 仅把更多算子接进来，并不能自动提升效率；
- 真正缺的是：
  - 如何根据当前失败模式选择合适算子；
  - 如何动态调整搜索子空间；
  - 如何决定何时值得升级到高保真仿真。

### 8.4 第四段：LLM 负责语义控制，传统优化器负责执行

- LLM 不直接替代 `NSGA-II`；
- LLM 读需求、读轨迹、读违规分解，然后产出 operator policy；
- `NSGA-II` 仍然负责联合基因搜索；
- `proxy + COMSOL` 仍然负责物理真值闭环。

### 8.5 第五段：最终增益叙事

如果实验成立，论文可以主张：

- 更快达到 `first feasible`
- 更少 COMSOL 调用
- 更低 AOCC-CV
- 更高 real-feasible rate
- 更低 contract_guard 浪费

而不是一上来主张：

- 所有目标值都全面优于传统方法

前者更可信，也更容易通过评审。

## 9. 实验设计建议

### 9.1 对照组

建议至少做以下 baseline：

1. `B0`: `position_only + NSGA-II`
2. `B1`: `hybrid + static operator space + NSGA-II`
3. `B2`: `hybrid + heuristic rule controller`
4. `B3`: `hybrid + static LLM prior`
5. `B4`: `hybrid + online LLM operator policy`
6. `B5`: `hybrid + online LLM operator policy + fidelity scheduler`

### 9.2 指标

建议统一记录：

- `proxy_feasible_rate`
- `real_feasible_rate`
- `first_feasible_eval`
- `COMSOL_calls_to_first_feasible`
- `AOCC-CV`
- `best_feasible_objective_curve`
- feasible hypervolume
- `contract_guard_hit_rate`
- `contract_guard_reason_distribution`
- operator family usage entropy
- proxy-real gap

### 9.3 公平对照原则

必须满足：

- matched budget
- 相同种子集
- 相同 active constraints
- 相同 proxy/real fidelity 设置
- 相同场景/BOM

建议：

- `seed >= 5` 起步
- 更稳妥的是 `seed >= 10`

### 9.4 分层实验推进

#### Phase P0：最小可发表结果

- 只做 `static LLM prior`
- 不做 online control

目标：

- 证明 LLM 能做 search-space pruning / warm-start
- 证明 first-feasible 更快

#### Phase P1：主创新版本

- 加入 `online operator policy`

目标：

- 证明 LLM 作为 trajectory-conditioned controller 的价值

#### Phase P2：多保真版本

- 加入 `fidelity scheduler`

目标：

- 证明在真实 COMSOL 预算下更高效

## 10. 需要新增的系统能力

为了支撑论文，本报告建议新增以下模块。

### 10.1 `LLMOperatorPolicyService`

职责：

- 输入运行时诊断
- 输出 operator priors / component scope / slot templates / mode bias

### 10.2 `TrajectoryDigestBuilder`

职责：

- 将代际轨迹压缩为 LLM 可消费摘要
- 避免把原始日志全部喂给模型

摘要内容建议包括：

- dominant violations
- feasible ratio trend
- operator effectiveness
- contract_guard reasons
- budget usage

### 10.3 `FidelityPromotionPolicy`

职责：

- 结合 LLM 建议与硬阈值规则
- 决定哪些候选值得升格到 COMSOL

### 10.4 `PolicyObservabilityContract`

必须稳定落盘：

- `policy_prompt_version`
- `policy_decision_id`
- `policy_inputs_digest`
- `policy_outputs`
- `policy_confidence`
- `policy_applied_generation`
- `policy_trigger_reason`

否则论文无法做 attribution。

## 11. 论文可主张的贡献点

如果后续实验完成，本报告建议把论文贡献点收敛为下面三条。

### C1. 语义算子策略控制器

提出一个 LLM-guided semantic operator policy，使 LLM 负责：

- 选择 operator family
- 限定作用组件范围
- 决定 action template
- 动态调节搜索模式

而经典 MOEA 继续负责数值执行。

### C2. 合同安全的混合搜索空间控制

在离散-连续混合搜索空间中，引入：

- `operator_program / hybrid`
- `PlacementContractGuard`
- action-level observability

使 LLM 产生的策略不直接越过工程合同边界。

### C3. 面向真实仿真预算的多保真调度

将 LLM 从“文本解释器”提升为“多保真工作流调度器”，以提升：

- first-feasible efficiency
- COMSOL 使用效率
- real-feasible 闭环收益

## 12. 不应过度主张的内容

论文中必须避免以下过度表述：

- “LLM replaces NSGA-II”
- “LLM directly generates physically valid layouts”
- “LLM universally outperforms traditional optimizers”
- “operator_program / hybrid 已在当前系统中稳定获得真实增益”

当前更诚实的表述应是：

- 当前系统已经具备混合搜索空间和真实物理闭环；
- LLM 的目标是提升策略效率，而不是替代底层物理与数值优化；
- 增益必须通过 matched-budget、多 seed、proxy/real 双层对照来证明。

## 13. 本报告最终建议

本报告最终建议如下：

1. **主创新点** 选 `LLM-guided semantic operator policy`
2. **次创新点** 选 `multi-fidelity scheduler`
3. **不把** “LLM 直接出布局” 作为主创新
4. **不把** “LLM 替代 NSGA-II” 作为主创新
5. **第一阶段实验目标** 优先证明：
   - 更快 first-feasible
   - 更少 COMSOL calls
   - 更低 AOCC-CV
6. **最终论文主叙事** 写成：

> 传统坐标搜索表达力有限；混合搜索空间表达力更强但也更难搜索；LLM 不替代优化器，而是作为语义化算子策略器，在合同保护和多保真物理反馈下提升搜索效率与真实可行性闭环表现。

## 14. 参考文献与链接

### 方法学与优化

- Large Language Models as Optimizers  
  https://arxiv.org/abs/2309.03409
- Large Language Models to Enhance Bayesian Optimization  
  https://arxiv.org/abs/2402.03921
- LLMs for Bayesian Optimization in Scientific Domains: Are We There Yet?  
  https://aclanthology.org/2025.findings-emnlp.838/
- AFlow: Automating Agentic Workflow Generation  
  https://arxiv.org/abs/2410.10762

### 工程设计 / CAD / 工作流

- A Solver-Aided Hierarchical Language for LLM-Driven CAD Design  
  https://arxiv.org/abs/2502.09819
- An investigation on utilizing large language model for industrial computer-aided design automation  
  https://www.sciencedirect.com/science/article/pii/S2212827124006656
- GenAI job scheduling system for solving a flexible job shop scheduling problem  
  https://www.cambridge.org/core/services/aop-cambridge-core/content/view/508C2D5805370719650FC04B2F514197/S0890060425100152a.pdf/genai_job_scheduling_system_for_solving_a_flexible_job_shop_scheduling_problem.pdf
- Exploring automated energy optimization with unstructured building data: A multi-agent based framework leveraging large language models  
  https://www.sciencedirect.com/science/article/pii/S0378778824008077

### 与工程优化更接近的相邻工作

- Large Language Model-assisted Surrogate Modelling for Engineering Optimization  
  https://www.honda-ri.de/pubs/pdf/5711.pdf
- LLM2TEA: An Agentic AI Designer for Discovery with Generative Evolutionary Multitasking  
  https://www.honda-ri.de/pubs/pdf/6442.pdf
- A Large Language Model-based Multi-Agent Framework for Analog Circuits' Sizing Relationships Extraction  
  https://arxiv.org/abs/2506.18424
- Optimization through In-Context Learning and Iterative LLM Prompting for Nuclear Engineering Design Problems  
  https://arxiv.org/abs/2503.19620
- iDesignGPT enhances conceptual design via large language model agentic workflows  
  https://www.nature.com/articles/s41467-026-68672-1
