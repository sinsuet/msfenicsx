import os
import yaml
import random
import numpy as np
import json
import logging
import sys
import shutil
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional
from scipy.stats import truncnorm
from scipy.interpolate import griddata
import matplotlib.pyplot as plt

from layout.SeqLS import SeqLS
from solver.solver import UnifiedSolver
from utils.utils import (
    compute_sdf, compute_cooling_sdf,
    plot_sdf, plot_temperature_field, plot_layout,
    plot_heat_source, plot_cooling_sdf
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DataGenerator:
    """
    统一、可配置的数据生成器。
    支持：时间戳目录结构、多种物理模式、双区间功率分布、动态精度控制。
    """
    def __init__(self, config_path: str, root_dir: str = None):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # 1. 建立目录结构
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_root = root_dir or self.config.get("save_root", "./dataset")
        mode_prefix = self.config.get("simulation_mode", "sim")
        self.session_dir = os.path.join(save_root, f"{mode_prefix}_{timestamp}")
        
        self.config_dir = os.path.join(self.session_dir, "config")
        self.samples_dir = os.path.join(self.session_dir, "samples")
        self.summary_dir = os.path.join(self.session_dir, "summary")
        
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.samples_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)
        
        # 2. 备份配置文件
        shutil.copy(config_path, os.path.join(self.config_dir, "config.yaml"))

        # 3. 解析基础参数
        self.num_samples = self.config["num_samples"]
        self.mesh_size = tuple(self.config["mesh_size"]) # (ny, nx)
        self.prec = self.config.get("decimal_precision", {})
        
        # 4. 初始化元件数量循环生成器
        self.comp_num_min = self.config["component"]["num_components_range"]["min"]
        self.comp_num_max = self.config["component"]["num_components_range"]["max"]
        self.current_comp_num = self.comp_num_min  # 从最小值开始
        
        logger.info(f"数据生成器启动 | 模式: radiation | 目标样本数: {self.num_samples}")
        logger.info(f"元件数量循环范围: {self.comp_num_min} ~ {self.comp_num_max}")

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _get_next_component_count(self) -> int:
        """获取下一个元件数量（循环递增）"""
        count = self.current_comp_num
        # 更新到下一个值，循环回到最小值
        if self.current_comp_num >= self.comp_num_max:
            self.current_comp_num = self.comp_num_min
        else:
            self.current_comp_num += 1
        return count


    def _get_value(self, cfg: Dict, key: str) -> float:
        """解析固定值或分布的值。只有 uniform 模式且配置了精度时才执行截断。"""
        if "fixed" in cfg:
            val = float(cfg["fixed"])
            # 固定值模式，如果配置了精度则截断
            if key in self.prec:
                return round(val, self.prec[key])
            return val
            
        dist_type = cfg.get("distribution")
        if dist_type == "discrete_uniform":
            # 离散均匀分布：不执行额外的精度截断，保持步长定义的精度
            vals = np.arange(cfg["min"], cfg["max"] + cfg["step"]/2, cfg["step"])
            return float(random.choice(vals))
        elif dist_type == "uniform":
            val = random.uniform(cfg["min"], cfg["max"])
            # 均匀分布：只有配置了精度才截断
            if key in self.prec:
                return round(val, self.prec[key])
            return val
        else:
            return float(cfg.get("fixed", 0.0))

    def _get_matched_domain_size(self, total_area: float) -> float:
        """根据面积占比范围匹配合适的布局域边长。"""
        ratio_range = self.config["component"]["area_ratio_range"]
        # 随机选择一个目标占比
        target_ratio = random.uniform(ratio_range[0], ratio_range[1])
        # 计算理论边长
        theoretical_side = np.sqrt(total_area / target_ratio)
        
        # 从配置的 domain_size 范围中寻找最接近的离散值
        d_cfg = self.config["domain_size"]
        candidates = np.arange(d_cfg["min"], d_cfg["max"] + d_cfg["step"]/2, d_cfg["step"])
        diff = np.abs(candidates - theoretical_side)
        best_side = float(candidates[np.argmin(diff)])
        
        # 应用精度控制
        if "domain_size" in self.prec:
            return round(best_side, self.prec["domain_size"])
        return best_side

    def run(self):
        """执行批量生成。"""
        logger.info(f"开始批量生成样本，保存至: {self.session_dir}")
        success_count = 0
        for i in range(self.num_samples):
            try:
                logger.info(f"正在生成样本 [{i+1}/{self.num_samples}]...")
                self._generate_single_sample(i)
                success_count += 1
            except Exception as e:
                logger.error(f"样本 {i} 生成失败: {e}")
        
        logger.info("=" * 50)
        logger.info(f"数据生成完成！")
        logger.info(f"成功: {success_count} / {self.num_samples}")
        logger.info(f"数据集路径: {self.session_dir}")
        logger.info("=" * 50)

    def _generate_single_sample(self, idx):
        # 1. 确定物理环境参数
        kappa = self._get_value(self.config["material_kappa"], "material_kappa")
        bg_temp = self._get_value(self.config["background_temperature"], "background_temperature")
        # 本生成器现在只支持辐射模式，始终读取发射率
        emissivity = self._get_value(self.config["emissivity"], "emissivity")

        # 2. 生成元件列表（循环递增数量）
        num_comp = self._get_next_component_count()
        logger.info(f"样本 {idx}: 生成 {num_comp} 个元件")
        components = self._create_components(num_comp)
        total_area = sum(c["area"] for c in components)
        
        # 3. 匹配布局域尺寸
        domain_side = self._get_matched_domain_size(total_area)
        layout_domain = (domain_side, domain_side)
        
        # 4. 执行布局采样 (使用 SeqLS)
        seq_ls = SeqLS(layout_domain, self.mesh_size)
        placed_components = seq_ls.layout_sampling(components, 
                                                   max_sampling_attempts=self.config["component"].get("max_sampling_attempts", 500))
        if len(placed_components) < num_comp:
            raise RuntimeError(f"布局失败: 仅放置了 {len(placed_components)}/{num_comp} 个元件")

        # 5. 生成散热线
        cooling_lines = self._create_cooling_lines(layout_domain)

        # 6. 求解温度场
        solver = UnifiedSolver(domain_side, domain_side, self.mesh_size[1], self.mesh_size[0], kappa=kappa)
        F_grid = self._create_source_matrix(placed_components, layout_domain)
        
        # 6. 求解温度场（非线性辐射边界条件）
        u_sol = solver.solve_radiation(F_grid, [l["endpoints"] for l in cooling_lines], bg_temp, emissivity)

        # 7. 后处理与保存
        self._save_sample(idx, {
            "heat_source": F_grid,
            "u_sol": u_sol,
            "solver": solver,
            "layout_domain": layout_domain,
            "bg_temp": bg_temp,
            "kappa": kappa,
            "emissivity": emissivity,
            "components": placed_components,
            "cooling_lines": cooling_lines
        })

    def _create_components(self, num_comp: int) -> List[Dict]:
        comp_cfg = self.config["component"]
        components = []
        
        # 分配功率区间
        if comp_cfg.get("force_power_proportion"):
            weights = [r["weight"] for r in comp_cfg["power_ranges"]]
            counts = np.random.multinomial(num_comp, weights)
            range_indices = []
            for i, count in enumerate(counts):
                range_indices.extend([i] * count)
            random.shuffle(range_indices)
        else:
            range_indices = random.choices(range(len(comp_cfg["power_ranges"])), 
                                           weights=[r["weight"] for r in comp_cfg["power_ranges"]], k=num_comp)

        for i in range(num_comp):
            shape = random.choices(comp_cfg["shapes"], weights=comp_cfg["shape_probs"])[0]
            p_cfg = comp_cfg["power_ranges"][range_indices[i]]
            
            # 功率生成逻辑：discrete_uniform vs uniform
            if p_cfg.get("distribution") == "discrete_uniform":
                p_vals = np.arange(p_cfg["min"], p_cfg["max"] + p_cfg["step"]/2, p_cfg["step"])
                power = float(random.choice(p_vals))
            else:
                power = random.uniform(p_cfg["min"], p_cfg["max"])
                if "power_values" in self.prec:
                    power = round(power, self.prec["power_values"])
            
            comp = {"id": i, "shape": shape, "total_power": power}
            
            # 尺寸生成
            s_cfg = comp_cfg[shape]
            if shape == "rect":
                comp["width"] = self._rand_dim(s_cfg["width"])
                comp["height"] = self._rand_dim(s_cfg["height"])
                comp["area"] = comp["width"] * comp["height"]
            elif shape == "circle":
                comp["radius"] = self._rand_dim(s_cfg["radius"])
                comp["area"] = np.pi * (comp["radius"]**2)
            elif shape == "capsule":
                comp["width"] = self._rand_dim(s_cfg["width"])
                comp["length"] = self._rand_dim(s_cfg["length"])
                comp["rotation"] = random.choice([0, 90])
                r = comp["width"] / 2
                comp["area"] = (comp["length"] - comp["width"]) * comp["width"] + np.pi * (r**2)
            
            comp["power"] = comp["total_power"] / comp["area"]
            components.append(comp)
        return components

    def _rand_dim(self, r: List[float]) -> float:
        val = random.uniform(r[0], r[1])
        if "component_dimensions" in self.prec:
            return round(val, self.prec["component_dimensions"])
        return val

    def _create_cooling_lines(self, layout_domain: Tuple[float, float]) -> List[Dict]:
        """生成散热线段，长度为布局域边长的固定比例，位置随机，避免重叠"""
        c_cfg = self.config["cooling_lines"]
        dx, dy = layout_domain
        lines = []

        # 计算散热线段长度（基于布局域边长的比例）
        length_ratio = c_cfg.get("length_ratio", 0.2)
        num_lines = c_cfg.get("num_lines", 2)
        overlap_threshold = c_cfg.get("overlap_threshold", 0.001)
        max_attempts = c_cfg.get("max_attempts", 100)
        available_edges = c_cfg.get("edges", ["bottom", "top", "left", "right"])

        # 为每条线段尝试生成
        for _ in range(num_lines):
            placed = False

            for attempt in range(max_attempts):
                # 随机选择一条边
                edge = random.choice(available_edges)

                # 根据边的方向计算长度和起始位置
                if edge in ["top", "bottom"]:
                    # 水平边：长度基于 x 方向
                    length = dx * length_ratio
                    max_start = dx - length
                    if max_start <= 0:
                        continue  # 长度超过边长，跳过
                    start = random.uniform(0, max_start)
                    y_pos = dy if edge == "top" else 0.0
                    endpoints = [[start, y_pos], [start + length, y_pos]]

                else:  # left or right
                    # 垂直边：长度基于 y 方向
                    length = dy * length_ratio
                    max_start = dy - length
                    if max_start <= 0:
                        continue  # 长度超过边长，跳过
                    start = random.uniform(0, max_start)
                    x_pos = dx if edge == "right" else 0.0
                    endpoints = [[x_pos, start], [x_pos, start + length]]

                # 检查是否与已有线段重叠
                has_overlap = False
                for existing_line in lines:
                    if self._check_line_overlap(endpoints, existing_line["endpoints"], 
                                                edge, existing_line["edge"], overlap_threshold):
                        has_overlap = True
                        break

                if not has_overlap:
                    lines.append({
                        "edge": edge,
                        "endpoints": endpoints,
                        "length": length
                    })
                    placed = True
                    break

            if not placed:
                logger.warning(f"无法放置第 {len(lines) + 1} 条散热线段（尝试 {max_attempts} 次后失败）")

        # 统一应用精度
        if "cooling_line_length" in self.prec:
            p = self.prec["cooling_line_length"]
            for l in lines:
                l["length"] = round(l["length"], p)
                l["endpoints"] = [[round(coord, p) for coord in pt] for pt in l["endpoints"]]

        return lines

    def _check_line_overlap(self, line1: List[List[float]], line2: List[List[float]],
                           edge1: str, edge2: str, threshold: float) -> bool:
        """检查两条线段是否重叠（仅检查同一条边上的线段）"""
        # 不在同一条边上，不会重叠
        if edge1 != edge2:
            return False

        # 提取线段的起点和终点坐标
        if edge1 in ["top", "bottom"]:
            # 水平线段：比较 x 坐标范围
            x1_start, x1_end = min(line1[0][0], line1[1][0]), max(line1[0][0], line1[1][0])
            x2_start, x2_end = min(line2[0][0], line2[1][0]), max(line2[0][0], line2[1][0])
            # 检查区间是否重叠
            return not (x1_end + threshold < x2_start or x2_end + threshold < x1_start)
        else:
            # 垂直线段：比较 y 坐标范围
            y1_start, y1_end = min(line1[0][1], line1[1][1]), max(line1[0][1], line1[1][1])
            y2_start, y2_end = min(line2[0][1], line2[1][1]), max(line2[0][1], line2[1][1])
            # 检查区间是否重叠
            return not (y1_end + threshold < y2_start or y2_end + threshold < y1_start)


    def _create_source_matrix(self, components: List[Dict], layout_domain: Tuple[float, float]) -> np.ndarray:
        ny, nx = self.mesh_size
        F = np.zeros((ny, nx))
        x = np.linspace(0, layout_domain[0], nx)
        y = np.linspace(0, layout_domain[1], ny)
        X, Y = np.meshgrid(x, y)
        tol = 1e-8
        
        for comp in components:
            cx, cy = comp["center"]
            p = comp["power"]
            if comp["shape"] == "rect":
                w, h = comp["width"], comp["height"]
                mask = (X >= cx - w/2 + tol) & (X <= cx + w/2 - tol) & \
                       (Y >= cy - h/2 + tol) & (Y <= cy + h/2 - tol)
            elif comp["shape"] == "circle":
                r = comp["radius"]
                mask = (X - cx)**2 + (Y - cy)**2 <= r**2 + tol
            elif comp["shape"] == "capsule":
                l, w = comp["length"], comp["width"]
                rot = comp["rotation"]
                r = w / 2
                rl = l - w
                if rot == 0:
                    mask = (X >= cx - rl/2) & (X <= cx + rl/2) & (Y >= cy - r) & (Y <= cy + r)
                    mask |= (X - (cx - rl/2))**2 + (Y - cy)**2 <= r**2
                    mask |= (X - (cx + rl/2))**2 + (Y - cy)**2 <= r**2
                else:
                    mask = (X >= cx - r) & (X <= cx + r) & (Y >= cy - rl/2) & (Y <= cy + rl/2)
                    mask |= (X - cx)**2 + (Y - (cy - rl/2))**2 <= r**2
                    mask |= (X - cx)**2 + (Y - (cy + rl/2))**2 <= r**2
            F[mask] = p
        return F

    def _save_sample(self, idx, data):
        sample_path = os.path.join(self.samples_dir, f"sample_{idx:05d}")
        os.makedirs(sample_path, exist_ok=True)
        
        # 1. 处理插值数据
        solver = data["solver"]
        u_sol = data["u_sol"]
        lx, ly = data["layout_domain"]
        ny, nx = self.mesh_size
        
        dof_coords = solver.V.tabulate_dof_coordinates()
        vals = u_sol.x.array
        
        x_grid = np.linspace(lx/(2*nx), lx - lx/(2*nx), nx)
        y_grid = np.linspace(ly/(2*ny), ly - ly/(2*ny), ny)
        X_grid, Y_grid = np.meshgrid(x_grid, y_grid, indexing='xy')
        
        temp_matrix = griddata((dof_coords[:, 0], dof_coords[:, 1]), vals, (X_grid, Y_grid), method='cubic')
        temp_matrix[np.isnan(temp_matrix)] = data["bg_temp"]
        
        # 2. 生成各种场
        sdf = compute_sdf(data["components"], X_grid, Y_grid)
        cooling_sdf = compute_cooling_sdf(data["cooling_lines"], X_grid, Y_grid)
        const_temp_field = np.full(self.mesh_size, data["bg_temp"])
        
        # 3. 保存 Numpy 文件
        np.save(os.path.join(sample_path, "heat_source.npy"), data["heat_source"].astype(np.float32))
        np.save(os.path.join(sample_path, "temperature.npy"), temp_matrix.astype(np.float32))
        np.save(os.path.join(sample_path, "sdf.npy"), sdf.astype(np.float32))
        np.save(os.path.join(sample_path, "cooling_sdf.npy"), cooling_sdf.astype(np.float32))
        np.save(os.path.join(sample_path, "cooling_temperature.npy"), const_temp_field.astype(np.float32))
        
        # 4. 保存 JSON
        info = {
            "sample_id": idx,
            "mode": "radiation",
            "layout_domain": data["layout_domain"],
            "kappa": data["kappa"],
            "background_temp": data["bg_temp"],
            "emissivity": data["emissivity"],
            "components": data["components"],
            "cooling_lines": data["cooling_lines"]
        }
        with open(os.path.join(sample_path, "info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
            
        # 5. 调用外部工具进行可视化保存
        x_range = (0, lx)
        y_range = (0, ly)
        
        # 布局图
        plot_layout(
            components=data["components"],
            layout_domain=data["layout_domain"],
            mesh_size=self.mesh_size,
            save_path=os.path.join(sample_path, "layout.png")
        )
        
        # 热源图
        plot_heat_source(
            source_matrix=data["heat_source"],
            layout_domain=data["layout_domain"],
            cooling_lines=data["cooling_lines"],
            save_path=os.path.join(sample_path, "heat_source.png")
        )
        
        # 温度场图
        plot_temperature_field(
            temp_matrix=temp_matrix,
            x_range=x_range,
            y_range=y_range,
            save_path=os.path.join(sample_path, "temperature.png")
        )
        
        # 元件 SDF 图
        plot_sdf(
            sdf_matrix=sdf,
            x_range=x_range,
            y_range=y_range,
            save_path=os.path.join(sample_path, "sdf.png")
        )
        
        # 散热边界 SDF 图
        plot_cooling_sdf(
            sdf_matrix=cooling_sdf,
            x_range=x_range,
            y_range=y_range,
            save_path=os.path.join(sample_path, "cooling_sdf.png")
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=r"./configs/config_default.yaml")
    args = parser.parse_args()
    gen = DataGenerator(args.config)
    gen.run()
