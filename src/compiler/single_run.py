from __future__ import annotations

from pathlib import Path

from mpi4py import MPI

from dolfinx import io

from msfenicsx_viz import (
    build_triangulation,
    component_cell_labels,
    save_layout_figure,
    save_mesh_figure,
    save_overview_html,
    save_subdomain_figure,
    save_temperature_figure,
    save_temperature_html,
    summarize_solution_by_component,
    write_summary_text,
)
from thermal_state import ThermalDesignState, load_state

from .geometry_builder import state_to_component_layout
from .mesh_builder import build_mesh_from_layout
from .physics_builder import build_problem
from .solver_runner import solve_steady_heat


def run_case_from_state(
    state: ThermalDesignState,
    *,
    output_root: str | Path,
    comm: MPI.Comm = MPI.COMM_WORLD,
) -> dict[str, str]:
    output_root = Path(output_root)
    figure_dir = output_root / "figures"
    data_dir = output_root / "data"
    figure_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    layout = state_to_component_layout(state)
    mesh_data, mesh_size = build_mesh_from_layout(layout, state.mesh["nx"], state.mesh["ny"], comm=comm)
    domain = mesh_data.mesh
    cell_tags = mesh_data.cell_tags
    facet_tags = mesh_data.facet_tags

    problem, V = build_problem(
        domain,
        cell_tags,
        facet_tags,
        layout,
        state.boundary_conditions,
        linear_solver=state.solver.linear_solver,
    )
    uh = solve_steady_heat(problem)

    coords, cells, triangulation = build_triangulation(V)
    cell_labels = component_cell_labels(cell_tags, len(cells))
    component_summary = summarize_solution_by_component(layout, cell_tags, V, uh)

    layout_png = figure_dir / "layout.png"
    mesh_png = figure_dir / "mesh.png"
    subdomains_png = figure_dir / "subdomains.png"
    temperature_png = figure_dir / "temperature.png"
    temperature_html = figure_dir / "temperature.html"
    overview_html = figure_dir / "overview.html"
    solution_xdmf = data_dir / "solution.xdmf"
    summary_txt = data_dir / "summary.txt"

    if comm.rank == 0:
        save_layout_figure(layout, layout_png)
        save_mesh_figure(triangulation, mesh_png)
        save_subdomain_figure(triangulation, cell_labels, layout, subdomains_png)
        save_temperature_figure(triangulation, uh.x.array, temperature_png)
        save_temperature_html(coords, cells, uh.x.array, layout, temperature_html)
        write_summary_text(
            summary_txt,
            num_cells=len(cells),
            num_vertices=coords.shape[0],
            temperature_min=float(uh.x.array.min()),
            temperature_max=float(uh.x.array.max()),
            component_summary=component_summary,
            units=state.units,
            reference_conditions=state.reference_conditions,
        )
        save_overview_html(
            overview_html,
            layout=layout,
            layout_png=layout_png,
            mesh_png=mesh_png,
            subdomains_png=subdomains_png,
            temperature_png=temperature_png,
            temperature_html=temperature_html,
            summary_txt=summary_txt,
            component_summary=component_summary,
            units=state.units,
            reference_conditions=state.reference_conditions,
        )

    with io.XDMFFile(domain.comm, str(solution_xdmf), "w") as xdmf:
        xdmf.write_mesh(domain)
        xdmf.write_function(uh)

    if comm.rank == 0:
        temperature_unit = state.units.get("temperature", "degC")
        print("Multicomponent example finished.")
        print(f"Mesh size target: {mesh_size:.5f}")
        print(f"Cells: {len(cells)}")
        print(f"Temperature min ({temperature_unit}): {uh.x.array.min():.6f}")
        print(f"Temperature max ({temperature_unit}): {uh.x.array.max():.6f}")
        for name, stats in component_summary.items():
            print(
                f"{name}: min={stats['min']:.6f}, max={stats['max']:.6f}, mean={stats['mean']:.6f} {temperature_unit}"
            )
        print(f"Interactive HTML: {temperature_html}")
        print(f"Overview HTML: {overview_html}")

    metrics = {
        "temperature_min": float(uh.x.array.min()),
        "temperature_max": float(uh.x.array.max()),
        "component_summary": component_summary,
        "mesh": {
            "num_cells": int(len(cells)),
            "num_vertices": int(coords.shape[0]),
            "target_mesh_size": float(mesh_size),
        },
        "units": dict(state.units),
        "reference_conditions": dict(state.reference_conditions),
    }

    return {
        "layout_png": str(layout_png),
        "mesh_png": str(mesh_png),
        "subdomains_png": str(subdomains_png),
        "temperature_png": str(temperature_png),
        "temperature_html": str(temperature_html),
        "overview_html": str(overview_html),
        "solution_xdmf": str(solution_xdmf),
        "summary_txt": str(summary_txt),
        "metrics": metrics,
    }


def run_case_from_state_file(state_path: str | Path, *, output_root: str | Path) -> dict[str, str]:
    state = load_state(state_path)
    return run_case_from_state(state, output_root=output_root)
