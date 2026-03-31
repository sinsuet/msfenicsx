from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.tri as mtri
import numpy as np
import pytest
import yaml
from dolfinx.fem.petsc import NonlinearProblem

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.solver.case_to_geometry import interpret_case
from core.solver.mesh_builder import build_panel_mesh
from core.solver.physics_builder import build_thermal_problem
from optimizers.io import generate_benchmark_cases, load_optimization_result, load_optimization_spec
from optimizers.repair import repair_case_from_vector


matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_OUTPUT_DIR = REPO_ROOT / "tests" / "artifacts" / "optimizer_overview"
DEFAULT_IMAGE_PATH = DEFAULT_OUTPUT_DIR / "nsga2_three_mode_overview.png"
DEFAULT_METADATA_PATH = DEFAULT_OUTPUT_DIR / "nsga2_three_mode_overview.json"

MODE_CONFIGS = (
    {
        "mode_id": "pure-native-nsga2",
        "label": "Pure-Native NSGA-II",
        "spec_path": REPO_ROOT / "scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml",
        "result_path": REPO_ROOT
        / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-full/2026-03-29-real-test/optimization_result.json",
    },
    {
        "mode_id": "union-uniform-nsga2",
        "label": "Union-Uniform NSGA-II",
        "spec_path": REPO_ROOT / "scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml",
        "result_path": REPO_ROOT
        / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-full/2026-03-29-real-test/optimization_result.json",
    },
    {
        "mode_id": "union-llm-nsga2",
        "label": "Union-LLM NSGA-II",
        "spec_path": REPO_ROOT / "scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_kimi_live.yaml",
        "result_path": REPO_ROOT
        / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-kimi-full/2026-03-29-real-test/optimization_result.json",
    },
)

COMPONENT_COLORS = {
    "processor": "#2E86AB",
    "rf_power_amp": "#F18F01",
    "obc": "#6C757D",
    "battery_pack": "#C73E1D",
}
ROLE_LABELS = {
    "processor": "CPU",
    "rf_power_amp": "PA",
    "obc": "OBC",
    "battery_pack": "BAT",
}


@dataclass(slots=True)
class FieldSnapshot:
    case_payload: dict[str, Any]
    temperatures: np.ndarray
    coordinates: np.ndarray
    triangles: np.ndarray
    summary_metrics: dict[str, Any]


