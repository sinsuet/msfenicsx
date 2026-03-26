# 辐射散热数据生成器

基于 FEniCSx 的热仿真数据生成工具，用于生成带有非线性辐射边界条件的二维热传导问题数据集。

## 项目简介

本项目实现了一个可配置的数据生成器，用于生成电子元件布局的热仿真数据。支持：
- 多种元件形状（矩形、圆形、胶囊形）
- 非线性辐射边界条件（Stefan-Boltzmann 定律）
- 自动布局算法（SeqLS）
- 完整的可视化输出

## 目录结构

```
radiation_gen/
├── configs/
│   └── config_default.yaml      # 默认配置文件
├── data_gen/
│   ├── __init__.py
│   └── configurable_generator.py # 数据生成器主程序
├── layout/
│   └── SeqLS.py                 # 序列布局采样算法
├── solver/
│   └── solver.py                # FEniCSx 热仿真求解器
├── utils/
│   ├── __init__.py
│   └── utils.py                 # 可视化和工具函数
└── README.md
```

## 环境依赖

### 必需依赖
```bash
# FEniCSx 及其依赖
dolfinx
petsc4py
mpi4py

# 科学计算
numpy
scipy

# 可视化
matplotlib

# 几何计算
shapely

# 配置文件
pyyaml
```

### 安装建议
推荐使用 conda 安装 FEniCSx：
```bash
conda create -n fenicsx python=3.10
conda activate fenicsx
conda install -c conda-forge fenics-dolfinx mpich pyvista
pip install shapely pyyaml
```

## 快速开始

### 1. 基本使用

使用默认配置生成数据：
```bash
python -m data_gen.configurable_generator
```

### 2. 配置文件说明

配置文件 `configs/config_default.yaml` 包含以下主要参数：

#### 全局设置
```yaml
simulation_mode: "radiation"  # 仿真模式（仅支持辐射模式）
num_samples: 5                # 生成样本数量
save_root: "/data/zxr/data"   # 数据保存根目录
mesh_size: [128, 128]         # 网格尺寸 (Ny, Nx)
```

#### 物理参数
```yaml
# 布局域尺寸 [m]
domain_size:
  min: 0.5
  max: 2.0
  step: 0.01
  distribution: "discrete_uniform"

# 材料导热系数 [W/(m·K)]
material_kappa:
  fixed: 1.155

# 表面发射率
emissivity:
  fixed: 0.9

# 环境温度 [K]
background_temperature:
  min: 260.0
  max: 290.0
  step: 0.5
  distribution: "discrete_uniform"
```

#### 元件配置
```yaml
component:
  # 元件数量范围（循环生成）
  num_components_range:
    min: 10               # 起始元件数量
    max: 20               # 结束元件数量
```

**元件数量生成规则**：
- 采用循环递增方式，而非随机生成
- 第 1 个样本：10 个元件
- 第 2 个样本：11 个元件
- ...
- 第 11 个样本：20 个元件
- 第 12 个样本：10 个元件（循环回到起始值）
- 以此类推

```yaml
component:
  # 元件数量范围
  num_components_range:
    min: 10
    max: 20
  
  # 形状概率分布
  shapes: ["rect", "circle", "capsule"]
  shape_probs: [0.55, 0.15, 0.3]
  
  # 面积占比范围
  area_ratio_range: [0.4, 0.5]
  
  # 功率区间配置（支持多区间）
  power_ranges:
    - min: 5.0
      max: 20.0
      step: 0.05
      distribution: "uniform"
      weight: 0.9          # 90% 的元件
    - min: 30.0
      max: 50.0
      distribution: "uniform"
      weight: 0.1          # 10% 的元件
  
  # 各形状尺寸范围 [m]
  rect:
    width: [0.05, 0.3]
    height: [0.05, 0.3]
  circle:
    radius: [0.025, 0.15]
  capsule:
    length: [0.15, 0.3]
    width: [0.025, 0.1]
```

#### 散热线配置
```yaml
cooling_lines:
  length_ratio: 0.2           # 散热线段长度为布局域边长的比例（20%）
  num_lines: 2                # 生成的散热线段数量
  edges: ["bottom", "top", "left", "right"]  # 可选边
  overlap_threshold: 0.001    # 重叠判定阈值 [m]
  max_attempts: 100           # 最大尝试次数
```

