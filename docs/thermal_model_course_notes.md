# 二维稳态多组件导热模型课程讲义

## 摘要

本讲义围绕当前仓库中的二维稳态多组件导热教学案例展开，目标是把“数学模型”“有限元离散”“FEniCSx 代码实现”和“LLM 驱动优化闭环”放到同一条主线上说明清楚。本文档以 `states/baseline_multicomponent.yaml` 为基准案例，以 `src/compiler/` 下的求解器实现为核心，对控制方程、界面条件、弱形式、离散矩阵结构、材料定义、边界条件和优化变量约束进行系统梳理。

本讲义强调两点：

1. 当前模型是一个带 SI 风格单位语义的教学型二维稳态热模型，而不是面向工程签核的高保真封装热模型。
2. 当前仓库的核心价值不只是“解一个稳态导热方程”，而是把结构化状态、有限元求解、约束评估、提案校验和 LLM 优化闭环连接成了一个可复盘、可扩展的系统。

---

## 1. 问题背景与教学目标

### 1.1 问题背景

当前案例研究的是一个二维截面上的多组件稳态导热问题。设计对象由三个矩形组件组成：

- 底板 `base_plate`
- 芯片 `chip`
- 热扩展块 `heat_spreader`

在这个模型中，芯片内部存在等效体热源，热量通过芯片、底板和热扩展块在结构内部传导，并最终通过左右两侧冷边界带走。该问题适合用于讲解：

- 分区材料导热问题如何建模
- 不同材料导热率如何进入 PDE
- 热源和边界条件如何影响温度场
- 有限元弱形式如何从控制方程推导而来
- 状态驱动建模与自动优化闭环如何组织

### 1.2 教学目标

通过本讲义，读者应当能够回答以下问题：

1. 当前仓库中的物理模型究竟是什么。
2. 每个状态字段对应什么几何或物理含义。
3. 稳态热传导方程如何推导出有限元弱形式。
4. 代码中哪些函数分别负责几何构造、网格标记、材料赋值、方程装配和结果评估。
5. 当前 LLM 闭环优化究竟在“改什么”，以及为什么它不是直接改 Python 脚本。

---

## 2. baseline 案例与状态定义

### 2.1 状态文件的位置与作用

当前基准案例定义在：

- `states/baseline_multicomponent.yaml`

该文件是整个系统的唯一设计事实来源。它同时描述：

- 几何布局
- 材料参数
- 热源
- 边界条件
- 网格控制参数
- 求解器类型
- 约束与目标
- 单位与参考工况

对应的 Python 数据结构定义在：

- `src/thermal_state/schema.py`
- `src/thermal_state/load_save.py`

其中 `ThermalDesignState` 是最核心的总状态对象。

### 2.2 baseline 的几何与材料参数

当前 `baseline_multicomponent.yaml` 中的参数如下。

#### 设计域

```text
x0 = 0.0
y0 = 0.0
width = 1.2
height = 0.5
```

#### 组件

| 组件 | 左下角 `(x0, y0)` | 尺寸 `(width, height)` | 材料 |
| --- | --- | --- | --- |
| `base_plate` | `(0.0, 0.0)` | `(1.2, 0.2)` | `base_material` |
| `chip` | `(0.45, 0.2)` | `(0.3, 0.12)` | `chip_material` |
| `heat_spreader` | `(0.25, 0.32)` | `(0.7, 0.1)` | `spreader_material` |

#### 材料导热率

| 材料名 | 导热率 `k` |
| --- | --- |
| `base_material` | `12.0 W/(m*K)` |
| `chip_material` | `45.0 W/(m*K)` |
| `spreader_material` | `90.0 W/(m*K)` |

#### 热源

- 在 `chip` 上施加等效体热源 `15000.0 W/m^3`

#### 边界条件

- 左边界：`T = 25 degC`
- 右边界：`T = 25 degC`
- 其余边界：零通量

#### 约束

- `chip_max_temperature <= 85 degC`

### 2.3 单位与教学语义

状态文件中显式保存了：

```text
length: m
temperature: degC
conductivity: W/(m*K)
heat_source: W/m^3
```

这意味着当前案例不再是旧版本中无量纲风格的热问题，而是一个带 SI 风格语义的教学模型。需要强调的是，这里的“工程语义”主要用于解释一致性，不代表当前参数已经完成真实封装级校准。

---

## 3. 物理模型与材料定义

### 3.1 温度场与材料场

设总求解区域为

