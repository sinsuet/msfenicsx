# Search Trajectory STN Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 optimizer `render-assets` 新增 Search Trajectory Network, STN 后处理图件和 CSV，用于解释高维 thermal-layout 优化搜索过程。

**Architecture:** 新增 `optimizers.analytics.search_trajectory` 从 `optimization_result.history` 构建 STN nodes、edges、metrics；新增 `visualization.figures.search_trajectory_network` 负责 deterministic Matplotlib 渲染；`optimizers.render_assets.render_run_assets()` 只作为编排层调用 analytics、写 CSV、写 PNG/PDF。首版不新增 runtime trace、不改 optimizer 行为、不引入新依赖。

**Tech Stack:** Python 3.12、numpy、matplotlib、pytest、现有 `msfenicsx` conda 环境。

---

## 文件结构

### 新增文件

- `optimizers/analytics/search_trajectory.py`：从 optimization history 构建 STN 数据结构，包含 objective extraction、non-dominated sorting、representative selection、location quantization、graph metrics。
- `visualization/figures/search_trajectory_network.py`：渲染 `search_trajectory_network.png/pdf` 和 `search_trajectory_nodes_by_vector.png/pdf`。
- `tests/optimizers/test_search_trajectory.py`：analytics 行为测试。
- `tests/visualization/test_search_trajectory_figure.py`：figure 输出测试。

### 修改文件

- `optimizers/render_assets.py`：导入 STN analytics/figures，写出 CSV，渲染图，清理 stale STN outputs。
- `tests/visualization/test_render_assets_fixtures.py`：扩展 existing render-assets fixture 断言 STN artifacts。

---

## Task 1: STN Analytics

**Files:**
- Create: `optimizers/analytics/search_trajectory.py`
- Create: `tests/optimizers/test_search_trajectory.py`

- [ ] **Step 1: 写失败测试**

Create `tests/optimizers/test_search_trajectory.py`:

```python
from optimizers.analytics.search_trajectory import build_search_trajectory


def _record(
    evaluation_index: int,
    generation: int,
    *,
    x: float,
    y: float,
    temperature: float,
    gradient: float,
    feasible: bool = True,
    violation: float = 0.0,
) -> dict:
    return {
        "evaluation_index": evaluation_index,
        "generation": generation,
        "source": "optimizer",
        "feasible": feasible,
        "decision_vector": {"c01_x": x, "c01_y": y},
        "objective_values": {
            "minimize_peak_temperature": temperature,
            "minimize_temperature_gradient_rms": gradient,
        },
        "constraint_values": {"radiator_span_budget": violation},
    }


def test_build_search_trajectory_selects_weighted_representatives_and_marks_shared_nodes() -> None:
    history = [
        {"evaluation_index": 0, "generation": 0, "source": "baseline"},
        _record(1, 0, x=0.100, y=0.100, temperature=330.0, gradient=14.0),
        _record(2, 0, x=0.500, y=0.500, temperature=320.0, gradient=20.0),
        _record(3, 1, x=0.110, y=0.100, temperature=329.0, gradient=13.0),
        _record(4, 1, x=0.500, y=0.500, temperature=319.0, gradient=18.0),
    ]

    result = build_search_trajectory(history, bin_width=0.05)

    assert len(result.nodes) == 2
    assert len(result.edges) == 5
    shared_nodes = [row for row in result.nodes if row["vector_count"] > 1]
    assert len(shared_nodes) == 2
    assert {row["vector_id"] for row in result.metrics if row["scope"] == "vector"} == {"V1", "V2", "V3", "V4", "V5"}
    overall = next(row for row in result.metrics if row["scope"] == "overall")
    assert overall["num_nodes"] == 2
    assert overall["num_edges"] == 5
    assert overall["shared_nodes"] == 2
    assert overall["pareto_nodes"] == 1


def test_build_search_trajectory_uses_infeasible_low_violation_records_when_generation_has_no_feasible_records() -> None:
    history = [
        _record(1, 0, x=0.100, y=0.100, temperature=1.0e12, gradient=1.0e12, feasible=False, violation=3.0),
        _record(2, 0, x=0.200, y=0.200, temperature=1.0e12, gradient=1.0e12, feasible=False, violation=1.0),
        _record(3, 1, x=0.250, y=0.250, temperature=340.0, gradient=30.0, feasible=True),
    ]

    result = build_search_trajectory(history, bin_width=0.05)

    assert result.nodes
    start_rows = [row for row in result.nodes if row["first_generation"] == 0]
    assert start_rows
    assert min(row["representative_evaluation_index"] for row in start_rows) == 2
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_search_trajectory.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'optimizers.analytics.search_trajectory'`.

