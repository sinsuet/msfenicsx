"""
SeqLS 布局算法：涵盖矩形，圆形，胶囊（支持胶囊旋转）
输入示例：
components = [
    {"id": 0, "shape": "capsule", "length": 0.048, "width": 0.012, "rotation": 0, "power": 8000},  # 横向
    {"id": 1, "shape": "capsule", "length": 0.048, "width": 0.012, "rotation": 90, "power": 8000},  # 纵向
    {"id": 2, "shape": "rect", "width": 0.024, "height": 0.024, "power": 6000},
    {"id": 3, "shape": "circle", "radius": 0.012, "power": 5000},
]
"""

import numpy as np
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from typing import List, Tuple, Dict, Optional


class SeqLS:
    def __init__(self,
                 layout_domain: Tuple[float, float],  # 布局域尺寸 (width, height)
                 mesh_size: Tuple[int, int]):  # 网格尺寸 N×M
        self.layout_width, self.layout_height = layout_domain
        self.mesh_N, self.mesh_M = mesh_size
        self.total_nodes = (self.mesh_N + 1, self.mesh_M + 1)  # VEM 矩阵尺寸 (N+1)×(M+1)

        # 网格单元尺寸（物理单位）
        self.grid_width = self.layout_width / self.mesh_M
        self.grid_height = self.layout_height / self.mesh_N

        # 初始化布局容器 VEM（全 0 矩阵）
        self.VEM0 = np.zeros(self.total_nodes, dtype=int)

        # 存储布局历史（用于可视化）
        self.layout_history = []
        # 存储已放置元件的VEM矩阵
        self.placed_vems = []
        self.tolerance = 1e-8

    def _check_component_size_vs_grid(self, components: List[Dict]):
        """校验元件尺寸是否小于网格单元尺寸（支持胶囊旋转）"""
        grid_width = self.layout_width / self.mesh_M
        grid_height = self.layout_height / self.mesh_N

        for comp in components:
            comp_id = comp["id"]
            shape = comp["shape"]
            errors = []

            if shape == "rect":
                w = comp["width"]
                h = comp["height"]
                if w < grid_width:
                    errors.append(f"宽度 {w}m 小于网格宽度 {grid_width:.4f}m")
                if h < grid_height:
                    errors.append(f"高度 {h}m 小于网格高度 {grid_height:.4f}m")

            elif shape == "circle":
                diameter = 2 * comp["radius"]
                if diameter < grid_width:
                    errors.append(f"直径 {diameter}m 小于网格宽度 {grid_width:.4f}m")
                if diameter < grid_height:
                    errors.append(f"直径 {diameter}m 小于网格高度 {grid_height:.4f}m")

            elif shape == "capsule":
                # 胶囊旋转后，宽度始终是垂直于长轴的尺寸（需覆盖网格）
                width = comp["width"]
                rotation = comp.get("rotation", 0)
                # 长轴方向的尺寸（长度）需覆盖对应轴的网格
                if rotation == 0:
                    # 横向：长轴沿X轴，长度需覆盖X方向网格
                    if width < grid_height:
                        errors.append(f"宽度 {width}m 小于网格高度 {grid_height:.4f}m")
                else:
                    # 纵向：长轴沿Y轴，长度需覆盖Y方向网格
                    if width < grid_width:
                        errors.append(f"宽度 {width}m 小于网格宽度 {grid_width:.4f}m")

            if errors:
                error_msg = (
                    f"元件 ID {comp_id}（形状：{shape}）存在尺寸问题：\n"
                    f"  - {'; '.join(errors)}\n"
                    "  建议：减小网格尺寸/增大元件尺寸/调整网格数量。"
                )
                raise ValueError(error_msg)

    def _calculate_component_area(self, component: Dict) -> float:
        """计算元件面积（用于排序）"""
        if component["shape"] == "rect":
            return component["width"] * component["height"]
        elif component["shape"] == "circle":
            return np.pi * component["radius"] ** 2
        elif component["shape"] == "capsule":
            return component["length"] * component["width"] + np.pi * (component["width"] / 2) ** 2
        return 0.0

    def _discretize_component(self, component: Dict, center: Tuple[float, float]) -> np.ndarray:
        """离散化元件（支持胶囊旋转）"""
        vem = np.zeros(self.total_nodes, dtype=int)
        center_x, center_y = center

        if component["shape"] == "rect":
            w, h = component["width"], component["height"]
            half_w, half_h = w / 2, h / 2

            min_x = center_x - half_w + self.tolerance
            max_x = center_x + half_w - self.tolerance
            min_y = center_y - half_h + self.tolerance
            max_y = center_y + half_h - self.tolerance

            start_row = max(0, int(np.floor(min_y / self.grid_height)))
            end_row = min(self.mesh_N, int(np.ceil(max_y / self.grid_height)))
            start_col = max(0, int(np.floor(min_x / self.grid_width)))
            end_col = min(self.mesh_M, int(np.ceil(max_x / self.grid_width)))

            for row in range(start_row, end_row + 1):
                for col in range(start_col, end_col + 1):
                    vem[row][col] = 1

        elif component["shape"] == "circle":
            r = component["radius"]

            min_x = center_x - r + self.tolerance
            max_x = center_x + r - self.tolerance
            min_y = center_y - r + self.tolerance
            max_y = center_y + r - self.tolerance
            start_row = max(0, int(np.floor(min_y / self.grid_height)))
            end_row = min(self.mesh_N, int(np.ceil(max_y / self.grid_height)))
            start_col = max(0, int(np.floor(min_x / self.grid_width)))
            end_col = min(self.mesh_M, int(np.ceil(max_x / self.grid_width)))

            for row in range(start_row, end_row + 1):
                for col in range(start_col, end_col + 1):
                    node_corners = [
                        (col * self.grid_width, row * self.grid_height),
                        ((col + 1) * self.grid_width, row * self.grid_height),
                        (col * self.grid_width, (row + 1) * self.grid_height),
                        ((col + 1) * self.grid_width, (row + 1) * self.grid_height)
                    ]
                    corner_in_circle = False
                    for (x, y) in node_corners:
                        corner_dist_sq = (x - center_x) ** 2 + (y - center_y) ** 2
                        if corner_dist_sq <= (r ** 2) + self.tolerance:
                            corner_in_circle = True
                            break
                    if corner_in_circle:
                        neighbor_offsets = [(0, 0), (0, 1), (1, 0), (1, 1)]
                        for dr, dc in neighbor_offsets:
                            nr = np.clip(row + dr, 0, self.mesh_N)
                            nc = np.clip(col + dc, 0, self.mesh_M)
                            vem[nr][nc] = 1

        elif component["shape"] == "capsule":
            length = component["length"]
            width = component["width"]
            rotation = component.get("rotation", 0)  # 获取旋转角度
            radius = width / 2
            rect_length = length - width  # 中间矩形长度

            if rotation == 0:
                # 横向：长轴沿X轴（原有逻辑）
                rect_min_x = center_x - rect_length / 2 + self.tolerance
                rect_max_x = center_x + rect_length / 2 - self.tolerance
                rect_min_y = center_y - radius + self.tolerance
                rect_max_y = center_y + radius - self.tolerance

                # 中间矩形
                start_row_rect = max(0, int(np.floor(rect_min_y / self.grid_height)))
                end_row_rect = min(self.mesh_N, int(np.ceil(rect_max_y / self.grid_height)))
                start_col_rect = max(0, int(np.floor(rect_min_x / self.grid_width)))
                end_col_rect = min(self.mesh_M, int(np.ceil(rect_max_x / self.grid_width)))
                for row in range(start_row_rect, end_row_rect + 1):
                    for col in range(start_col_rect, end_col_rect + 1):
                        vem[row][col] = 1

                # 左端半圆
                left_circle_center = (rect_min_x, center_y)
                left_min_x = left_circle_center[0] - radius + self.tolerance
                left_max_x = left_circle_center[0] - self.tolerance
                left_min_y = left_circle_center[1] - radius + self.tolerance
                left_max_y = left_circle_center[1] + radius - self.tolerance
                start_row_left = max(0, int(np.floor(left_min_y / self.grid_height)))
                end_row_left = min(self.mesh_N, int(np.ceil(left_max_y / self.grid_height)))
                start_col_left = max(0, int(np.floor(left_min_x / self.grid_width)))
                end_col_left = min(self.mesh_M, int(np.ceil(left_max_x / self.grid_width)))

                # 右端半圆
                right_circle_center = (rect_max_x, center_y)
                right_min_x = right_circle_center[0] + self.tolerance
                right_max_x = right_circle_center[0] + radius - self.tolerance
                right_min_y = right_circle_center[1] - radius + self.tolerance
                right_max_y = right_circle_center[1] + radius - self.tolerance
                start_row_right = max(0, int(np.floor(right_min_y / self.grid_height)))
                end_row_right = min(self.mesh_N, int(np.ceil(right_max_y / self.grid_height)))
                start_col_right = max(0, int(np.floor(right_min_x / self.grid_width)))
                end_col_right = min(self.mesh_M, int(np.ceil(right_max_x / self.grid_width)))

            else:  # rotation == 90（纵向：长轴沿Y轴）
                # 中间矩形（沿Y轴延伸）
                rect_min_y = center_y - rect_length / 2 + self.tolerance  # Y方向起点
                rect_max_y = center_y + rect_length / 2 - self.tolerance  # Y方向终点
                rect_min_x = center_x - radius + self.tolerance  # X方向起点
                rect_max_x = center_x + radius - self.tolerance  # X方向终点

                # 中间矩形离散化
                start_row_rect = max(0, int(np.floor(rect_min_y / self.grid_height)))
                end_row_rect = min(self.mesh_N, int(np.ceil(rect_max_y / self.grid_height)))
                start_col_rect = max(0, int(np.floor(rect_min_x / self.grid_width)))
                end_col_rect = min(self.mesh_M, int(np.ceil(rect_max_x / self.grid_width)))
                for row in range(start_row_rect, end_row_rect + 1):
                    for col in range(start_col_rect, end_col_rect + 1):
                        vem[row][col] = 1

                # 下端半圆（对应横向左端）
                bottom_circle_center = (center_x, rect_min_y)
                bottom_min_y = bottom_circle_center[1] - radius + self.tolerance
                bottom_max_y = bottom_circle_center[1] - self.tolerance
                bottom_min_x = bottom_circle_center[0] - radius + self.tolerance
                bottom_max_x = bottom_circle_center[0] + radius - self.tolerance
                start_row_bottom = max(0, int(np.floor(bottom_min_y / self.grid_height)))
                end_row_bottom = min(self.mesh_N, int(np.ceil(bottom_max_y / self.grid_height)))
                start_col_bottom = max(0, int(np.floor(bottom_min_x / self.grid_width)))
                end_col_bottom = min(self.mesh_M, int(np.ceil(bottom_max_x / self.grid_width)))

                # 上端半圆（对应横向右端）
                top_circle_center = (center_x, rect_max_y)
                top_min_y = top_circle_center[1] + self.tolerance
                top_max_y = top_circle_center[1] + radius - self.tolerance
                top_min_x = top_circle_center[0] - radius + self.tolerance
                top_max_x = top_circle_center[0] + radius - self.tolerance
                start_row_top = max(0, int(np.floor(top_min_y / self.grid_height)))
                end_row_top = min(self.mesh_N, int(np.ceil(top_max_y / self.grid_height)))
                start_col_top = max(0, int(np.floor(top_min_x / self.grid_width)))
                end_col_top = min(self.mesh_M, int(np.ceil(top_max_x / self.grid_width)))

                # 替换横向的左右半圆为纵向的上下半圆
                left_circle_center = bottom_circle_center
                left_min_x, left_max_x = bottom_min_x, bottom_max_x
                left_min_y, left_max_y = bottom_min_y, bottom_max_y
                start_row_left, end_row_left = start_row_bottom, end_row_bottom
                start_col_left, end_col_left = start_col_bottom, end_col_bottom

                right_circle_center = top_circle_center
                right_min_x, right_max_x = top_min_x, top_max_x
                right_min_y, right_max_y = top_min_y, top_max_y
                start_row_right, end_row_right = start_row_top, end_row_top
                start_col_right, end_col_right = start_col_top, end_col_top

            # 处理两端半圆（横向/纵向通用逻辑）
            neighbor_offsets = [(0, 0), (0, 1), (1, 0), (1, 1)]

            # 左/下端半圆
            for row in range(start_row_left, end_row_left + 1):
                for col in range(start_col_left, end_col_left + 1):
                    node_corners = [
                        (col * self.grid_width, row * self.grid_height),
                        ((col + 1) * self.grid_width, row * self.grid_height),
                        (col * self.grid_width, (row + 1) * self.grid_height),
                        ((col + 1) * self.grid_width, (row + 1) * self.grid_height)
                    ]
                    has_corner_in_circle = False
                    for (x, y) in node_corners:
                        dist_sq = (x - left_circle_center[0]) ** 2 + (y - left_circle_center[1]) ** 2
                        if dist_sq <= (radius ** 2) + self.tolerance:
                            has_corner_in_circle = True
                            break
                    if has_corner_in_circle:
                        for dr, dc in neighbor_offsets:
                            nr = np.clip(row + dr, 0, self.mesh_N)
                            nc = np.clip(col + dc, 0, self.mesh_M)
                            vem[nr][nc] = 1

            # 右/上端半圆
            for row in range(start_row_right, end_row_right + 1):
                for col in range(start_col_right, end_col_right + 1):
                    node_corners = [
                        (col * self.grid_width, row * self.grid_height),
                        ((col + 1) * self.grid_width, row * self.grid_height),
                        (col * self.grid_width, (row + 1) * self.grid_height),
                        ((col + 1) * self.grid_width, (row + 1) * self.grid_height)
                    ]
                    has_corner_in_circle = False
                    for (x, y) in node_corners:
                        dist_sq = (x - right_circle_center[0]) ** 2 + (y - right_circle_center[1]) ** 2
                        if dist_sq <= (radius ** 2) + self.tolerance:
                            has_corner_in_circle = True
                            break
                    if has_corner_in_circle:
                        for dr, dc in neighbor_offsets:
                            nr = np.clip(row + dr, 0, self.mesh_N)
                            nc = np.clip(col + dc, 0, self.mesh_M)
                            vem[nr][nc] = 1

        return vem

    def _get_vem_for_position(self, component: Dict, node_row: int, node_col: int) -> np.ndarray:
        """获取元件在指定节点位置的VEM矩阵（支持旋转）"""
        center = self._node_to_physical(node_row, node_col)
        return self._discretize_component(component, center)

    def _identify_feasible_region(self, component: Dict, placed_vems: List[np.ndarray]) -> np.ndarray:
        """识别可行布局区域（支持胶囊旋转）"""
        integrated_evem = np.zeros(self.total_nodes, dtype=int)

        # 1. 检查与布局容器的约束
        if component["shape"] == "rect":
            w, h = component["width"], component["height"]
            min_valid_x = w / 2
            max_valid_x = self.layout_width - w / 2
            min_valid_y = h / 2
            max_valid_y = self.layout_height - h / 2

        elif component["shape"] == "circle":
            r = component["radius"]
            min_valid_x = r
            max_valid_x = self.layout_width - r
            min_valid_y = r
            max_valid_y = self.layout_height - r

        elif component["shape"] == "capsule":
            length, width = component["length"], component["width"]
            rotation = component.get("rotation", 0)  # 考虑旋转

            if rotation == 0:
                # 横向：长轴沿X轴，长度方向需X空间
                min_valid_x = length / 2
                max_valid_x = self.layout_width - length / 2
                min_valid_y = width / 2
                max_valid_y = self.layout_height - width / 2
            else:
                # 纵向：长轴沿Y轴，长度方向需Y空间
                min_valid_x = width / 2  # X方向只需宽度的一半
                max_valid_x = self.layout_width - width / 2
                min_valid_y = length / 2  # Y方向需要长度的一半
                max_valid_y = self.layout_height - length / 2

        # 标记超出边界的位置为不可行
        for row in range(self.total_nodes[0]):
            for col in range(self.total_nodes[1]):
                x, y = self._node_to_physical(row, col)
                if x < min_valid_x or x > max_valid_x or y < min_valid_y or y > max_valid_y:
                    integrated_evem[row][col] = 1

        # 2. 检查与已放置元件的约束
        for placed_vem in placed_vems:
            integrated_evem = np.logical_or(integrated_evem, placed_vem).astype(int)

        return integrated_evem

    def _sample_feasible_position(self, component: Dict, feasible_region: np.ndarray, max_sampling_attempts) -> Tuple[
        int, int]:
        """在可行区域中随机采样位置（通用逻辑不变）"""
        zero_indices = np.argwhere(feasible_region == 0)
        if not zero_indices.size:
            return None

        for _ in range(max_sampling_attempts):
            sampled_node = tuple(zero_indices[random.randint(0, len(zero_indices) - 1)])
            row, col = sampled_node

            temp_component_vem = self._get_vem_for_position(component, row, col)
            overlap = False
            for placed_vem in self.placed_vems:
                if np.any(np.logical_and(temp_component_vem, placed_vem)):
                    overlap = True
                    break

            if not overlap:
                return sampled_node

        return None

    def _node_to_physical(self, node_row: int, node_col: int) -> Tuple[float, float]:
        """网格节点坐标转物理坐标"""
        return (
            node_col * self.grid_width,
            node_row * self.grid_height
        )

    def layout_sampling(self, components: List[Dict], max_sampling_attempts: int) -> List[Dict]:
        """执行布局采样（支持旋转胶囊）"""
        self._check_component_size_vs_grid(components)
        self.VEM0 = np.zeros(self.total_nodes, dtype=int)
        self.layout_history = []
        self.placed_vems = []

        # 按面积降序排序
        components_sorted = sorted(components, key=self._calculate_component_area, reverse=True)

        placed_components = []
        self.layout_history.append(([], np.copy(self.VEM0)))

        for component in components_sorted:
            feasible_region = self._identify_feasible_region(component, self.placed_vems)
            sampled_node = self._sample_feasible_position(component, feasible_region, max_sampling_attempts)

            if sampled_node is None:
                print(f"警告：无法为元件 ID {component['id']} 找到合适位置")
                continue

            physical_center = self._node_to_physical(*sampled_node)

            component_with_center = component.copy()
            component_with_center["center"] = physical_center
            # component_with_center["node_position"] = sampled_node

            component_vem = self._discretize_component(component, physical_center)
            self.placed_vems.append(component_vem)
            placed_components.append(component_with_center)

            self.VEM0 = np.logical_or(self.VEM0, component_vem).astype(int)
            self.layout_history.append((placed_components.copy(), np.copy(self.VEM0)))

        return placed_components

    def visualize_layout(self, components: List[Dict], show_vem: bool = False, save_path: Optional[str] = None):
        """可视化布局（支持旋转胶囊）"""
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_xlim(0, self.layout_width)
        ax.set_ylim(0, self.layout_height)
        ax.set_aspect('equal')
        ax.set_title("SeqLS Final Layout")
        ax.set_xlabel("X Position (m)")
        ax.set_ylabel("Y Position (m)")

        # # 绘制网格线
        # for x in np.arange(0, self.layout_width, self.grid_width):
        #     ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
        # for y in np.arange(0, self.layout_height, self.grid_height):
        #     ax.axhline(y, color='gray', linestyle='--', linewidth=0.5)

        # 绘制元件
        for i, component in enumerate(components):
            cx, cy = component["center"]
            color = f"C{i}"
            shape = component["shape"]

            if shape == "rect":
                w, h = component["width"], component["height"]
                rect = Rectangle(
                    (cx - w / 2, cy - h / 2),
                    w, h,
                    fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                )
                ax.add_patch(rect)

            elif shape == "circle":
                r = component["radius"]
                circle = Circle(
                    (cx, cy), r,
                    fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                )
                ax.add_patch(circle)

            elif shape == "capsule":
                length, width = component["length"], component["width"]
                rotation = component.get("rotation", 0)
                radius = width / 2
                rect_length = length - width

                if rotation == 0:
                    # 横向：中间矩形沿X轴
                    rect = Rectangle(
                        (cx - rect_length / 2, cy - radius),
                        rect_length, width,
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    )
                    ax.add_patch(rect)
                    # 左右半圆
                    ax.add_patch(Circle(
                        (cx - rect_length / 2, cy), radius,
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    ))
                    ax.add_patch(Circle(
                        (cx + rect_length / 2, cy), radius,
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    ))
                else:
                    # 纵向：中间矩形沿Y轴
                    rect = Rectangle(
                        (cx - radius, cy - rect_length / 2),  # 左下角坐标
                        width, rect_length,  # 宽（X）、高（Y）
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    )
                    ax.add_patch(rect)
                    # 上下半圆
                    ax.add_patch(Circle(
                        (cx, cy - rect_length / 2), radius,
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    ))
                    ax.add_patch(Circle(
                        (cx, cy + rect_length / 2), radius,
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    ))

            ax.text(
                cx, cy,
                f"ID: {component['id']}\nPower: {component['power']}W",
                ha='center', va='center', fontsize=7, color='white', fontweight='bold'
            )

        if show_vem:
            covered_nodes = np.argwhere(self.VEM0 == 1)
            for (row, col) in covered_nodes:
                x, y = self._node_to_physical(row, col)
                ax.scatter(x, y, color='red', s=8, alpha=0.6)

        plt.tight_layout()
        if save_path is not None:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图像已保存至：{save_path}")
        else:
            plt.show()
        plt.close()

    def visualize_layout_process(self):
        """可视化布局过程（支持旋转胶囊）"""
        num_steps = len(self.layout_history)
        fig, axes = plt.subplots(1, num_steps, figsize=(5 * num_steps, 5))

        if num_steps == 1:
            axes = [axes]

        for i, (components, vem) in enumerate(self.layout_history):
            ax = axes[i]
            ax.set_xlim(0, self.layout_width)
            ax.set_ylim(0, self.layout_height)
            ax.set_aspect('equal')
            ax.set_title(f"Step {i}: {len(components)} components")

            # for x in np.arange(0, self.layout_width, self.grid_width):
            #     ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
            # for y in np.arange(0, self.layout_height, self.grid_height):
            #     ax.axhline(y, color='gray', linestyle='--', linewidth=0.5)

            for j, component in enumerate(components):
                cx, cy = component["center"]
                color = f"C{comp['id']}"
                shape = component["shape"]

                if shape == "rect":
                    w, h = component["width"], component["height"]
                    rect = Rectangle(
                        (cx - w / 2, cy - h / 2), w, h,
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    )
                    ax.add_patch(rect)

                elif shape == "circle":
                    r = component["radius"]
                    circle = Circle(
                        (cx, cy), r,
                        fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                    )
                    ax.add_patch(circle)

                elif shape == "capsule":
                    length, width = component["length"], component["width"]
                    rotation = component.get("rotation", 0)
                    radius = width / 2
                    rect_length = length - width

                    if rotation == 0:
                        rect = Rectangle(
                            (cx - rect_length / 2, cy - radius),
                            rect_length, width,
                            fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                        )
                        ax.add_patch(rect)
                        ax.add_patch(Circle(
                            (cx - rect_length / 2, cy), radius,
                            fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                        ))
                        ax.add_patch(Circle(
                            (cx + rect_length / 2, cy), radius,
                            fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                        ))
                    else:
                        rect = Rectangle(
                            (cx - radius, cy - rect_length / 2),
                            width, rect_length,
                            fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                        )
                        ax.add_patch(rect)
                        ax.add_patch(Circle(
                            (cx, cy - rect_length / 2), radius,
                            fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                        ))
                        ax.add_patch(Circle(
                            (cx, cy + rect_length / 2), radius,
                            fill=True, facecolor=color, edgecolor='black', linewidth=2, alpha=0.7
                        ))

                ax.text(
                    cx, cy,
                    f"ID: {component['id']}",
                    ha='center', va='center', fontsize=7, color='white', fontweight='bold'
                )

            covered_nodes = np.argwhere(vem == 1)
            for (row, col) in covered_nodes:
                x, y = self._node_to_physical(row, col)
                ax.scatter(x, y, color='red', s=5, alpha=0.5)

        plt.tight_layout()
        plt.show()


# 示例调用（含旋转胶囊）
if __name__ == "__main__":
    random.seed(42)
    layout_domain = (0.1, 0.1)  # 0.1m×0.1m布局域
    mesh_size = (256, 256)
    seq_ls = SeqLS(layout_domain, mesh_size)

    # 定义带旋转的胶囊元件
    components = [
        {"id": 0, "shape": "capsule", "length": 0.048, "width": 0.012, "rotation": 0, "power": 8000},  # 横向
        {"id": 1, "shape": "capsule", "length": 0.048, "width": 0.012, "rotation": 90, "power": 8000},  # 纵向
        {"id": 2, "shape": "rect", "width": 0.024, "height": 0.024, "power": 6000},
        {"id": 3, "shape": "circle", "radius": 0.012, "power": 5000},
    ]

    max_attempts = 500
    result = seq_ls.layout_sampling(components, max_attempts)
    if result:
        print("布局成功！元件信息：")
        for comp in result:
            cx, cy = comp['center']
            print(
                f"元件 ID: {comp['id']}, 形状: {comp['shape']}, 旋转: {comp.get('rotation', 0)}, 中心: ({cx:.3f}, {cy:.3f})")
        seq_ls.visualize_layout(result, save_path="rotated_capsule_layout.png")
