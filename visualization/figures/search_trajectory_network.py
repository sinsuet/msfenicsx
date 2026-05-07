"""Search trajectory network figures."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.style.baseline import DPI_DEFAULT, DPI_HIRES, PALETTE_CATEGORICAL, apply_baseline

VECTOR_COLORS = {
    "V1": PALETTE_CATEGORICAL[1],
    "V2": PALETTE_CATEGORICAL[3],
    "V3": PALETTE_CATEGORICAL[7],
    "V4": PALETTE_CATEGORICAL[2],
    "V5": PALETTE_CATEGORICAL[5],
}
SHARED_NODE_COLOR = "#D9D9D9"
PARETO_COLOR = "#D55E00"


def render_search_trajectory_network(
    *,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    output: Path,
    hires: bool = False,
) -> None:
    if not nodes:
        return
    apply_baseline()
    output = ensure_output_parent(Path(output))
    positions = _layout_positions(nodes, edges)
    fig, ax = plt.subplots(figsize=(4.2, 3.2))

    max_edge_weight = max((int(edge.get("weight", 1)) for edge in edges), default=1)
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        if source not in positions or target not in positions:
            continue
        sx, sy = positions[source]
        tx, ty = positions[target]
        color = VECTOR_COLORS.get(str(edge.get("vector_id", "")), "#4A4A4A")
        linewidth = 0.4 + 1.4 * (int(edge.get("weight", 1)) / max_edge_weight)
        ax.annotate(
            "",
            xy=(tx, ty),
            xytext=(sx, sy),
            arrowprops={
                "arrowstyle": "->",
                "color": color,
                "alpha": 0.42,
                "lw": linewidth,
                "shrinkA": 8,
                "shrinkB": 8,
                "mutation_scale": 7,
            },
        )

    max_visits = max((int(node.get("visit_count", 1)) for node in nodes), default=1)
    terminal_generation = max((int(node.get("last_generation", 0)) for node in nodes), default=0)
    for node in nodes:
        node_id = str(node["node_id"])
        x_value, y_value = positions[node_id]
        vectors = str(node.get("vectors", "")).split("|")
        marker = _node_marker(node, terminal_generation=terminal_generation)
        color = SHARED_NODE_COLOR if int(node.get("vector_count", 1)) > 1 else VECTOR_COLORS.get(vectors[0], "#666666")
        size = 28.0 + 95.0 * math.sqrt(int(node.get("visit_count", 1)) / max_visits)
        edge_color = PARETO_COLOR if bool(node.get("pareto_member", False)) else "#222222"
        linewidth = 1.1 if bool(node.get("pareto_member", False)) else 0.45
        ax.scatter(
            [x_value],
            [y_value],
            s=size,
            marker=marker,
            facecolor=color,
            edgecolor=edge_color,
            linewidth=linewidth,
            zorder=3,
        )

    ax.set_title("Search Trajectory Network", loc="left")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_aspect("equal", adjustable="datalim")
    _save(fig, output, hires=hires)


def render_search_trajectory_nodes_by_vector(
    *,
    metrics: Sequence[Mapping[str, Any]],
    output: Path,
    hires: bool = False,
) -> None:
    vector_rows = [row for row in metrics if row.get("scope") == "vector"]
    if not vector_rows:
        return
    apply_baseline()
    output = ensure_output_parent(Path(output))
    labels = [str(row.get("vector_id", "")) for row in vector_rows]
    values = [int(row.get("num_nodes", 0)) for row in vector_rows]
    colors = [VECTOR_COLORS.get(label, "#666666") for label in labels]
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    ax.bar(labels, values, color=colors, edgecolor="#222222", linewidth=0.4)
    ax.set_title("Unique STN Nodes by Vector", loc="left")
    ax.set_xlabel("Decomposition vector")
    ax.set_ylabel("Unique nodes")
    ax.grid(axis="y", alpha=0.18, linewidth=0.4)
    _save(fig, output, hires=hires)


def _node_marker(node: Mapping[str, Any], *, terminal_generation: int) -> str:
    first_generation = int(node.get("first_generation", 0))
    last_generation = int(node.get("last_generation", first_generation))
    if first_generation == 0:
        return "s"
    if last_generation >= terminal_generation:
        return "^"
    return "o"


def _layout_positions(
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[float, float]]:
    node_ids = [str(node["node_id"]) for node in nodes]
    if len(node_ids) == 1:
        return {node_ids[0]: (0.0, 0.0)}
    rng = np.random.default_rng(42)
    angles = np.linspace(0.0, 2.0 * np.pi, len(node_ids), endpoint=False)
    positions = {
        node_id: np.asarray([math.cos(angle), math.sin(angle)], dtype=np.float64) + rng.normal(0.0, 0.01, 2)
        for node_id, angle in zip(node_ids, angles, strict=True)
    }
    edge_pairs = [
        (str(edge["source"]), str(edge["target"]))
        for edge in edges
        if edge.get("source") in positions and edge.get("target") in positions
    ]
    for _iteration in range(120):
        forces = {node_id: np.zeros(2, dtype=np.float64) for node_id in node_ids}
        for i, left in enumerate(node_ids):
            for right in node_ids[i + 1 :]:
                delta = positions[left] - positions[right]
                distance = max(float(np.linalg.norm(delta)), 1.0e-3)
                force = 0.015 * delta / (distance * distance)
                forces[left] += force
                forces[right] -= force
        for source, target in edge_pairs:
            delta = positions[target] - positions[source]
            forces[source] += 0.025 * delta
            forces[target] -= 0.025 * delta
        for node_id in node_ids:
            positions[node_id] += np.clip(forces[node_id], -0.05, 0.05)
    return {node_id: (float(value[0]), float(value[1])) for node_id, value in positions.items()}


def _save(fig, output: Path, *, hires: bool) -> None:
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)
