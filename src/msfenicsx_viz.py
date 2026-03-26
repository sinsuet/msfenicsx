from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.tri as mtri
import numpy as np
import plotly.graph_objects as go


@dataclass(frozen=True)
class ComponentRect:
    name: str
    label: int
    x0: float
    y0: float
    width: float
    height: float
    conductivity: float
    heat_source: float

    @property
    def x1(self) -> float:
        return self.x0 + self.width

    @property
    def y1(self) -> float:
        return self.y0 + self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x0 + 0.5 * self.width, self.y0 + 0.5 * self.height)


def default_component_layout() -> list[ComponentRect]:
    return [
        ComponentRect(
            name="base_plate",
            label=1,
            x0=0.0,
            y0=0.0,
            width=1.20,
            height=0.20,
            conductivity=12.0,
            heat_source=0.0,
        ),
        ComponentRect(
            name="chip",
            label=2,
            x0=0.45,
            y0=0.20,
            width=0.30,
            height=0.12,
            conductivity=45.0,
            heat_source=15000.0,
        ),
        ComponentRect(
            name="heat_spreader",
            label=3,
            x0=0.25,
            y0=0.32,
            width=0.70,
            height=0.10,
            conductivity=90.0,
            heat_source=0.0,
        ),
    ]


def summarize_values_by_component(
    component_names: list[str],
    labels: np.ndarray,
    values: np.ndarray,
) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    labels = np.asarray(labels)
    values = np.asarray(values)
    for idx, name in enumerate(component_names, start=1):
        mask = labels == idx
        selected = values[mask]
        if selected.size == 0:
            summary[name] = {"count": 0, "min": np.nan, "max": np.nan, "mean": np.nan}
            continue
        summary[name] = {
            "count": int(selected.size),
            "min": float(selected.min()),
            "max": float(selected.max()),
            "mean": float(selected.mean()),
        }
    return summary


def build_triangulation(V) -> tuple[np.ndarray, np.ndarray, mtri.Triangulation]:
    coords = V.tabulate_dof_coordinates()[:, :2]
    cells = np.asarray(V.dofmap.list, dtype=np.int32)
    triangulation = mtri.Triangulation(coords[:, 0], coords[:, 1], cells)
    return coords, cells, triangulation


def component_cell_labels(cell_tags, num_cells: int) -> np.ndarray:
    labels = np.zeros(num_cells, dtype=np.int32)
    labels[np.asarray(cell_tags.indices, dtype=np.int32)] = np.asarray(cell_tags.values, dtype=np.int32)
    return labels