- [ ] **Step 3: 实现 analytics**

Create `optimizers/analytics/search_trajectory.py` with:

```python
"""Search Trajectory Network analytics for optimizer histories."""

from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

DEFAULT_STN_WEIGHTS: tuple[tuple[str, tuple[float, float]], ...] = (
    ("V1", (1.0, 0.0)),
    ("V2", (0.75, 0.25)),
    ("V3", (0.5, 0.5)),
    ("V4", (0.25, 0.75)),
    ("V5", (0.0, 1.0)),
)
DEFAULT_BIN_WIDTH = 0.02
OBJECTIVE_KEYS = {
    "temperature_max": (
        "temperature_max",
        "summary.temperature_max",
        "minimize_peak_temperature",
    ),
    "temperature_gradient_rms": (
        "temperature_gradient_rms",
        "summary.temperature_gradient_rms",
        "minimize_temperature_gradient_rms",
    ),
}


@dataclass(frozen=True)
class SearchTrajectoryResult:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    metrics: list[dict[str, Any]]


def build_search_trajectory(
    history: Sequence[Mapping[str, Any]],
    *,
    bin_width: float = DEFAULT_BIN_WIDTH,
    weights: Sequence[tuple[str, tuple[float, float]]] = DEFAULT_STN_WEIGHTS,
) -> SearchTrajectoryResult:
    rows = [_normalized_row(row) for row in history if _is_optimizer_row(row)]
    if not rows:
        return SearchTrajectoryResult(nodes=[], edges=[], metrics=[_empty_overall_metrics(bin_width)])

    pareto_eval_indices = _pareto_evaluation_indices([row for row in rows if row["feasible"]])
    trajectories: dict[str, list[dict[str, Any]]] = {vector_id: [] for vector_id, _weight in weights}
    for generation in sorted({int(row["generation"]) for row in rows}):
        generation_rows = [row for row in rows if int(row["generation"]) == generation]
        candidate_rows = _candidate_rows(generation_rows, target_count=len(weights))
        if not candidate_rows:
            continue
        selected_rows = _front_filled_rows(candidate_rows, target_count=len(weights))
        for vector_id, weight in weights:
            representative = _select_representative(selected_rows, weight)
            trajectories[vector_id].append(representative)

    node_accumulator: dict[str, dict[str, Any]] = {}
    edge_accumulator: dict[tuple[str, str, str], dict[str, Any]] = {}
    for vector_id, trajectory in trajectories.items():
        previous_node_id: str | None = None
        for row in trajectory:
            node_id, location_key = _location_id(row["decision_vector"], bin_width=bin_width)
            _accumulate_node(
                node_accumulator,
                node_id=node_id,
                location_key=location_key,
                vector_id=vector_id,
                row=row,
                pareto_member=int(row["evaluation_index"]) in pareto_eval_indices,
            )
            if previous_node_id is not None:
                _accumulate_edge(
                    edge_accumulator,
                    source=previous_node_id,
                    target=node_id,
                    vector_id=vector_id,
                    generation=int(row["generation"]),
                )
            previous_node_id = node_id

    nodes = [_finalize_node(node) for node in node_accumulator.values()]
    nodes.sort(key=lambda row: (int(row["first_generation"]), str(row["node_id"])))
    edges = list(edge_accumulator.values())
    edges.sort(key=lambda row: (str(row["vector_id"]), int(row["first_generation"]), str(row["source"]), str(row["target"])))
    metrics = _metrics(nodes, edges, bin_width=bin_width, vector_ids=[vector_id for vector_id, _weight in weights])
    return SearchTrajectoryResult(nodes=nodes, edges=edges, metrics=metrics)


def _is_optimizer_row(row: Mapping[str, Any]) -> bool:
    return str(row.get("source", "")).strip().lower() != "baseline" and isinstance(row.get("decision_vector"), Mapping)


def _normalized_row(row: Mapping[str, Any]) -> dict[str, Any]:
    objective_values = dict(row.get("objective_values", row.get("objectives", {})) or {})
    temperature = _first_float(objective_values, OBJECTIVE_KEYS["temperature_max"])
    gradient = _first_float(objective_values, OBJECTIVE_KEYS["temperature_gradient_rms"])
    return {
        "evaluation_index": int(row.get("evaluation_index", row.get("eval_index", 0))),
        "generation": int(row.get("generation", row.get("generation_index", 0))),
        "feasible": bool(row.get("feasible", False)),
        "status": str(row.get("status") or ("ok" if bool(row.get("feasible", False)) else "infeasible")),
        "decision_vector": {str(key): float(value) for key, value in dict(row["decision_vector"]).items()},
        "temperature_max": temperature,
        "temperature_gradient_rms": gradient,
        "total_violation": _total_positive_violation(dict(row.get("constraint_values", row.get("constraints", {})) or {})),
    }


def _first_float(values: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    for key in keys:
        if key in values and values[key] is not None:
            return float(values[key])
    return None


def _total_positive_violation(values: Mapping[str, Any]) -> float:
    return float(sum(max(0.0, float(value)) for value in values.values()))


def _candidate_rows(rows: Sequence[dict[str, Any]], *, target_count: int) -> list[dict[str, Any]]:
    valid = [row for row in rows if row["temperature_max"] is not None and row["temperature_gradient_rms"] is not None]
    feasible = [row for row in valid if row["feasible"]]
    if len(feasible) >= target_count:
        return feasible
    infeasible = sorted(
        [row for row in valid if not row["feasible"]],
        key=lambda row: (float(row["total_violation"]), -int(row["evaluation_index"])),
    )
    return feasible + infeasible[: max(0, target_count - len(feasible))]


def _front_filled_rows(rows: Sequence[dict[str, Any]], *, target_count: int) -> list[dict[str, Any]]:
    remaining = list(rows)
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < target_count:
        front_indices = _non_dominated_indices(remaining)
        front = [remaining[index] for index in front_indices]
        selected.extend(front)
        front_index_set = set(front_indices)
        remaining = [row for index, row in enumerate(remaining) if index not in front_index_set]
    return selected or list(rows)


def _non_dominated_indices(rows: Sequence[Mapping[str, Any]]) -> list[int]:
    points = [(float(row["temperature_max"]), float(row["temperature_gradient_rms"])) for row in rows]
    indices: list[int] = []
    for i, point in enumerate(points):
        dominated = False
        for j, challenger in enumerate(points):
            if i == j:
                continue
            if challenger[0] <= point[0] and challenger[1] <= point[1] and (challenger[0] < point[0] or challenger[1] < point[1]):
                dominated = True
                break
        if not dominated:
            indices.append(i)
    return indices


def _select_representative(rows: Sequence[dict[str, Any]], weight: tuple[float, float]) -> dict[str, Any]:
    objectives = np.asarray(
        [(float(row["temperature_max"]), float(row["temperature_gradient_rms"])) for row in rows],
        dtype=np.float64,
    )
    ideal = objectives.min(axis=0)
    span = objectives.max(axis=0) - ideal
    span = np.where(span <= 1.0e-12, 1.0, span)
    weights = np.asarray(weight, dtype=np.float64)
    scores = np.max(weights * np.abs((objectives - ideal) / span), axis=1)
    best_score = float(np.min(scores))
    tied = [index for index, score in enumerate(scores) if abs(float(score) - best_score) <= 1.0e-12]
    return dict(max((rows[index] for index in tied), key=lambda row: int(row["evaluation_index"])))


def _location_id(decision_vector: Mapping[str, float], *, bin_width: float) -> tuple[str, str]:
    quantized = tuple(int(round(float(decision_vector[key]) / bin_width)) for key in sorted(decision_vector))
    location_key = ",".join(str(value) for value in quantized)
    digest = hashlib.sha1(location_key.encode("utf-8")).hexdigest()[:12]
    return f"stn-{digest}", location_key


def _accumulate_node(
    nodes: dict[str, dict[str, Any]],
    *,
    node_id: str,
    location_key: str,
    vector_id: str,
    row: Mapping[str, Any],
    pareto_member: bool,
) -> None:
    node = nodes.setdefault(
        node_id,
        {
            "node_id": node_id,
            "location_key": location_key,
            "visit_count": 0,
            "vectors": set(),
            "first_generation": int(row["generation"]),
            "last_generation": int(row["generation"]),
            "representative_evaluation_index": int(row["evaluation_index"]),
            "temperature_max": row["temperature_max"],
            "temperature_gradient_rms": row["temperature_gradient_rms"],
            "feasible": bool(row["feasible"]),
            "pareto_member": False,
            "status": row["status"],
        },
    )
    node["visit_count"] = int(node["visit_count"]) + 1
    node["vectors"].add(vector_id)
    node["first_generation"] = min(int(node["first_generation"]), int(row["generation"]))
    node["last_generation"] = max(int(node["last_generation"]), int(row["generation"]))
    if int(row["evaluation_index"]) >= int(node["representative_evaluation_index"]):
        node["representative_evaluation_index"] = int(row["evaluation_index"])
        node["temperature_max"] = row["temperature_max"]
        node["temperature_gradient_rms"] = row["temperature_gradient_rms"]
        node["feasible"] = bool(row["feasible"])
        node["status"] = row["status"]
    node["pareto_member"] = bool(node["pareto_member"] or pareto_member)


def _finalize_node(node: Mapping[str, Any]) -> dict[str, Any]:
    vectors = sorted(str(value) for value in node["vectors"])
    return {
        **{key: value for key, value in dict(node).items() if key != "vectors"},
        "vector_count": len(vectors),
        "vectors": "|".join(vectors),
    }


def _accumulate_edge(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    *,
    source: str,
    target: str,
    vector_id: str,
    generation: int,
) -> None:
    key = (source, target, vector_id)
    edge = edges.setdefault(
        key,
        {
            "source": source,
            "target": target,
            "vector_id": vector_id,
            "weight": 0,
            "first_generation": generation,
            "last_generation": generation,
        },
    )
    edge["weight"] = int(edge["weight"]) + 1
    edge["first_generation"] = min(int(edge["first_generation"]), generation)
    edge["last_generation"] = max(int(edge["last_generation"]), generation)


def _pareto_evaluation_indices(rows: Sequence[Mapping[str, Any]]) -> set[int]:
    if not rows:
        return set()
    return {int(rows[index]["evaluation_index"]) for index in _non_dominated_indices(rows)}


def _metrics(
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    *,
    bin_width: float,
    vector_ids: Sequence[str],
) -> list[dict[str, Any]]:
    result = [_metric_row("overall", "", nodes, edges, bin_width=bin_width)]
    for vector_id in vector_ids:
        vector_edges = [edge for edge in edges if edge["vector_id"] == vector_id]
        vector_node_ids = {str(edge["source"]) for edge in vector_edges} | {str(edge["target"]) for edge in vector_edges}
        if not vector_node_ids:
            vector_node_ids = {
                str(node["node_id"])
                for node in nodes
                if vector_id in str(node.get("vectors", "")).split("|")
            }
        vector_nodes = [node for node in nodes if str(node["node_id"]) in vector_node_ids]
        result.append(_metric_row("vector", vector_id, vector_nodes, vector_edges, bin_width=bin_width))
    return result


def _metric_row(
    scope: str,
    vector_id: str,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    *,
    bin_width: float,
) -> dict[str, Any]:
    in_degree: dict[str, int] = defaultdict(int)
    out_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, set[str]] = defaultdict(set)
    node_ids = {str(node["node_id"]) for node in nodes}
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        out_degree[source] += 1
        in_degree[target] += 1
        adjacency[source].add(target)
        adjacency[target].add(source)
        node_ids.add(source)
        node_ids.add(target)
    in_values = [in_degree[node_id] for node_id in node_ids]
    out_values = [out_degree[node_id] for node_id in node_ids]
    return {
        "scope": scope,
        "vector_id": vector_id,
        "bin_width": float(bin_width),
        "num_nodes": len(nodes),
        "num_edges": len(edges),
        "shared_nodes": sum(1 for node in nodes if int(node.get("vector_count", 1)) > 1),
        "pareto_nodes": sum(1 for node in nodes if bool(node.get("pareto_member", False))),
        "components": _component_count(node_ids, adjacency),
        "mean_in_degree": float(np.mean(in_values)) if in_values else 0.0,
        "max_in_degree": max(in_values) if in_values else 0,
        "mean_out_degree": float(np.mean(out_values)) if out_values else 0.0,
        "max_out_degree": max(out_values) if out_values else 0,
    }


def _component_count(node_ids: set[str], adjacency: Mapping[str, set[str]]) -> int:
    unseen = set(node_ids)
    components = 0
    while unseen:
        components += 1
        start = unseen.pop()
        queue: deque[str] = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency.get(current, set()):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return components


def _empty_overall_metrics(bin_width: float) -> dict[str, Any]:
    return _metric_row("overall", "", [], [], bin_width=bin_width)
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_search_trajectory.py
```

