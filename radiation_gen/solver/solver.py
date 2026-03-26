"""
精简的热仿真求解器，仅支持非线性辐射边界条件。

物理模型：
    -κ∇²T = f(x)  (域内热传导方程)
    -κ∂T/∂n = εσ(T⁴ - T_amb⁴)  (边界辐射散热)

其中：
- κ: 导热系数 [W/(m·K)]
- ε: 表面发射率 (0~1)
- σ: Stefan-Boltzmann 常数 = 5.67×10⁻⁸ W/(m²·K⁴)
- T: 温度 [K]
- T_amb: 环境温度 [K]
"""

import numpy as np
import ufl
from dolfinx import fem, mesh, log
from dolfinx.fem.petsc import NonlinearProblem
from mpi4py import MPI

# Stefan-Boltzmann 常数 [W/(m²·K⁴)]
STEFAN_BOLTZMANN = 5.670374419e-8


class UnifiedSolver:
    """统一热仿真求解器，支持非线性辐射边界条件。"""
    
    def __init__(self, length_x, length_y, nx, ny, kappa=1.0, comm=MPI.COMM_WORLD):
        """
        初始化求解器。
        
        参数:
            length_x: 布局域长度 (x方向) [m]
            length_y: 布局域宽度 (y方向) [m]
            nx: x方向网格数量
            ny: y方向网格数量
            kappa: 材料导热系数 [W/(m·K)]
            comm: MPI 通信器
        """
        self.length_x = length_x
        self.length_y = length_y
        self.nx = nx
        self.ny = ny
        self.kappa = kappa
        self.comm = comm
        
        # 创建矩形网格
        domain = ((0.0, 0.0), (length_x, length_y))
        self.mesh = mesh.create_rectangle(
            self.comm, domain, (nx, ny), cell_type=mesh.CellType.triangle
        )
        
        # 定义一阶拉格朗日函数空间
        self.V = fem.functionspace(self.mesh, ("Lagrange", 1))
        
    def solve_radiation(self, F_grid, radiation_lines, T_amb, emissivity=0.9):
        """
        求解带有非线性辐射边界条件的热传导方程。
        
        参数:
            F_grid: 热源矩阵 (Ny x Nx)
            radiation_lines: 辐射边界线段列表 [[(x0,y0), (x1,y1)], ...]
            T_amb: 环境温度 [K]
            emissivity: 表面发射率 (0~1)
            
        返回:
            fem.Function: 温度场解
        """
        # 1. 插值热源到有限元空间
        f_expr = fem.Function(self.V)
        self._interpolate_source(f_expr, F_grid)
        
        # 2. 标记辐射边界
        facet_tags = self._mark_boundaries(radiation_lines)
        ds = ufl.Measure("ds", domain=self.mesh, subdomain_data=facet_tags)
        
        # 3. 合并所有辐射边界的积分测度
        unique_tags = np.unique(facet_tags.values)
        unique_tags = unique_tags[unique_tags > 0]
        ds_rad = ds(int(unique_tags[0]))
        for tag in unique_tags[1:]:
            ds_rad = ds_rad + ds(int(tag))
            
        # 4. 定义非线性变分问题
        u = fem.Function(self.V)
        v = ufl.TestFunction(self.V)
        dx = ufl.Measure("dx", domain=self.mesh)
        
        # 初始猜测：环境温度 + 50K
        u.x.array[:] = T_amb + 50.0
        
        # 辐射系数
        eps_sigma = emissivity * STEFAN_BOLTZMANN
        
        # 残差形式：∫κ∇u·∇v dx + ∫εσ(u⁴-T_amb⁴)v ds - ∫fv dx = 0
        residual = (
            ufl.inner(self.kappa * ufl.grad(u), ufl.grad(v)) * dx + 
            eps_sigma * (u**4 - T_amb**4) * v * ds_rad - 
            ufl.inner(f_expr, v) * dx
        )
        
        # 雅可比矩阵
        J = ufl.derivative(residual, u)
        
        # 5. 配置并求解
        petsc_options = {
            "snes_type": "newtonls",
            "snes_max_it": 50,
            "snes_rtol": 1e-6,
            "ksp_type": "gmres",
            "pc_type": "ilu"
        }
        
        problem = NonlinearProblem(
            residual, u, bcs=[], J=J,
            petsc_options_prefix="rad_",
            petsc_options=petsc_options
        )
        
        log.set_log_level(log.LogLevel.WARNING)
        problem.solve()
        
        return u

    def _mark_boundaries(self, boundary_lines):
        """标记边界线段为 facets。"""
        facet_indices, facet_values = [], []
        
        for i, line in enumerate(boundary_lines):
            tag = i + 1
            (x0, y0), (x1, y1) = line
            
            # 定义边界判断函数
            def boundary_func(x, line=line):
                (lx, ly), (rx, ry) = line
                if np.isclose(lx, rx):  # 垂直线
                    return np.isclose(x[0], lx) & (x[1] >= min(ly, ry) - 1e-6) & (x[1] <= max(ly, ry) + 1e-6)
                else:  # 水平线
                    return np.isclose(x[1], ly) & (x[0] >= min(lx, rx) - 1e-6) & (x[0] <= max(lx, rx) + 1e-6)
            
            # 定位边界 facets
            facets = mesh.locate_entities_boundary(
                self.mesh, self.mesh.topology.dim - 1, boundary_func
            )
            facet_indices.append(facets)
            facet_values.append(np.full_like(facets, tag))
            
        # 创建 MeshTags
        return mesh.meshtags(
            self.mesh, self.mesh.topology.dim - 1,
            np.hstack(facet_indices).astype(np.int32),
            np.hstack(facet_values).astype(np.int32)
        )

    def _interpolate_source(self, f_func, F_grid):
        """将热源矩阵插值到有限元空间。"""
        ny, nx = F_grid.shape
        
        def source_eval(x):
            # 坐标归一化到 [0, 1]
            x_ratio = np.clip(x[0] / self.length_x, 0, 1)
            y_ratio = np.clip(x[1] / self.length_y, 0, 1)
            
            # 映射到矩阵索引
            xx = (x_ratio * (nx - 1)).astype(int)
            yy = (y_ratio * (ny - 1)).astype(int)
            
            return F_grid[yy, xx]

        f_func.interpolate(source_eval)