$$
\Omega = \Omega_{\mathrm{base}} \cup \Omega_{\mathrm{chip}} \cup \Omega_{\mathrm{spreader}}.
$$

其中：

- $\Omega_{\mathrm{base}}$ 表示底板区域
- $\Omega_{\mathrm{chip}}$ 表示芯片区域
- $\Omega_{\mathrm{spreader}}$ 表示热扩展块区域

在当前模型中，导热率是分区常数场：

$$
k(x)=
\begin{cases}
k_{\mathrm{base}}, & x \in \Omega_{\mathrm{base}}, \\
k_{\mathrm{chip}}, & x \in \Omega_{\mathrm{chip}}, \\
k_{\mathrm{spreader}}, & x \in \Omega_{\mathrm{spreader}}.
\end{cases}
$$

代码中这一思想的落点是：

- `src/compiler/geometry_builder.py::state_to_component_layout`
- `src/compiler/physics_builder.py::build_problem`

### 3.2 热源定义

热源也是分区常数场：

$$
q(x)=
\begin{cases}
q_{\mathrm{chip}}, & x \in \Omega_{\mathrm{chip}}, \\
0, & x \notin \Omega_{\mathrm{chip}}.
\end{cases}
$$

其中当前 baseline 使用：

$$
q_{\mathrm{chip}} = 15000.0\ \mathrm{W/m^3}.
$$

这不是从真实器件三维封装功率严格反推得到的热源，而是教学用的等效体热源。若引入厚度 $t_z$，并把当前二维截面解释为一块厚度均匀的三维挤出体，则总功率满足：

$$
P = q_{\mathrm{chip}} \cdot |\Omega_{\mathrm{chip}}| \cdot t_z.
$$

当前状态中并未单独存储 $t_z$，因此这个模型更适合理解“热源强度如何影响热点温度”，而不是直接用于真实芯片功率标定。

### 3.3 材料定义的物理含义

当前 `MaterialState` 只包含一个标量：

- `conductivity`

因此当前仓库中的材料模型默认满足以下假设：

1. 材料各向同性。
2. 导热率与温度无关。
3. 同一组件内部导热率为常数。
4. 组件之间不存在单独建模的界面热阻。

这意味着：

- `base_material`、`chip_material`、`spreader_material` 更应理解为等效材料区，而不是完整的真实材料卡。
- 当前模型尚未包含接触热阻、层间热阻、对流换热和辐射换热。

---

## 4. 控制方程、边界条件与界面条件

### 4.1 强形式控制方程

当前模型求解的是二维稳态热传导方程：

$$
-\nabla \cdot (k \nabla T) = q \quad \text{in } \Omega.
$$

其中：

- $T(x)$ 是温度场
- $k(x)$ 是导热率场
- $q(x)$ 是体热源场

### 4.2 边界条件

设左右冷边界分别为 $\Gamma_L$ 与 $\Gamma_R$，其余外边界为 $\Gamma_N$，则：

$$
T = 25 \quad \text{on } \Gamma_L \cup \Gamma_R,
$$

$$
-k \nabla T \cdot n = 0 \quad \text{on } \Gamma_N.
$$

这里第二个条件表示绝热边界，也可解释为零法向热流边界。

### 4.3 界面条件

若两个子区域在内部界面 $\Gamma_{ij}$ 上相接，则在理想连续接触假设下应满足：

$$
[T]_{\Gamma_{ij}} = 0,
$$

$$
[k \nabla T \cdot n]_{\Gamma_{ij}} = 0.
$$

前者表示温度连续，后者表示法向热流连续。当前代码并未显式写出界面条件，而是通过：

- 共享网格接口
- 全局连续的温度有限元空间
- 弱形式整体装配

自动满足这些条件。

---

## 5. 从强形式到弱形式的推导

### 5.1 乘测试函数并积分

取测试函数 $v$，对控制方程两边乘以 $v$ 并在 $\Omega$ 上积分：

$$
\int_{\Omega} \left[-\nabla \cdot (k \nabla T)\right] v \, d\Omega
=
\int_{\Omega} q v \, d\Omega.
$$

### 5.2 分部积分

对左侧做分部积分：

$$
\int_{\Omega} k \nabla T \cdot \nabla v \, d\Omega
-
\int_{\partial \Omega} (k \nabla T \cdot n) v \, d\Gamma
=
\int_{\Omega} q v \, d\Omega.
$$

### 5.3 边界项处理