Expected: PASS。

---

## Task 2: STN Figure Renderer

**Files:**
- Create: `visualization/figures/search_trajectory_network.py`
- Create: `tests/visualization/test_search_trajectory_figure.py`

- [ ] **Step 1: 写失败测试**

Create `tests/visualization/test_search_trajectory_figure.py`:

```python
from pathlib import Path


def test_search_trajectory_figures_write_png_and_pdf(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from visualization.figures.search_trajectory_network import (
        render_search_trajectory_network,
        render_search_trajectory_nodes_by_vector,
    )

    nodes = [
        {
            "node_id": "n1",
            "visit_count": 2,
            "vector_count": 1,
            "vectors": "V1",
            "first_generation": 0,
            "last_generation": 0,
            "pareto_member": False,
        },
        {
            "node_id": "n2",
            "visit_count": 4,
            "vector_count": 2,
            "vectors": "V1|V2",
            "first_generation": 1,
            "last_generation": 1,
            "pareto_member": True,
        },
    ]
    edges = [
        {"source": "n1", "target": "n2", "vector_id": "V1", "weight": 3},
    ]
    metrics = [
        {"scope": "vector", "vector_id": "V1", "num_nodes": 2},
        {"scope": "vector", "vector_id": "V2", "num_nodes": 1},
    ]

    network_output = tmp_path / "search_trajectory_network.png"
    bar_output = tmp_path / "search_trajectory_nodes_by_vector.png"

    render_search_trajectory_network(nodes=nodes, edges=edges, output=network_output)
    render_search_trajectory_nodes_by_vector(metrics=metrics, output=bar_output)

    assert network_output.exists()
    assert network_output.with_name("pdf").joinpath("search_trajectory_network.pdf").exists()
    assert bar_output.exists()
    assert bar_output.with_name("pdf").joinpath("search_trajectory_nodes_by_vector.pdf").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n msfenicsx pytest -v tests/visualization/test_search_trajectory_figure.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'visualization.figures.search_trajectory_network'`.

