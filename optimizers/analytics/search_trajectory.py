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
    edges.sort(
        key=lambda row: (
            str(row["vector_id"]),
            int(row["first_generation"]),
            str(row["source"]),
            str(row["target"]),
        )
    )
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
    valid = [
        row
        for row in rows
        if row["temperature_max"] is not None and row["temperature_gradient_rms"] is not None
    ]
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
            if challenger[0] <= point[0] and challenger[1] <= point[1] and (
                challenger[0] < point[0] or challenger[1] < point[1]
            ):
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
        vector_node_ids = {str(edge["source"]) for edge in vector_edges} | {
            str(edge["target"]) for edge in vector_edges
        }
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