在 Dirichlet 边界上，测试函数满足 $v=0$；在绝热边界上，满足 $k \nabla T \cdot n = 0$。因此边界项消失，得到弱形式：

$$
\int_{\Omega} k \nabla T \cdot \nabla v \, d\Omega
=
\int_{\Omega} q v \, d\Omega.
$$

更严格地说，应写为：

求 $T \in V_g$，使得对任意 $v \in V_0$，有

$$
a(T, v) = L(v),
$$

其中

$$
a(T, v) = \int_{\Omega} k \nabla T \cdot \nabla v \, d\Omega,
$$

$$
L(v) = \int_{\Omega} q v \, d\Omega.
$$

### 5.4 与代码的直接对应

在 `src/compiler/physics_builder.py` 中，最核心的两行是：

```python
a = conductivity * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
L = heat_source * v * ufl.dx
```

这正是上述弱形式在 UFL 中的直接表达。

---

## 6. 有限元离散与矩阵形式

### 6.1 离散空间

当前代码中温度场和参数场的离散选择为：

- 温度场：`Lagrange P1`
- 材料场：`DG0`
- 热源场：`DG0`

在 `src/compiler/physics_builder.py` 中对应：

```python
V = fem.functionspace(domain, ("Lagrange", 1))
DG0 = fem.functionspace(domain, ("DG", 0))
```

其含义是：

1. 温度在节点上连续，在每个单元内线性变化。
2. 导热率和热源在每个单元内是常数。

### 6.2 基函数展开

设温度离散解写为

$$
T_h(x) = \sum_{j=1}^{N} U_j \phi_j(x),
$$

其中 $\phi_j$ 是 `P1` 基函数，$U_j$ 是待求节点温度系数。

将其代入弱形式，并令测试函数取同一组基函数，可得线性系统：

$$
A U = b,
$$

其中

$$
A_{ij} = \int_{\Omega} k_h \nabla \phi_j \cdot \nabla \phi_i \, d\Omega,
$$

$$
b_i = \int_{\Omega} q_h \phi_i \, d\Omega.
$$

这里的 $k_h$ 和 $q_h$ 是分片常数近似。

### 6.3 分区装配的含义

由于 $k_h$ 和 $q_h$ 按单元标签赋值，因此可把整体积分理解为各组件区域积分之和：

$$
A_{ij}
=
\sum_{m \in \{\mathrm{base},\mathrm{chip},\mathrm{spreader}\}}
\int_{\Omega_m} k_m \nabla \phi_j \cdot \nabla \phi_i \, d\Omega,
$$

$$
b_i
=
\int_{\Omega_{\mathrm{chip}}} q_{\mathrm{chip}} \phi_i \, d\Omega.
$$

因此，材料变化本质上就是在刚度矩阵不同区域的积分权重发生变化；热源变化则体现在右端项大小变化。

---

## 7. 核心代码实现解析

### 7.1 状态层：`thermal_state`

核心文件：

- `src/thermal_state/schema.py`
- `src/thermal_state/load_save.py`

主要职责：

1. 用 dataclass 固化状态结构。
2. 从 YAML 读入状态。
3. 把当前轮状态写回 `state.yaml` 或 `next_state.yaml`。

在教学上，这一层的意义是把“几何、材料、热源、边界条件、约束”从 Python 逻辑中剥离出来，转为结构化设计状态。

### 7.2 几何布局层：`geometry_builder`

核心文件：

- `src/compiler/geometry_builder.py`

其中 `state_to_component_layout(state)` 做了三件关键事情：

1. 根据 `state.components` 读取所有矩形组件。
2. 根据 `component.material` 找到对应导热率。
3. 根据 `heat_sources` 查出每个组件上的热源值。

最终每个组件被组织成 `ComponentRect`，并附带：

- 几何尺寸
- 组件名称
- 标签编号
- 导热率
- 热源

这是后续网格与物理装配的中间桥梁。

### 7.3 网格与物理组标记：`mesh_builder`

核心文件：

- `src/compiler/mesh_builder.py`

其处理流程如下：

1. 用 gmsh 为每个组件建立矩形几何。
2. 用 `fragment` 让不同矩形共享接口。
3. 通过子区域质心判断当前碎片属于哪个组件。
4. 为每个子区域建立 2D physical group。
5. 找到最左和最右边界曲线，分别标记为冷边界。
6. 生成二维三角网格，再转为 dolfinx 的 mesh 数据结构。