- [ ] **Step 3: 实现 figure renderer**

Create `visualization/figures/search_trajectory_network.py` with:

```python
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
    for node in nodes:
        node_id = str(node["node_id"])
        x_value, y_value = positions[node_id]
        vectors = str(node.get("vectors", "")).split("|")
        marker = _node_marker(node)
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


def _node_marker(node: Mapping[str, Any]) -> str:
    first_generation = int(node.get("first_generation", 0))
    last_generation = int(node.get("last_generation", first_generation))
    if first_generation == 0:
        return "s"
    if last_generation >= first_generation:
        return "^"
    return "o"


def _layout_positions(nodes: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]]) -> dict[str, tuple[float, float]]:
    node_ids = [str(node["node_id"]) for node in nodes]
    if len(node_ids) == 1:
        return {node_ids[0]: (0.0, 0.0)}
    rng = np.random.default_rng(42)
    angles = np.linspace(0.0, 2.0 * np.pi, len(node_ids), endpoint=False)
    positions = {
        node_id: np.asarray([math.cos(angle), math.sin(angle)], dtype=np.float64) + rng.normal(0.0, 0.01, 2)
        for node_id, angle in zip(node_ids, angles, strict=True)
    }
    edge_pairs = [(str(edge["source"]), str(edge["target"])) for edge in edges if edge.get("source") in positions and edge.get("target") in positions]
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
```

