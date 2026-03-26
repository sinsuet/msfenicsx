# FEniCSx 安装与第一个二维稳态导热示例

## 1. 这套环境是什么

- 系统：WSL2 Ubuntu 24.04.3 LTS
- 项目目录：`~/msfenicsx`
- conda 环境：`msfenicsx`
- 安装路线：`conda-forge` 上的 `fenics-dolfinx`

这条路线的优点是：

- 对 WSL2 新手更直接，不需要 Docker。
- 和社区常见教程更接近。
- 后续继续补 `gmsh`、`pyvista`、`jupyterlab` 也比较自然。

## 2. 建议你以后常用的命令

先进入项目目录：

```bash
cd ~/msfenicsx
```

激活环境：

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate msfenicsx
```

检查导入：

```bash
python examples/00_import_check.py
```

运行第一个二维导热例子：

```bash
python examples/01_steady_heat_rectangle.py
```

如果你想显式通过 MPI 启动，也可以：

```bash
mpirun -n 1 python examples/01_steady_heat_rectangle.py
```

## 3. 这个导热问题在求什么

我们求的是二维矩形区域里的稳态温度场 `u(x, y)`。

稳态意味着：

- 温度不随时间变化。
- 区域内部没有热源项。

所以控制方程是：

```text
-Δu = 0
```

这里的 `Δ` 是拉普拉斯算子，表示温度在空间中的二阶变化。

## 4. 为什么这个例子适合入门

这个例子把边界温度设成：

```text
u(x, y) = 1 - x / L
```

含义是：

- 左边界 `x = 0`，温度是 `1`
- 右边界 `x = L`，温度是 `0`
- 上下边界也沿着 `x` 方向做同样的线性变化

这样做有两个好处：

- 物理图像很直观：温度从左到右线性下降。
- 解析解已知，正好也是 `u = 1 - x / L`，所以我们可以拿它验证程序是不是装对、写对、算对。

## 5. 代码里最重要的几个概念

### 5.1 网格 `mesh`

网格就是把连续区域切成很多小单元。这里用的是二维三角形网格。

在代码里：

```python
domain = mesh.create_rectangle(...)
```

它定义了：

- 计算区域是一个矩形
- 矩形被分成多少个小单元
- 单元类型是三角形

## 5.2 函数空间 `function space`

函数空间决定“我们准备用什么样的函数近似真实解”。

这里选的是：

```python
V = fem.functionspace(domain, ("Lagrange", 1))
```

意思是：

- 使用拉格朗日有限元
- 阶数是 1，也就是每个单元里用线性函数近似温度

这是入门最常见、最稳妥的选择。

## 5.3 边界条件 `Dirichlet boundary condition`

Dirichlet 边界条件就是直接指定边界上的温度值。

这里先插值出边界温度函数：

```python
u_D.interpolate(lambda x: 1.0 - x[0] / length)
```

再找到边界自由度：

```python
boundary_dofs = fem.locate_dofs_geometrical(...)
```

最后把边界条件绑定到问题上：

```python
bc = fem.dirichletbc(u_D, boundary_dofs)
```

## 5.4 变分形式 `variational form`

有限元不会直接用强形式 `-Δu = 0` 去求，而是转成弱形式。

这个例子对应：

```python
a = inner(grad(u), grad(v)) * dx
L = 0 * v * dx
```

你可以先把它理解成：

- `u` 是未知温度
- `v` 是测试函数
- `a` 表示系统刚度
- `L` 表示右端项

当前没有热源，所以右端项是 0。

## 5.5 求解

我们用 `LinearProblem` 来装配并求解线性系统：

```python
problem = LinearProblem(...)
uh = problem.solve()
```

求出来的 `uh` 就是离散后的温度场。

## 5.6 结果查看

这个示例会输出三类结果：

- `outputs/figures/01_steady_heat_rectangle.png`
  - 温度场伪彩色图
- `outputs/data/01_steady_heat_rectangle.xdmf`
  - 可用于 ParaView 等工具继续查看
- `outputs/data/01_steady_heat_rectangle_summary.txt`
  - 最小值、最大值、与解析解的最大误差

## 6. 你应该重点关注什么

第一次跑通时，重点不是一下子记住所有 API，而是先建立这条主线：

1. 先有几何区域
2. 再离散成网格
3. 再选函数空间
4. 再写边界条件
5. 再写变分形式
6. 最后求解和查看结果

这条主线就是后面做更复杂热传导、弹性力学、流体问题时的共同骨架。

## 7. 下一步适合学什么

跑通这个例子后，下一步建议按这个顺序继续：

1. 把边界温度改成别的函数，看看结果怎么变
2. 给内部加热源项，学习 `f * v * dx`
3. 改成不同材料系数，学习 `k * inner(grad(u), grad(v)) * dx`
4. 再进入瞬态热传导