需要特别指出两个实现细节。

第一，当前 PDE 的实际求解域是“组件并集”，不是 `design_domain` 整个矩形。这一点可以从 `mesh_builder.py` 只为组件建矩形而不为 `design_domain` 建整块背景域看出来。

第二，`mesh.nx` 和 `mesh.ny` 当前只用于计算目标网格尺寸：

$$
h = \min\left(\frac{W}{n_x}, \frac{H}{n_y}\right),
$$

其中 $W$ 和 $H$ 是当前组件并集的总宽高。它们不是结构化网格意义下的最终单元数。

### 7.4 物理场赋值与方程装配：`physics_builder`

核心文件：

- `src/compiler/physics_builder.py`

这里最重要的实现步骤是：

1. 创建温度空间 `V` 与分片常数空间 `DG0`。
2. 创建 `conductivity` 和 `heat_source` 两个 `fem.Function(DG0)`。
3. 用 `cell_tags.find(component.label)` 找到属于每个组件的单元。
4. 把相应单元上的导热率和热源值写入数组。
5. 找到左右边界自由度。
6. 构造 Dirichlet 边界条件。
7. 定义弱形式 `a` 与 `L`。
8. 用 `LinearProblem` 生成线性求解问题。

这里还有一个值得课堂强调的点：状态文件虽然有 `boundary_conditions: neumann / others / 0.0`，但代码并没有显式写一个 Neumann 边界积分项。这不是遗漏，而是因为“其余边界为零通量”正好对应弱形式中的自然边界条件，默认边界项为零即可。

### 7.5 求解与单轮运行：`single_run`

核心文件：

- `src/compiler/solver_runner.py`
- `src/compiler/single_run.py`

`solver_runner.py` 的 `solve_steady_heat(problem)` 直接调用 `problem.solve()`。

`single_run.py` 则负责把完整单轮串起来：

1. 读取状态。
2. 构造布局。
3. 生成网格。
4. 装配 PDE。
5. 求解温度场。
6. 导出图片、HTML、XDMF 和汇总文本。
7. 返回结构化 `metrics`。

这一步是整个求解链的实际入口。`examples/02_multicomponent_steady_heat.py` 就是对这一层的薄封装。

### 7.6 后处理与指标汇总：`msfenicsx_viz` 与 `evaluator`

核心文件：

- `src/msfenicsx_viz.py`
- `src/evaluator/constraints.py`
- `src/evaluator/objectives.py`
- `src/evaluator/report.py`

其中：

- `summarize_solution_by_component(...)` 会对每个组件提取 `count/min/max/mean`
- `extract_metric_value(...)` 会把 `chip_max_temperature` 这类指标名映射到结构化结果
- `evaluate_case(...)` 会生成：
  - `feasible`
  - `violations`
  - `objective_summary`
  - `priority_actions`

这是从“求得温度场”迈向“自动判断设计是否达标”的关键一步。

---

## 8. baseline 结果及其物理解释

### 8.1 当前结果

`outputs/02_multicomponent_steady_heat/data/summary.txt` 给出了当前 baseline 的主要结果：

- `temperature_min = 25.000000 degC`
- `temperature_max = 89.301304 degC`
- `base_plate max = 87.804790 degC`
- `chip max = 89.301304 degC`
- `heat_spreader max = 89.301304 degC`

约束是：

$$
T_{\mathrm{chip,max}} \le 85\ \mathrm{degC},
$$

因此当前 baseline 不可行。

### 8.2 为什么热点出现在芯片及其上方

从物理上看，这一结果符合直觉：

1. 芯片内部存在唯一的体热源，因此它是温升的直接来源。
2. 热扩展块虽然导热率更高，但它位于芯片上方，承担的是铺展热量的作用，而不是主动降温的无限冷源。
3. 左右两侧边界被固定在 `25 degC`，因此热量需要通过底板和扩展块逐步传到左右两侧。

### 8.3 为什么 `chip` 和 `heat_spreader` 的最大温度相同

从数值实现看，这并不奇怪。当前温度场用的是全局连续 `P1` 空间，组件接口处共享节点。后处理时，组件温度统计是按组件所属单元的自由度集合抽取的，因此接口上的共享节点值会同时出现在相邻组件的统计里。

因此：

- `chip max` 与 `heat_spreader max` 相同

并不表示两个区域内部处处等温，而是说明离散热点恰好出现在二者共享接口附近的某个自由度位置。

---

## 9. LLM 驱动优化闭环的实现原理