- [ ] **Step 4: 运行 figure 测试确认通过**

Run:

```bash
conda run -n msfenicsx pytest -v tests/visualization/test_search_trajectory_figure.py
```

Expected: PASS。

---

## Task 3: 接入 render-assets

**Files:**
- Modify: `optimizers/render_assets.py`
- Modify: `tests/visualization/test_render_assets_fixtures.py`

- [ ] **Step 1: 写失败测试**

在 `tests/visualization/test_render_assets_fixtures.py` 的 `required` list 中加入：

```python
"analytics/search_trajectory_nodes.csv",
"analytics/search_trajectory_edges.csv",
"analytics/search_trajectory_metrics.csv",
"figures/search_trajectory_network.png",
"figures/pdf/search_trajectory_network.pdf",
"figures/search_trajectory_nodes_by_vector.png",
"figures/pdf/search_trajectory_nodes_by_vector.pdf",
```

新增 stale cleanup 断言：

```python
def test_render_assets_cleans_stale_search_trajectory_outputs(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from optimizers.render_assets import render_run_assets

    run_root = tmp_path / "0416_2030__llm"
    _seed_run_bundle(run_root)
    stale_files = [
        run_root / "analytics" / "search_trajectory_nodes.csv",
        run_root / "analytics" / "search_trajectory_edges.csv",
        run_root / "analytics" / "search_trajectory_metrics.csv",
        run_root / "figures" / "search_trajectory_network.png",
        run_root / "figures" / "search_trajectory_nodes_by_vector.png",
    ]
    for path in stale_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale", encoding="utf-8")

    render_run_assets(run_root, hires=False)

    for path in stale_files:
        assert path.exists()
        assert path.read_bytes() != b"stale"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n msfenicsx pytest -v tests/visualization/test_render_assets_fixtures.py::test_render_assets_produces_full_mainline_outputs tests/visualization/test_render_assets_fixtures.py::test_render_assets_cleans_stale_search_trajectory_outputs
```