def _build_cases_from_record(
    spec_path: Path,
    record: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    spec = load_optimization_spec(spec_path)
    base_cases = generate_benchmark_cases(spec_path, spec)
    vector = np.asarray(
        [
            float(record["decision_vector"][variable["variable_id"]])
            for variable in spec.design_variables
        ],
        dtype=np.float64,
    )
    candidate_cases = {
        operating_case_id: repair_case_from_vector(base_case, spec, vector).to_dict()
        for operating_case_id, base_case in base_cases.items()
    }
    return candidate_cases


def _solve_case_field(case_payload: dict[str, Any]) -> FieldSnapshot:
    solver_inputs = interpret_case(case_payload)
    domain = build_panel_mesh(solver_inputs["panel_domain"], solver_inputs["mesh_profile"])
    problem_data = build_thermal_problem(domain, solver_inputs)
    solver_profile = solver_inputs["solver_profile"]
    petsc_options = {
        "snes_type": "newtonls",
        "snes_atol": float(solver_profile.get("absolute_tolerance", 1.0e-8)),
        "snes_rtol": float(solver_profile.get("relative_tolerance", 1.0e-8)),
        "snes_max_it": int(solver_profile.get("max_iterations", 50)),
        "ksp_type": "preonly",
        "pc_type": "lu",
    }
    problem = NonlinearProblem(
        problem_data["residual"],
        problem_data["temperature"],
        petsc_options_prefix="thermal_",
        petsc_options=petsc_options,
    )
    problem.solve()
    problem_data["temperature"].x.scatter_forward()
    coordinates = problem_data["temperature"].function_space.tabulate_dof_coordinates()[:, :2]
    triangles = _build_triangles(problem_data["temperature"])
    temperatures = np.asarray(problem_data["temperature"].x.array, dtype=np.float64)
    return FieldSnapshot(
        case_payload=case_payload,
        temperatures=temperatures,
        coordinates=np.asarray(coordinates, dtype=np.float64),
        triangles=triangles,
        summary_metrics={
            "temperature_min": float(np.min(temperatures)),
            "temperature_mean": float(np.mean(temperatures)),
            "temperature_max": float(np.max(temperatures)),
        },
    )


def _build_triangles(temperature_function: Any) -> np.ndarray:
    dofmap = temperature_function.function_space.dofmap
    mesh = temperature_function.function_space.mesh
    num_cells = mesh.topology.index_map(mesh.topology.dim).size_local
    triangles = np.asarray([dofmap.cell_dofs(cell) for cell in range(num_cells)], dtype=np.int32)
    return triangles


def _collect_mode_panels() -> tuple[list[dict[str, Any]], dict[str, tuple[float, float]]]:
    mode_panels: list[dict[str, Any]] = []
    operating_case_temperatures: dict[str, list[np.ndarray]] = {"hot": [], "cold": []}
    for config in MODE_CONFIGS:
        result = load_optimization_result(config["result_path"]).to_dict()
        start_record = result["baseline_candidates"][0]
        end_record = result["history"][-1]
        start_cases = _build_cases_from_record(config["spec_path"], start_record)
        end_cases = _build_cases_from_record(config["spec_path"], end_record)
        start_fields = {name: _solve_case_field(case_payload) for name, case_payload in start_cases.items()}
        end_fields = {name: _solve_case_field(case_payload) for name, case_payload in end_cases.items()}
        for operating_case_id in ("hot", "cold"):
            operating_case_temperatures[operating_case_id].append(start_fields[operating_case_id].temperatures)
            operating_case_temperatures[operating_case_id].append(end_fields[operating_case_id].temperatures)
        mode_panels.append(
            {
                "config": config,
                "result": result,
                "start_record": start_record,
                "end_record": end_record,
                "start_fields": start_fields,
                "end_fields": end_fields,
            }
        )
    temperature_ranges = {
        operating_case_id: (
            min(float(np.min(values)) for values in values_list),
            max(float(np.max(values)) for values in values_list),
        )
        for operating_case_id, values_list in operating_case_temperatures.items()
    }
    return mode_panels, temperature_ranges


def render_optimizer_overview(
    *,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    destination = DEFAULT_OUTPUT_DIR if output_dir is None else Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    mode_panels, temperature_ranges = _collect_mode_panels()
    figure = plt.figure(figsize=(23, 15), constrained_layout=False)
    outer = figure.add_gridspec(
        nrows=len(mode_panels),
        ncols=4,
        left=0.04,
        right=0.915,
        bottom=0.05,
        top=0.93,
        hspace=0.28,
        wspace=0.12,
        width_ratios=(1.2, 1.05, 1.2, 1.05),
    )
    figure.suptitle(
        "Temporary Overview of Three NSGA-II Modes\nStart vs End Layout and Hot/Cold Thermal Fields",
        fontsize=18,
        fontweight="bold",
    )
    colorbar_mappables: dict[str, Any] = {}
    metadata_modes: list[dict[str, Any]] = []
    for row_index, panel in enumerate(mode_panels):
        result = panel["result"]
        aggregate = result["aggregate_metrics"]
        row_label = (
            f"{panel['config']['label']}\n"
            f"first feasible={aggregate['first_feasible_eval']}  "
            f"feasible rate={aggregate['feasible_rate']:.3f}  "
            f"pareto={aggregate['pareto_size']}"
        )
        start_layout_ax = figure.add_subplot(outer[row_index, 0])
        _plot_layout(start_layout_ax, panel["start_fields"]["hot"].case_payload)
        start_layout_ax.set_ylabel(row_label, fontsize=11, rotation=90, labelpad=28, fontweight="bold")
        start_thermal_spec = outer[row_index, 1].subgridspec(2, 1, hspace=0.08)
        start_hot_ax = figure.add_subplot(start_thermal_spec[0, 0])
        start_cold_ax = figure.add_subplot(start_thermal_spec[1, 0])
        colorbar_mappables["hot"] = _plot_thermal(
            start_hot_ax,
            panel["start_fields"]["hot"],
            "hot",
            temperature_ranges["hot"],
        )
        colorbar_mappables["cold"] = _plot_thermal(
            start_cold_ax,
            panel["start_fields"]["cold"],
            "cold",
            temperature_ranges["cold"],
        )
        end_layout_ax = figure.add_subplot(outer[row_index, 2])
        _plot_layout(end_layout_ax, panel["end_fields"]["hot"].case_payload)
        end_thermal_spec = outer[row_index, 3].subgridspec(2, 1, hspace=0.08)
        end_hot_ax = figure.add_subplot(end_thermal_spec[0, 0])
        end_cold_ax = figure.add_subplot(end_thermal_spec[1, 0])
        if row_index == 0:
            start_layout_ax.set_title("Start Layout", fontsize=13, fontweight="bold", pad=12)
            start_hot_ax.set_title("Start Thermal", fontsize=13, fontweight="bold", pad=12)
            end_layout_ax.set_title("End Layout", fontsize=13, fontweight="bold", pad=12)
            end_hot_ax.set_title("End Thermal", fontsize=13, fontweight="bold", pad=12)
        _plot_thermal(
            end_hot_ax,
            panel["end_fields"]["hot"],
            "hot",
            temperature_ranges["hot"],
        )
        _plot_thermal(
            end_cold_ax,
            panel["end_fields"]["cold"],
            "cold",
            temperature_ranges["cold"],
        )
        metadata_modes.append(
            {
                "mode_id": panel["config"]["mode_id"],
                "label": panel["config"]["label"],
                "optimization_result_path": str(panel["config"]["result_path"]),
                "spec_path": str(panel["config"]["spec_path"]),
                "start_evaluation_index": panel["start_record"]["evaluation_index"],
                "end_evaluation_index": panel["end_record"]["evaluation_index"],
                "aggregate_metrics": aggregate,
                "start_summary_metrics": {
                    operating_case_id: snapshot.summary_metrics
                    for operating_case_id, snapshot in panel["start_fields"].items()
                },
                "end_summary_metrics": {
                    operating_case_id: snapshot.summary_metrics
                    for operating_case_id, snapshot in panel["end_fields"].items()
                },
            }
        )
    if "hot" in colorbar_mappables:
        hot_colorbar_ax = figure.add_axes([0.93, 0.57, 0.015, 0.27])
        hot_colorbar = figure.colorbar(colorbar_mappables["hot"], cax=hot_colorbar_ax)
        hot_colorbar.set_label("Hot [K]", fontsize=10)
    if "cold" in colorbar_mappables:
        cold_colorbar_ax = figure.add_axes([0.93, 0.16, 0.015, 0.27])
        cold_colorbar = figure.colorbar(colorbar_mappables["cold"], cax=cold_colorbar_ax)
        cold_colorbar.set_label("Cold [K]", fontsize=10)
    image_path = destination / DEFAULT_IMAGE_PATH.name
    metadata_path = destination / DEFAULT_METADATA_PATH.name
    figure.savefig(image_path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    metadata = {
        "image_path": str(image_path),
        "temperature_ranges": {
            operating_case_id: {"min": temperature_range[0], "max": temperature_range[1]}
            for operating_case_id, temperature_range in temperature_ranges.items()
        },
        "modes": metadata_modes,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def _plot_layout(ax: Any, case_payload: dict[str, Any]) -> None:
    width = float(case_payload["panel_domain"]["width"])
    height = float(case_payload["panel_domain"]["height"])
    ax.set_facecolor("#F4F1EA")
    ax.add_patch(plt.Rectangle((0.0, 0.0), width, height, fill=False, edgecolor="#1F2933", linewidth=1.8))
    for component in case_payload["components"]:
        component_width = float(component["geometry"]["width"])
        component_height = float(component["geometry"]["height"])
        center_x = float(component["pose"]["x"])
        center_y = float(component["pose"]["y"])
        lower_left = (center_x - 0.5 * component_width, center_y - 0.5 * component_height)
        role = str(component["role"])
        patch = plt.Rectangle(
            lower_left,
            component_width,
            component_height,
            facecolor=COMPONENT_COLORS.get(role, "#9AA5B1"),
            edgecolor="#1F2933",
            linewidth=1.1,
            alpha=0.75,
        )
        ax.add_patch(patch)
        ax.text(center_x, center_y, ROLE_LABELS.get(role, role), ha="center", va="center", fontsize=8, color="white")
    for feature in case_payload["boundary_features"]:
        if feature["kind"] != "line_sink" or feature["edge"] != "top":
            continue
        start = float(feature["start"]) * width
        end = float(feature["end"]) * width
        ax.plot([start, end], [height, height], color="#D64550", linewidth=5.0, solid_capstyle="round")
    ax.set_xlim(-0.02, width + 0.02)
    ax.set_ylim(-0.02, height + 0.03)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def _plot_thermal(
    ax: Any,
    snapshot: FieldSnapshot,
    operating_case_id: str,
    temperature_range: tuple[float, float],
) -> Any:
    triangulation = mtri.Triangulation(
        snapshot.coordinates[:, 0],
        snapshot.coordinates[:, 1],
        snapshot.triangles,
    )
    image = ax.tripcolor(
        triangulation,
        snapshot.temperatures,
        shading="gouraud",
        cmap="inferno",
        vmin=temperature_range[0],
        vmax=temperature_range[1],
    )
    for component in snapshot.case_payload["components"]:
        component_width = float(component["geometry"]["width"])
        component_height = float(component["geometry"]["height"])
        center_x = float(component["pose"]["x"])
        center_y = float(component["pose"]["y"])
        lower_left = (center_x - 0.5 * component_width, center_y - 0.5 * component_height)
        ax.add_patch(
            plt.Rectangle(
                lower_left,
                component_width,
                component_height,
                fill=False,
                edgecolor="#DCE3EA",
                linewidth=0.9,
            )
        )
    width = float(snapshot.case_payload["panel_domain"]["width"])
    height = float(snapshot.case_payload["panel_domain"]["height"])
    for feature in snapshot.case_payload["boundary_features"]:
        if feature["kind"] != "line_sink" or feature["edge"] != "top":
            continue
        start = float(feature["start"]) * width
        end = float(feature["end"]) * width
        ax.plot([start, end], [height, height], color="#89C2D9", linewidth=3.0, solid_capstyle="round")
    ax.text(
        0.01,
        0.97,
        f"{operating_case_id}  Tmax={snapshot.summary_metrics['temperature_max']:.2f}K",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        color="white",
        bbox={"facecolor": (0.0, 0.0, 0.0, 0.28), "edgecolor": "none", "pad": 3.0},
    )
    ax.set_xlim(0.0, width)
    ax.set_ylim(0.0, height)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    return image


def test_render_optimizer_overview(tmp_path: Path) -> None:
    metadata = render_optimizer_overview(output_dir=tmp_path)

    image_path = Path(metadata["image_path"])
    metadata_path = tmp_path / DEFAULT_METADATA_PATH.name

    assert image_path.exists()
    assert image_path.stat().st_size > 0
    assert metadata_path.exists()
    assert [item["mode_id"] for item in metadata["modes"]] == [
        "pure-native-nsga2",
        "union-uniform-nsga2",
        "union-llm-nsga2",
    ]
    assert metadata["modes"][0]["start_evaluation_index"] == 1
    assert metadata["modes"][2]["aggregate_metrics"]["pareto_size"] == 0


def main() -> None:
    metadata = render_optimizer_overview()
    print(yaml.safe_dump(metadata, sort_keys=False), end="")


if __name__ == "__main__":
    main()