def summarize_solution_by_component(layout, cell_tags, V, uh) -> dict[str, dict[str, float]]:
    cell_label_array = component_cell_labels(cell_tags, len(V.dofmap.list))
    dofmap = np.asarray(V.dofmap.list, dtype=np.int32)
    summary: dict[str, dict[str, float]] = {}
    for component in layout:
        cells = np.where(cell_label_array == component.label)[0]
        if cells.size == 0:
            summary[component.name] = {"count": 0, "min": np.nan, "max": np.nan, "mean": np.nan}
            continue
        dofs = np.unique(dofmap[cells].ravel())
        values = uh.x.array[dofs]
        summary[component.name] = {
            "count": int(values.size),
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": float(values.mean()),
        }
    return summary


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_layout_figure(layout: list[ComponentRect], path: Path) -> None:
    ensure_parent(path)
    fig, ax = plt.subplots(figsize=(8, 3))
    colors = ["#9ecae1", "#fdae6b", "#a1d99b"]
    for color, component in zip(colors, layout, strict=True):
        rect = patches.Rectangle(
            (component.x0, component.y0),
            component.width,
            component.height,
            facecolor=color,
            edgecolor="black",
            linewidth=1.5,
            alpha=0.85,
        )
        ax.add_patch(rect)
        ax.text(*component.center, component.name, ha="center", va="center", fontsize=10)
    ax.set_title("Initial Component Layout")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal")
    ax.set_xlim(-0.05, max(component.x1 for component in layout) + 0.05)
    ax.set_ylim(-0.02, max(component.y1 for component in layout) + 0.05)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_mesh_figure(triangulation: mtri.Triangulation, path: Path) -> None:
    ensure_parent(path)
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.triplot(triangulation, color="#3c3c3c", linewidth=0.5)
    ax.set_title("Mesh")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_subdomain_figure(
    triangulation: mtri.Triangulation,
    cell_labels: np.ndarray,
    layout: list[ComponentRect],
    path: Path,
) -> None:
    ensure_parent(path)
    fig, ax = plt.subplots(figsize=(8, 3))
    collection = ax.tripcolor(
        triangulation,
        facecolors=cell_labels,
        edgecolors="black",
        linewidth=0.2,
        cmap="Set2",
    )
    for component in layout:
        ax.text(*component.center, component.name, ha="center", va="center", fontsize=9)
    ax.set_title("Component Subdomains")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal")
    colorbar = fig.colorbar(collection, ax=ax)
    colorbar.set_label("Component label")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_temperature_figure(
    triangulation: mtri.Triangulation,
    nodal_values: np.ndarray,
    path: Path,
) -> None:
    ensure_parent(path)
    fig, ax = plt.subplots(figsize=(8, 3))
    contour = ax.tricontourf(triangulation, nodal_values, levels=30, cmap="inferno")
    ax.set_title("Temperature Field")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal")
    fig.colorbar(contour, ax=ax, label="Temperature (degC)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_temperature_html(
    coords: np.ndarray,
    cells: np.ndarray,
    nodal_values: np.ndarray,
    layout: list[ComponentRect],
    path: Path,
) -> None:
    ensure_parent(path)
    hover_text = [
        f"x={x:.4f} m<br>y={y:.4f} m<br>T={t:.4f} degC"
        for (x, y), t in zip(coords, nodal_values, strict=True)
    ]
    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=coords[:, 0],
                y=coords[:, 1],
                z=nodal_values,
                i=cells[:, 0],
                j=cells[:, 1],
                k=cells[:, 2],
                intensity=nodal_values,
                colorscale="Inferno",
                colorbar={"title": "Temperature (degC)"},
                flatshading=True,
                hovertext=hover_text,
                hoverinfo="text",
                showscale=True,
            )
        ]
    )
    label_height = float(nodal_values.max()) * 1.05 if len(nodal_values) else 0.0
    for component in layout:
        cx, cy = component.center
        fig.add_trace(
            go.Scatter3d(
                x=[cx],
                y=[cy],
                z=[label_height],
                mode="text",
                text=[component.name],
                showlegend=False,
                textfont={"size": 12},
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        title="Interactive Temperature Field",
        scene={
            "xaxis_title": "x (m)",
            "yaxis_title": "y (m)",
            "zaxis_title": "Temperature (degC)",
            "camera": {"eye": {"x": 1.5, "y": -1.8, "z": 0.9}},
            "aspectmode": "data",
        },
        margin={"l": 0, "r": 0, "b": 0, "t": 40},
    )
    # Bundle Plotly into the HTML so opening the file directly works offline
    # and does not depend on an external CDN request.
    fig.write_html(path, include_plotlyjs=True, full_html=True)


def write_summary_text(
    path: Path,
    *,
    num_cells: int,
    num_vertices: int,
    temperature_min: float,
    temperature_max: float,
    component_summary: dict[str, dict[str, float]],
    units: dict[str, str] | None = None,
    reference_conditions: dict[str, float] | None = None,
) -> None:
    ensure_parent(path)
    units = units or {}
    reference_conditions = reference_conditions or {}
    temperature_unit = units.get("temperature", "degC")
    lines = [
        f"num_cells: {num_cells}",
        f"num_vertices: {num_vertices}",
        f"temperature_min ({temperature_unit}): {temperature_min:.6f}",
        f"temperature_max ({temperature_unit}): {temperature_max:.6f}",
    ]
    if reference_conditions:
        for key, value in reference_conditions.items():
            lines.append(f"{key} ({temperature_unit}): {float(value):.6f}")
    lines.extend(
        [
            "",
            "component_summary:",
        ]
    )
    for name, stats in component_summary.items():
        lines.append(
            f"  - {name}: count={stats['count']}, min={stats['min']:.6f}, "
            f"max={stats['max']:.6f}, mean={stats['mean']:.6f} ({temperature_unit})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_overview_html(
    path: Path,
    *,
    layout: list[ComponentRect],
    layout_png: Path,
    mesh_png: Path,
    subdomains_png: Path,
    temperature_png: Path,
    temperature_html: Path,
    summary_txt: Path,
    component_summary: dict[str, dict[str, float]],
    units: dict[str, str] | None = None,
    reference_conditions: dict[str, float] | None = None,
) -> None:
    ensure_parent(path)
    units = units or {}
    reference_conditions = reference_conditions or {}
    layout_name = layout_png.name
    mesh_name = mesh_png.name
    subdomains_name = subdomains_png.name
    temperature_png_name = temperature_png.name
    temperature_html_name = temperature_html.name
    summary_rel = Path(os.path.relpath(summary_txt, start=path.parent))
    x_min = min(component.x0 for component in layout)
    x_max = max(component.x1 for component in layout)
    y_max = max(component.y1 for component in layout)
    temperature_unit = units.get("temperature", "degC")
    conductivity_unit = units.get("conductivity", "W/(m*K)")
    heat_source_unit = units.get("heat_source", "W/m^3")
    ambient_text = ""
    if reference_conditions:
        sink_temp = reference_conditions.get(
            "cold_sink_temperature",
            reference_conditions.get("ambient_temperature"),
        )
        ambient_text = f" 当前案例采用 SI 风格教学单位，冷端参考温度为 {sink_temp} {temperature_unit}。"

    stats_cards = []
    for component in layout:
        stats = component_summary[component.name]
        stats_cards.append(
            f"""
            <div class="legend-item">
              <strong>{component.name}</strong>
              k = {component.conductivity:.1f} {conductivity_unit}, q = {component.heat_source:.1f} {heat_source_unit}<br>
              min = {stats['min']:.4f} {temperature_unit}<br>
              max = {stats['max']:.4f} {temperature_unit}<br>
              mean = {stats['mean']:.4f} {temperature_unit}
            </div>
            """
        )
    stats_html = "\n".join(stats_cards)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Multicomponent Heat Overview</title>
  <style>
    :root {{
      --bg: #f6f2ea;
      --panel: #fffdf9;
      --ink: #222;
      --muted: #625e57;
      --line: #d9d0c2;
      --accent: #a44a3f;
      --accent-soft: #f3d6cf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff7e8 0, transparent 24rem),
        linear-gradient(180deg, #f8f1e7 0%, var(--bg) 100%);
    }}
    .shell {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      background: rgba(255,255,255,0.72);
      backdrop-filter: blur(8px);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 12px 40px rgba(60, 45, 30, 0.08);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 2rem;
    }}
    .subtitle {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 20px 0 16px;
    }}
    .tab-button {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.9);
      color: var(--ink);
      padding: 10px 14px;
      border-radius: 999px;
      cursor: pointer;
      font-size: 0.95rem;
    }}
    .tab-button.active {{
      background: var(--accent);
      color: white;
      border-color: var(--accent);
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(0, 3fr) minmax(280px, 1fr);
      gap: 20px;
      margin-top: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 16px;
      box-shadow: 0 8px 30px rgba(60, 45, 30, 0.06);
    }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}
    .image-frame {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      overflow: hidden;
      background: #fff;
    }}
    img {{
      width: 100%;
      height: auto;
      display: block;
    }}
    iframe {{
      width: 100%;
      min-height: 720px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: white;
    }}
    .caption {{
      margin: 10px 2px 0;
      color: var(--muted);
      line-height: 1.6;
    }}
    .summary-link {{
      display: inline-block;
      margin-top: 14px;
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }}
    .legend {{
      display: grid;
      gap: 10px;
    }}
    .legend-item {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .legend-item strong {{
      display: block;
      margin-bottom: 6px;
    }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      iframe {{ min-height: 540px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>2D Multicomponent Heat Dashboard</h1>
      <p class="subtitle">
        用一个页面同时查看组件布局、有限元网格、子区域分区和交互式温度场。
        推荐按从左到右的学习顺序看：先理解布局，再看网格和分区，最后再读温度场。{ambient_text}
      </p>
      <div class="toolbar">
        <button class="tab-button active" data-tab="layout">Layout</button>
        <button class="tab-button" data-tab="mesh">Mesh</button>
        <button class="tab-button" data-tab="subdomains">Subdomains</button>
        <button class="tab-button" data-tab="physics">Physics</button>
        <button class="tab-button" data-tab="temperature">Temperature</button>
      </div>
      <div class="grid">
        <div class="panel">
          <div class="tab-panel active" data-panel="layout">
            <div class="image-frame"><img src="{layout_name}" alt="Initial component layout"></div>
            <p class="caption">先看组件初始摆放。底板在下方，芯片在中间，扩展块在上方。</p>
          </div>
          <div class="tab-panel" data-panel="mesh">
            <div class="image-frame"><img src="{mesh_name}" alt="Finite element mesh"></div>
            <p class="caption">再看网格是如何把连续几何切成小三角形单元，这一步决定了有限元怎么离散求解。</p>
          </div>
          <div class="tab-panel" data-panel="subdomains">
            <div class="image-frame"><img src="{subdomains_name}" alt="Subdomain labels"></div>
            <p class="caption">每个颜色块代表一个组件分区，材料参数和热源都是依赖这些分区标签分配的。</p>
          </div>
          <div class="tab-panel" data-panel="physics">
            <div class="image-frame">
              <svg viewBox="-0.08 -0.05 1.36 0.58" style="display:block;width:100%;height:auto;background:white">
                <defs>
                  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#a44a3f"></polygon>
                  </marker>
                </defs>
                <rect x="0" y="0" width="1.20" height="0.20" fill="#9ecae1" stroke="#222" stroke-width="0.01"></rect>
                <rect x="0.45" y="0.20" width="0.30" height="0.12" fill="#fdae6b" stroke="#222" stroke-width="0.01"></rect>
                <rect x="0.25" y="0.32" width="0.70" height="0.10" fill="#a1d99b" stroke="#222" stroke-width="0.01"></rect>
                <text x="0.60" y="0.10" text-anchor="middle" font-size="0.045">base_plate</text>
                <text x="0.60" y="0.26" text-anchor="middle" font-size="0.045">chip</text>
                <text x="0.60" y="0.37" text-anchor="middle" font-size="0.045">heat_spreader</text>

                <line x1="{x_min}" y1="0.02" x2="{x_min}" y2="{y_max}" stroke="#205493" stroke-width="0.012"></line>
                <line x1="{x_max}" y1="0.02" x2="{x_max}" y2="{y_max}" stroke="#205493" stroke-width="0.012"></line>
                <text x="-0.03" y="0.46" text-anchor="start" font-size="0.040" fill="#205493">Cold boundary</text>
                <text x="1.02" y="0.46" text-anchor="start" font-size="0.040" fill="#205493">Cold boundary</text>

                <line x1="0.60" y1="0.24" x2="0.60" y2="0.14" stroke="#a44a3f" stroke-width="0.010" marker-end="url(#arrowhead)"></line>
                <text x="0.63" y="0.16" font-size="0.040" fill="#a44a3f">Heat source in chip</text>

                <line x1="0.15" y1="-0.01" x2="0.30" y2="-0.01" stroke="#666" stroke-width="0.008"></line>
                <line x1="0.90" y1="-0.01" x2="1.05" y2="-0.01" stroke="#666" stroke-width="0.008"></line>
                <text x="0.16" y="-0.025" font-size="0.036" fill="#666">Insulated boundary</text>
                <text x="0.79" y="-0.025" font-size="0.036" fill="#666">Insulated boundary</text>
              </svg>
            </div>
            <p class="caption">Physics: 左右两侧是冷边界，其他外边界绝热，芯片内部有体热源，热量向底板和扩展块扩散。</p>
          </div>
          <div class="tab-panel" data-panel="temperature">
            <div class="image-frame"><img src="{temperature_png_name}" alt="Temperature field"></div>
            <p class="caption">静态图适合快速看热点位置；下面的交互图更适合旋转、缩放和悬停查看。</p>
            <iframe src="{temperature_html_name}" title="Interactive temperature field"></iframe>
          </div>
        </div>
        <aside class="panel">
          <div class="legend">
            <div class="legend-item">
              <strong>Recommended Reading Order</strong>
              1. Layout
              <br>2. Mesh
              <br>3. Subdomains
              <br>4. Temperature
            </div>
            <div class="legend-item">
              <strong>How To Read This Case</strong>
              Chip 内部有热源，所以它附近温度最高；热量随后向底板和扩展块扩散，并最终通过左右冷边界带走。
            </div>
            <div class="legend-item">
              <strong>Physics</strong>
              Cold boundaries: 左右边界 `T = 0`
              <br>Insulated boundaries: 其余外边界
              <br>Heat source: 仅 `chip` 内部 `q > 0`
            </div>
            {stats_html}
            <div class="legend-item">
              <strong>Files</strong>
              这个总览页引用同目录下的 PNG 和 `temperature.html`。
              <a class="summary-link" href="{summary_rel.as_posix()}">Open summary.txt</a>
            </div>
          </div>
        </aside>
      </div>
    </section>
  </div>
  <script>
    const buttons = document.querySelectorAll(".tab-button");
    const panels = document.querySelectorAll(".tab-panel");
    for (const button of buttons) {{
      button.addEventListener("click", () => {{
        const target = button.dataset.tab;
        for (const item of buttons) item.classList.toggle("active", item === button);
        for (const panel of panels) {{
          panel.classList.toggle("active", panel.dataset.panel === target);
        }}
      }});
    }}
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def save_history_dashboard_html(path: Path, *, history_summary: dict) -> None:
    ensure_parent(path)
    runs = history_summary.get("runs", [])
    latest_run = runs[-1] if runs else {}
    best_run = None
    numeric_runs = [run for run in runs if isinstance(run.get("chip_max_temperature"), (int, float))]
    if numeric_runs:
        best_run = min(numeric_runs, key=lambda item: item["chip_max_temperature"])

    summary_json = json.dumps(history_summary, ensure_ascii=False)
    latest_model = latest_run.get("model_info", {}).get("model", "N/A")
    latest_status = latest_run.get("status", "N/A")
    best_temp = best_run.get("chip_max_temperature") if best_run else None
    best_run_id = best_run.get("run_id", "N/A") if best_run else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Thermal Optimization History Dashboard</title>
  <style>
    :root {{
      --bg: #f5efe4;
      --panel: rgba(255,255,255,0.9);
      --line: #d9d0c2;
      --ink: #1f1b18;
      --muted: #6a635b;
      --accent: #a44a3f;
      --accent-soft: #f5d6cf;
      --good: #2d7a46;
      --warn: #b45f06;
      --bad: #a61b1b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff6e8 0, transparent 26rem),
        linear-gradient(180deg, #fbf4ea 0%, var(--bg) 100%);
    }}
    .shell {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 12px 40px rgba(60, 45, 30, 0.08);
    }}
    .hero {{
      padding: 24px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 2rem;
    }}
    .subtitle {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: white;
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 0.85rem;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .stat-value {{
      font-size: 1.3rem;
      font-weight: 700;
    }}
    .workspace {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(340px, 1fr);
      gap: 18px;
    }}
    .panel {{
      padding: 18px;
    }}
    .section-title {{
      margin: 0 0 12px;
      font-size: 1.15rem;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }}
    .chart-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: white;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .timeline-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 0.95rem;
    }}
    .timeline-table th, .timeline-table td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}
    .timeline-row {{
      cursor: pointer;
    }}
    .timeline-row.active {{
      background: var(--accent-soft);
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 700;
    }}
    .badge.good {{ background: #dbf0df; color: var(--good); }}
    .badge.warn {{ background: #fde9c9; color: var(--warn); }}
    .badge.bad {{ background: #f8d7d7; color: var(--bad); }}
    .detail-grid {{
      display: grid;
      gap: 12px;
    }}
    .detail-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: white;
    }}
    .detail-card pre {{
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      font-size: 0.92rem;
      line-height: 1.55;
    }}
    .link-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
    }}
    .link-row a {{
      text-decoration: none;
      color: white;
      background: var(--accent);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 0.92rem;
    }}
    .compare {{
      margin-top: 18px;
    }}
    .compare-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: white;
    }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 1050px) {{
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .workspace {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Thermal Optimization History Workspace</h1>
      <p class="subtitle">
        这个工作台把多轮优化的指标变化、提案、合法性检查与单轮可视化入口放到同一页里，方便你追踪模型到底做了什么，以及为什么被接受或拦下。
      </p>
      <div class="stats">
        <div class="stat"><div class="stat-label">Run Count</div><div class="stat-value">{history_summary.get("run_count", 0)}</div></div>
        <div class="stat"><div class="stat-label">Latest Run</div><div class="stat-value">{latest_run.get("run_id", "N/A")}</div></div>
        <div class="stat"><div class="stat-label">Latest Status</div><div class="stat-value">{latest_status}</div></div>
        <div class="stat"><div class="stat-label">Best Chip Max</div><div class="stat-value">{best_temp if best_temp is not None else "N/A"}</div><div class="muted">{best_run_id}</div></div>
        <div class="stat"><div class="stat-label">Latest Model</div><div class="stat-value">{latest_model}</div></div>
      </div>
    </section>
    <section class="workspace">
      <div class="panel">
        <h2 class="section-title">Timeline And Metrics</h2>
        <div class="chart-grid">
          <div class="chart-card">
            <h3 class="section-title">chip_max_temperature</h3>
            <svg id="chip-chart" viewBox="0 0 640 220" aria-label="chip max temperature chart"></svg>
          </div>
          <div class="chart-card">
            <h3 class="section-title">temperature_max</h3>
            <svg id="temp-chart" viewBox="0 0 640 220" aria-label="temperature max chart"></svg>
          </div>
        </div>
        <table class="timeline-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Status</th>
              <th>chip_max_temperature</th>
              <th>Validation</th>
            </tr>
          </thead>
          <tbody id="timeline-body"></tbody>
        </table>
        <div class="compare">
          <h2 class="section-title">Selected Run vs Previous Run</h2>
          <div class="compare-card">
            <pre id="compare-content">Select a run to compare changes.</pre>
          </div>
        </div>
      </div>
      <aside class="panel">
        <h2 class="section-title">Run Detail</h2>
        <div class="detail-grid">
          <div class="detail-card">
            <strong>Summary</strong>
            <pre id="detail-summary">Select a run from the timeline.</pre>
          </div>
          <div class="detail-card">
            <strong>Proposal</strong>
            <pre id="detail-proposal"></pre>
          </div>
          <div class="detail-card">
            <strong>Validation</strong>
            <pre id="detail-validation"></pre>
          </div>
          <div class="detail-card">
            <strong>Decision</strong>
            <pre id="detail-decision"></pre>
            <div class="link-row" id="detail-links"></div>
          </div>
        </div>
      </aside>
    </section>
  </div>
  <script>
    const historySummary = {summary_json};
    const runs = historySummary.runs || [];

    function statusBadge(status) {{
      if (status === "feasible" || status === "proposal_applied") return '<span class="badge good">' + status + '</span>';
      if (status === "invalid_proposal") return '<span class="badge bad">' + status + '</span>';
      return '<span class="badge warn">' + (status || 'incomplete') + '</span>';
    }}

    function formatNumber(value) {{
      if (typeof value !== "number") return "N/A";
      return value.toFixed(6);
    }}

    function polylinePoints(values, width, height, padding) {{
      const numeric = values.filter((value) => typeof value === "number");
      if (!numeric.length) return "";
      const min = Math.min(...numeric);
      const max = Math.max(...numeric);
      const span = max - min || 1.0;
      return values.map((value, index) => {{
        const x = padding + (index * (width - 2 * padding) / Math.max(values.length - 1, 1));
        const y = typeof value === "number"
          ? height - padding - ((value - min) / span) * (height - 2 * padding)
          : height - padding;
        return `${{x}},${{y}}`;
      }}).join(" ");
    }}

    function renderChart(svgId, values, color) {{
      const svg = document.getElementById(svgId);
      const width = 640;
      const height = 220;
      const padding = 32;
      const points = polylinePoints(values, width, height, padding);
      svg.innerHTML = `
        <rect x="0" y="0" width="${{width}}" height="${{height}}" fill="#fff" stroke="#d9d0c2" rx="18"></rect>
        <line x1="${{padding}}" y1="${{height - padding}}" x2="${{width - padding}}" y2="${{height - padding}}" stroke="#b8ab99"></line>
        <line x1="${{padding}}" y1="${{padding}}" x2="${{padding}}" y2="${{height - padding}}" stroke="#b8ab99"></line>
        <polyline fill="none" stroke="${{color}}" stroke-width="3" points="${{points}}"></polyline>
      `;
      values.forEach((value, index) => {{
        if (typeof value !== "number") return;
        const x = padding + (index * (width - 2 * padding) / Math.max(values.length - 1, 1));
        const numeric = values.filter((item) => typeof item === "number");
        const min = Math.min(...numeric);
        const max = Math.max(...numeric);
        const span = max - min || 1.0;
        const y = height - padding - ((value - min) / span) * (height - 2 * padding);
        svg.innerHTML += `<circle cx="${{x}}" cy="${{y}}" r="4.5" fill="${{color}}"></circle>`;
      }});
    }}

    function renderTimeline() {{
      const tbody = document.getElementById("timeline-body");
      const activeIndex = Math.max(runs.length - 1, 0);
      tbody.innerHTML = runs.map((run, index) => `
        <tr class="timeline-row ${{index === activeIndex ? 'active' : ''}}" data-index="${{index}}">
          <td>${{run.run_id}}</td>
          <td>${{statusBadge(run.status)}}</td>
          <td>${{formatNumber(run.chip_max_temperature)}}</td>
          <td>${{run.validation_valid === true ? 'valid' : run.validation_valid === false ? 'invalid' : 'N/A'}}</td>
        </tr>
      `).join("");
      tbody.querySelectorAll(".timeline-row").forEach((row) => {{
        row.addEventListener("click", () => {{
          tbody.querySelectorAll(".timeline-row").forEach((item) => item.classList.remove("active"));
          row.classList.add("active");
          renderDetail(Number(row.dataset.index));
        }});
      }});
    }}

    function diffChanges(run, prevRun) {{
      const lines = [];
      if (!prevRun) return "No previous run for comparison.";
      const prevChanges = prevRun.changes || [];
      const currChanges = run.changes || [];
      const delta = typeof run.chip_max_temperature === "number" && typeof prevRun.chip_max_temperature === "number"
        ? (run.chip_max_temperature - prevRun.chip_max_temperature).toFixed(6)
        : "N/A";
      lines.push(`Previous run: ${{prevRun.run_id}}`);
      lines.push(`Current run: ${{run.run_id}}`);
      lines.push(`chip_max_temperature delta: ${{delta}}`);
      lines.push("");
      lines.push("Previous changes:");
      lines.push(prevChanges.length ? JSON.stringify(prevChanges, null, 2) : "[]");
      lines.push("");
      lines.push("Current changes:");
      lines.push(currChanges.length ? JSON.stringify(currChanges, null, 2) : "[]");
      return lines.join("\\n");
    }}

    function renderDetail(index) {{
      const run = runs[index];
      if (!run) return;
      const prevRun = index > 0 ? runs[index - 1] : null;
      document.getElementById("detail-summary").textContent = [
        `run_id: ${{run.run_id}}`,
        `status: ${{run.status || 'N/A'}}`,
        `feasible: ${{run.feasible}}`,
        `chip_max_temperature: ${{formatNumber(run.chip_max_temperature)}}`,
        `temperature_max: ${{formatNumber(run.temperature_max)}}`,
      ].join("\\n");
      document.getElementById("detail-proposal").textContent = [
        `decision_summary: ${{run.decision_summary || 'N/A'}}`,
        `changes:`,
        JSON.stringify(run.changes || [], null, 2),
        ``,
        `model_info:`,
        JSON.stringify(run.model_info || {{}}, null, 2),
      ].join("\\n");
      document.getElementById("detail-validation").textContent = [
        `validation_valid: ${{run.validation_valid}}`,
        `validation_reasons:`,
        JSON.stringify(run.validation_reasons || [], null, 2),
      ].join("\\n");
      document.getElementById("detail-decision").textContent = [
        `status: ${{run.status || 'N/A'}}`,
        `overview_html: ${{run.overview_html || 'N/A'}}`,
        `temperature_html: ${{run.temperature_html || 'N/A'}}`,
      ].join("\\n");
      document.getElementById("compare-content").textContent = diffChanges(run, prevRun);

      const links = [];
      if (run.overview_html) links.push(`<a href="${{run.overview_html}}">Open Overview</a>`);
      if (run.temperature_html) links.push(`<a href="${{run.temperature_html}}">Open Temperature</a>`);
      document.getElementById("detail-links").innerHTML = links.join("");
    }}

    renderChart("chip-chart", runs.map((run) => run.chip_max_temperature), "#a44a3f");
    renderChart("temp-chart", runs.map((run) => run.temperature_max), "#205493");
    renderTimeline();
    renderDetail(Math.max(runs.length - 1, 0));
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