Expected: FAIL，因为 `render-assets` 尚未生成 STN artifacts。

- [ ] **Step 3: 修改 render-assets**

在 `optimizers/render_assets.py` import 区加入：

```python
from optimizers.analytics.search_trajectory import build_search_trajectory
from visualization.figures.search_trajectory_network import (
    render_search_trajectory_network,
    render_search_trajectory_nodes_by_vector,
)
```

在 `render_run_assets()` 中 `optimization_result` block 内，`progress_rows` 处理之后加入：

```python
        search_trajectory = build_search_trajectory(list(optimization_result.get("history", [])))
        _write_dict_rows_csv(analytics / "search_trajectory_nodes.csv", search_trajectory.nodes)
        _write_dict_rows_csv(analytics / "search_trajectory_edges.csv", search_trajectory.edges)
        _write_dict_rows_csv(analytics / "search_trajectory_metrics.csv", search_trajectory.metrics)
        if search_trajectory.nodes:
            render_search_trajectory_network(
                nodes=search_trajectory.nodes,
                edges=search_trajectory.edges,
                output=figures / "search_trajectory_network.png",
                hires=hires,
            )
            render_search_trajectory_nodes_by_vector(
                metrics=search_trajectory.metrics,
                output=figures / "search_trajectory_nodes_by_vector.png",
                hires=hires,
            )
```

在 `_cleanup_render_outputs()` figure patterns 中加入：

```python
"search_trajectory_network.*",
"search_trajectory_nodes_by_vector.*",
```

在 analytics cleanup list 中加入：

```python
run_root / "analytics" / "search_trajectory_nodes.csv",
run_root / "analytics" / "search_trajectory_edges.csv",
run_root / "analytics" / "search_trajectory_metrics.csv",
```

- [ ] **Step 4: 运行 render-assets focused 测试确认通过**

Run:

```bash
conda run -n msfenicsx pytest -v tests/visualization/test_render_assets_fixtures.py::test_render_assets_produces_full_mainline_outputs tests/visualization/test_render_assets_fixtures.py::test_render_assets_cleans_stale_search_trajectory_outputs
```

Expected: PASS。

---

## Task 4: Focused Verification

**Files:**
- No code changes.

- [ ] **Step 1: 运行 STN 相关 focused tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_search_trajectory.py tests/visualization/test_search_trajectory_figure.py tests/visualization/test_render_assets_fixtures.py
```

Expected: PASS。

- [ ] **Step 2: 检查工作区 diff**

Run:

```bash
git status --short
git diff -- docs/superpowers/specs/2026-05-07-search-trajectory-stn-design.md docs/superpowers/plans/2026-05-07-search-trajectory-stn.md optimizers/analytics/search_trajectory.py visualization/figures/search_trajectory_network.py optimizers/render_assets.py tests/optimizers/test_search_trajectory.py tests/visualization/test_search_trajectory_figure.py tests/visualization/test_render_assets_fixtures.py
```

Expected: 只包含 STN spec、plan、analytics、figure、render-assets 接入和 focused tests。

---

## 自审

- Spec 覆盖：Task 1 覆盖数据入口、候选选择、location、nodes/edges/metrics；Task 2 覆盖图件；Task 3 覆盖 `render-assets` 接入和 stale cleanup；Task 4 覆盖 focused verification。
- Placeholder scan：本计划没有 `TBD`、`TODO` 或“稍后实现”类占位。
- 类型一致性：`build_search_trajectory()` 返回 `SearchTrajectoryResult(nodes, edges, metrics)`，figure 和 render-assets 都消费同一字段结构。