### 9.1 为什么不是直接让模型改代码

当前系统的核心设计是：

```text
Design State -> Compiler/Runner -> Evaluator -> LLM Proposal -> Validator -> Next State
```

这意味着模型修改的是结构化状态，而不是 Python 脚本。这样做有三个重要优点：

1. 每轮输入输出都可复现。
2. 每轮变更都能被精确校验。
3. 非法提案可以被拦截并记录原因。

### 9.2 允许修改哪些变量

变量注册表定义在：

- `src/optimization/variable_registry.py`

当前开放的变量包括：

- `materials.spreader_material.conductivity`
- `materials.base_material.conductivity`
- `components.2.width`
- `components.2.height`
- `components.2.x0`
- `components.2.y0`
- `heat_sources.0.value`

这说明当前优化关注的是：

- 热扩展能力
- 热流下游抽热能力
- 热扩展块几何尺度与位置
- 负载场景变化

### 9.3 提案合法性约束

提案校验在：

- `src/validation/bounds.py`
- `src/validation/geometry.py`
- `src/validation/proposals.py`

其核心约束包括：

1. 导热率上界和下界。
2. 单步导热率变化比限制。
3. 尺寸必须为正。
4. 尺寸单步变化比限制。
5. 位置单步移动限制。
6. 组件不能重叠。
7. 组件不能超出 `design_domain`。

这里必须再次强调一个工程细节：

- `design_domain` 在当前实现中主要服务于提案合法性检查，不直接参与 PDE 求解域构造。

### 9.4 优化循环的运行逻辑

总控位于：

- `src/orchestration/optimize_loop.py`

每一轮都会保存：

- `state.yaml`
- `evaluation.json`
- `proposal.json`
- `proposal_validation.json`
- `decision.json`
- `next_state.yaml`
- `outputs/`

因此该系统不是一次性黑盒优化，而是可追溯的轮次式工程闭环。

---

## 10. 模型假设、局限与扩展方向

### 10.1 当前假设

当前教学案例默认采用如下假设：

1. 二维稳态。
2. 各向同性、常数导热率。
3. 芯片热源为等效体热源。
4. 左右边界固定温度，其余边界绝热。
5. 组件界面理想接触，无界面热阻。
6. 无对流、无辐射、无瞬态项。

### 10.2 当前局限

因此，该模型当前更适合用于：

- 有限元入门
- 组件级热路径理解
- 约束驱动设计演示
- LLM 辅助优化流程教学

而不适合直接用于：

- 真实产品热认证
- 工艺签核
- 精确封装热阻提取
- 瞬态热冲击评估

### 10.3 后续扩展方向

如果要继续提升物理真实性，可按以下顺序扩展：

1. 引入对流边界条件。
2. 引入界面热阻。
3. 引入温度相关材料参数。
4. 从器件功率和厚度更严格地反推热源。
5. 引入瞬态项，求解非稳态升温过程。
6. 把二维截面扩展到更接近真实封装的三维模型。

---

## 11. 教学总结

从课程讲授角度看，当前仓库的核心知识链条可以概括为：

1. 用结构化状态描述组件导热问题。
2. 用 gmsh 建立多组件共享接口的二维网格。
3. 用分片常数导热率与热源场构造稳态导热方程。
4. 用 FEniCSx 把弱形式离散成线性系统。
5. 用组件级指标把“温度场结果”翻译成“设计是否可行”。
6. 用变量注册表与校验器把优化搜索限制在可解释、可控的空间里。
7. 用 LLM 生成结构化设计修改提案，形成自动化闭环。

因此，这个项目最适合作为“从 PDE 到有限元代码，再到自动设计闭环”的综合教学案例。

---

## 附：课堂讲解建议顺序

若将本案例用于授课或组会报告，建议按以下顺序展开：

1. 先展示 `states/baseline_multicomponent.yaml`，让学生理解几何、材料、热源和边界条件。
2. 再讲强形式控制方程与界面条件，明确问题属于哪类 PDE。
3. 随后推导弱形式，解释为什么绝热边界在当前实现中不需要单独写边界积分项。
4. 接着讲 `P1 + DG0` 的离散思想，以及它在代码中的具体落点。
5. 最后再讲 `evaluator`、`validator` 与 `optimize_loop`，说明为什么这个仓库已经不仅仅是一个“求解脚本”。

对课堂来说，这样的顺序比一开始直接读代码更容易建立整体理解。
