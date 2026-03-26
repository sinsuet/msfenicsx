'''
Author: wangqineng zhet3988009@gmail.com
Description: 封装所有可视化相关的工具函数，无需初始化类，直接调用
'''
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Optional
from scipy.spatial.distance import cdist
from shapely.geometry import LineString, Point
from matplotlib.patches import Rectangle, Circle
def plot_cooling_sdf(sdf_matrix: np.ndarray, x_range: Tuple[float, float],
                     y_range: Tuple[float, float], save_path: str) -> None:
    """可视化散热口的SDF"""
    plt.figure(figsize=(8, 6))
    im = plt.imshow(
        sdf_matrix,
        extent=[x_range[0], x_range[1], y_range[0], y_range[1]],
        cmap='bwr',  # 颜色映射可自定义
        origin="lower"
    )
    plt.colorbar(im, label="Signed Distance (m)")
    plt.title("Cooling Lines SDF")
    plt.xlabel("X Coordinate (m)")
    plt.ylabel("Y Coordinate (m)")
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
def compute_cooling_sdf(cooling_lines: List[Dict], X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """计算散热线段的符号距离场（SDF）

    Args:
        cooling_lines: 散热线段列表（含端点坐标）
        X, Y: 网格的X、Y坐标矩阵（meshgrid生成）
    Returns:
        sdf: 每个网格点到最近散热线段的距离（浮点矩阵）
    """
    sdf = np.ones_like(X) * float('inf')  # 初始化为无穷大（表示远离所有线段）
    for line in cooling_lines:
        endpoints = line["endpoints"]
        line_geom = LineString(endpoints)  # 转换为Shapely线段对象
        # 遍历每个网格点，计算到线段的距离
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                x, y = X[i, j], Y[i, j]
                point = Point(x, y)
                dist = line_geom.distance(point)
                sdf[i, j] = min(sdf[i, j], dist)  # 保留到最近线段的距离
    # 可根据需求添加“符号”（如线段内部为负、外部为正），此处简化为“到线段的最短距离”
    return sdf
def plot_layout(
        components: List[Dict],
        layout_domain: Tuple[float, float],
        mesh_size: Tuple[int, int],
        save_path: Optional[str] = None
):
    """绘制布局图（支持胶囊横向/纵向旋转）"""
    layout_width, layout_height = layout_domain
    mesh_N, mesh_M = mesh_size
    grid_width = layout_width / mesh_M  # x方向网格单元尺寸
    grid_height = layout_height / mesh_N  # y方向网格单元尺寸

    plt.figure(figsize=(8, 6))
    ax = plt.gca()
    ax.set_xlim(0, layout_width)
    ax.set_ylim(0, layout_height)
    ax.set_aspect('equal')
    ax.set_title("Component Layout")
    ax.set_xlabel("X Coordinate (m)")
    ax.set_ylabel("Y Coordinate (m)")
    ax.set_xticks([])  # 隐藏x轴刻度
    ax.set_yticks([])  # 隐藏y轴刻度

    # 绘制元件
    for comp in components:
        cx, cy = comp["center"]
        color = f"C{comp['id']}"  # 按ID分配颜色

        if comp["shape"] == "rect":
            # 矩形绘制逻辑不变
            w, h = comp["width"], comp["height"]
            rect = Rectangle(
                (cx - w / 2, cy - h / 2), w, h,
                fill=True, facecolor=color, edgecolor='none', alpha=0.7)
            ax.add_patch(rect)

        elif comp["shape"] == "circle":
            # 圆形绘制逻辑不变
            r = comp["radius"]
            circle = Circle(
                (cx, cy), r,
                fill=True, facecolor=color, edgecolor='none', alpha=0.7)
            ax.add_patch(circle)

        elif comp["shape"] == "capsule":
            # 胶囊绘制逻辑（新增旋转支持）
            length = comp["length"]
            width = comp["width"]
            rotation = comp.get("rotation", 0)  # 获取旋转角度（默认0°）
            radius = width / 2
            rect_len = length - width  # 中间矩形的长度

            if rotation == 0:
                # 横向：长轴沿X轴（原有逻辑）
                # 中间矩形（x方向延伸）
                rect = Rectangle(
                    (cx - rect_len / 2, cy - radius),  # 左下角坐标
                    rect_len, width,  # 宽（x方向）、高（y方向）
                    fill=True, facecolor=color, edgecolor='none', alpha=0.7)
                ax.add_patch(rect)
                # 两端半圆（左右分布）
                ax.add_patch(Circle((cx - rect_len / 2, cy), radius,
                                    fill=True, facecolor=color, edgecolor='none', alpha=0.7))
                ax.add_patch(Circle((cx + rect_len / 2, cy), radius,
                                    fill=True, facecolor=color, edgecolor='none', alpha=0.7))

            elif rotation == 90:
                # 纵向：长轴沿Y轴（新增逻辑）
                # 中间矩形（y方向延伸）
                rect = Rectangle(
                    (cx - radius, cy - rect_len / 2),  # 左下角坐标
                    width, rect_len,  # 宽（x方向）、高（y方向）
                    fill=True, facecolor=color, edgecolor='none', alpha=0.7)
                ax.add_patch(rect)
                # 两端半圆（上下分布）
                ax.add_patch(Circle((cx, cy - rect_len / 2), radius,
                                    fill=True, facecolor=color, edgecolor='none', alpha=0.7))
                ax.add_patch(Circle((cx, cy + rect_len / 2), radius,
                                    fill=True, facecolor=color, edgecolor='none', alpha=0.7))

        # 标注元件信息（ID和功率）
        ax.text(
            cx, cy,
            # f"ID: {comp['id']}\n{comp['power']}W",
            f"ID: {comp['id']}\n{comp['total_power']}W",
            ha='center', va='center', fontsize=11, color='black', fontweight='bold'
        )

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    plt.close()
def plot_sdf(
        sdf_matrix: np.ndarray,
        x_range: Tuple[float, float],
        y_range: Tuple[float, float],
        save_path: Optional[str] = None
):
    """绘制有符号距离场（SDF）"""
    plt.figure(figsize=(8, 6))
    # 蓝-白-红配色：内部（负）-边界（0）-外部（正）
    im = plt.imshow(
        sdf_matrix,
        cmap='bwr',
        aspect='auto',
        origin='lower',
        extent=[x_range[0], x_range[1], y_range[0], y_range[1]],
        vmin=-0.02,  # 距离范围（根据布局域调整）
        vmax=0.02
    )
    cbar = plt.colorbar(im)
    cbar.set_label('Signed Distance (m)')
    plt.xlabel('X Coordinate (m)')
    plt.ylabel('Y Coordinate (m)')
    plt.title('Signed Distance Field (SDF)')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()
def plot_temperature_field(
        temp_matrix: np.ndarray,  # 256×256插值后的矩阵
        x_range: Tuple[float, float],  # 实际x坐标范围
        y_range: Tuple[float, float],  # 实际y坐标范围
        save_path: Optional[str] = None
):
    """绘制插值后的温度场（使用实际坐标范围）"""
    plt.figure(figsize=(8, 6))
    im = plt.imshow(
        temp_matrix,
        cmap='jet',  # plasma viridis magma cividis inferno
        aspect='auto',
        origin='lower',
        extent=[x_range[0], x_range[1], y_range[0], y_range[1]]  # 基于实际坐标
    )

    cbar = plt.colorbar(im)
    cbar.set_label('Temperature (K)')
    plt.xlabel('X Coordinate (m)')
    plt.ylabel('Y Coordinate (m)')
    plt.title('2D Temperature Field')
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        # print(f"温度场图已保存至: {save_path}")
        plt.close()
    else:
        plt.show()
        plt.close()

def plot_heat_source(
        source_matrix: np.ndarray,
        layout_domain: Tuple[float, float],
        cooling_lines: List[Dict],
        save_path: Optional[str] = None
):
    """绘制热源矩阵（叠加散热线段）- 逻辑不变，适配从JSON加载的线段格式"""
    plt.figure(figsize=(6, 6))
    domain_width, domain_height = layout_domain

    # 绘制热源矩阵
    im = plt.imshow(
        source_matrix,
        cmap='hot',
        aspect='equal',
        origin='lower',
        extent=[0, domain_width, 0, domain_height]
    )

    # 绘制散热线段（逻辑不变，兼容JSON加载的endpoints格式）
    for idx, line in enumerate(cooling_lines, 1):
        # 从JSON加载的endpoints是列表，转为元组（与函数原逻辑兼容）
        (x1, y1), (x2, y2) = tuple(line["endpoints"][0]), tuple(line["endpoints"][1])
        # 双线叠加增强对比
        plt.plot([x1, x2], [y1, y2], 'k-', linewidth=4, alpha=0.8)
        plt.plot([x1, x2], [y1, y2], 'w-', linewidth=3, alpha=0.9)
        # 端点标记（第一条线显示图例）
        if idx == 1:
            plt.plot(x1, y1, 'ko', markersize=8)
            plt.plot(x1, y1, 'wo', markersize=6)
            plt.plot(x2, y2, 'ko', markersize=8)
            plt.plot(x2, y2, 'wo', markersize=6)
        else:
            plt.plot(x1, y1, 'ko', markersize=8)
            plt.plot(x1, y1, 'wo', markersize=6)
            plt.plot(x2, y2, 'ko', markersize=8)
            plt.plot(x2, y2, 'wo', markersize=6)

    # 颜色条、标签等
    cbar = plt.colorbar(im, label='Heat Flux (W/m²)', shrink=0.8, pad=0.05)
    cbar.ax.set_ylabel(cbar.ax.get_ylabel(), fontsize=10)
    plt.xlabel('X (m)', fontsize=12)
    plt.ylabel('Y (m)', fontsize=12)
    plt.title('Heat Source Distribution with Cooling Lines', fontsize=14, pad=15)

    # 刻度优化
    plt.xticks(np.linspace(0, domain_width, 6), fontsize=10)
    plt.yticks(np.linspace(0, domain_height, 6), fontsize=10)

    # 保存或显示（高分辨率）
    if save_path:
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
    else:
        plt.show()

def compute_sdf(components: List[Dict], grid_x: np.ndarray, grid_y: np.ndarray) -> np.ndarray:
    """计算有符号距离场（SDF），支持胶囊旋转"""
    sdf = np.full_like(grid_x, np.inf)
    h, w = grid_x.shape
    points = np.stack([grid_x.ravel(), grid_y.ravel()], axis=1)

    for comp in components:
        shape = comp["shape"]
        cx, cy = comp["center"]

        if shape == "rect":
            w_rect, h_rect = comp["width"], comp["height"]
            x_min, x_max = cx - w_rect / 2, cx + w_rect / 2
            y_min, y_max = cy - h_rect / 2, cy + h_rect / 2

            dx = np.max([x_min - points[:, 0], points[:, 0] - x_max, np.zeros_like(points[:, 0])], axis=0)
            dy = np.max([y_min - points[:, 1], points[:, 1] - y_max, np.zeros_like(points[:, 1])], axis=0)
            dist = np.sqrt(dx ** 2 + dy ** 2)

            inside = (points[:, 0] >= x_min) & (points[:, 0] <= x_max) & \
                     (points[:, 1] >= y_min) & (points[:, 1] <= y_max)
            dist[inside] = -np.min([
                points[:, 0][inside] - x_min,
                x_max - points[:, 0][inside],
                points[:, 1][inside] - y_min,
                y_max - points[:, 1][inside]
            ], axis=0)

        elif shape == "circle":
            r = comp["radius"]
            dist = cdist(points, [[cx, cy]]).ravel() - r

        elif shape == "capsule":
            length = comp["length"]
            width = comp["width"]
            rotation = comp.get("rotation", 0)  # 0=横向(X轴), 90=纵向(Y轴)
            r = width / 2
            rect_len = length - width  # 中间矩形长度

            if rotation == 0:
                p1 = np.array([cx - rect_len / 2, cy])
                p2 = np.array([cx + rect_len / 2, cy])
            elif rotation == 90:
                p1 = np.array([cx, cy - rect_len / 2])
                p2 = np.array([cx, cy + rect_len / 2])
            else:
                raise ValueError(f"不支持的旋转角度: {rotation}")

            vec = p2 - p1
            t = np.clip(((points - p1) @ vec) / (vec @ vec + 1e-8), 0, 1)
            closest = p1 + t[:, None] * vec
            dist_line = np.linalg.norm(points - closest, axis=1) - r

            dist_circle1 = cdist(points, [p1]).ravel() - r
            dist_circle2 = cdist(points, [p2]).ravel() - r
            dist = np.min([dist_line, dist_circle1, dist_circle2], axis=0)

        else:
            raise ValueError(f"不支持的形状: {shape}")

        sdf = np.min([sdf, dist.reshape(h, w)], axis=0)

    return sdf