说明：
- 散热线段长度自动根据布局域边长计算（水平边基于 x 方向，垂直边基于 y 方向）
- 位置在选定边上随机生成
- 同一条边上的线段不会重叠

#### 精度控制
```yaml
decimal_precision:
  # 可选配置项（注释掉则不进行精度截断）
  # background_temperature: 2
  # material_kappa: 3
  # domain_size: 2
  # cooling_line_length: 3
  # component_dimensions: 3
  # power_values: 2
```

## 输出数据格式

每个样本生成在独立的文件夹中，包含以下文件：

### 数据文件
- `heat_source.npy` - 热源矩阵 (Ny × Nx)
- `temperature.npy` - 温度场矩阵 (Ny × Nx)
- `sdf.npy` - 元件符号距离场 (Ny × Nx)
- `cooling_sdf.npy` - 散热边界符号距离场 (Ny × Nx)
- `cooling_temperature.npy` - 恒定背景温度场 (Ny × Nx)
- `info.json` - 样本元数据

### 可视化文件
- `layout.png` - 元件布局图
- `heat_source.png` - 热源分布图
- `temperature.png` - 温度场图
- `sdf.png` - 元件 SDF 图
- `cooling_sdf.png` - 散热边界 SDF 图

### 元数据 (info.json)
```json
{
  "sample_id": 0,
  "mode": "radiation",
  "layout_domain": [1.5, 1.5],
  "kappa": 1.155,
  "background_temp": 275.0,
  "emissivity": 0.9,
  "components": [
    {
      "id": 0,
      "shape": "rect",
      "width": 0.2,
      "height": 0.15,
      "total_power": 15.5,
      "area": 0.03,
      "power": 516.67,
      "center": [0.75, 0.8]
    }
  ],
  "cooling_lines": [
    {
      "edge": "bottom",
      "endpoints": [[0.2, 0.0], [0.5, 0.0]],
      "length": 0.3
    }
  ]
}
```

## 核心算法

### 1. 布局算法 (SeqLS)
- 按面积降序排列元件
- 基于 VEM（虚拟元件矩阵）的碰撞检测
- 支持矩形、圆形、胶囊形（含旋转）
- 自动匹配布局域尺寸

### 2. 热仿真求解器
物理模型：
```
域内方程：-κ∇²T = f(x)
边界条件：-κ∂T/∂n = εσ(T⁴ - T_amb⁴)
```

其中：
- κ: 导热系数 [W/(m·K)]
- ε: 表面发射率 (0~1)
- σ: Stefan-Boltzmann 常数 = 5.67×10⁻⁸ W/(m²·K⁴)
- T: 温度 [K]
- T_amb: 环境温度 [K]

求解方法：
- 有限元方法（FEniCSx）
- Newton 迭代法求解非线性问题
- GMRES + ILU 预条件

### 3. 符号距离场 (SDF)
- 元件 SDF：到最近元件边界的有符号距离
- 散热边界 SDF：到最近散热线段的距离
- 用于神经网络的几何特征编码

## 数据集目录结构

```
dataset/
└── radiation_20260303_114530/
    ├── config/
    │   └── config.yaml          # 配置文件备份
    ├── samples/
    │   ├── sample_00000/
    │   │   ├── heat_source.npy
    │   │   ├── temperature.npy
    │   │   ├── sdf.npy
    │   │   ├── cooling_sdf.npy
    │   │   ├── cooling_temperature.npy
    │   │   ├── info.json
    │   │   ├── layout.png
    │   │   ├── heat_source.png
    │   │   ├── temperature.png
    │   │   ├── sdf.png
    │   │   └── cooling_sdf.png
    │   ├── sample_00001/
    │   └── ...
    └── summary/
```

## 参数分布说明

### 分布类型

1. **固定值 (fixed)**
```yaml
material_kappa:
  fixed: 1.155
```

2. **离散均匀分布 (discrete_uniform)**
```yaml
domain_size:
  min: 0.5
  max: 2.0
  step: 0.01
  distribution: "discrete_uniform"
```
生成值：0.5, 0.51, 0.52, ..., 2.0

3. **连续均匀分布 (uniform)**
```yaml
background_temperature:
  min: 260.0
  max: 290.0
  distribution: "uniform"
```
生成值：[260.0, 290.0] 区间内的任意浮点数

### 精度控制

只有 `uniform` 分布且配置了 `decimal_precision` 时才会进行四舍五入：
```yaml
decimal_precision:
  background_temperature: 2  # 保留2位小数
```
