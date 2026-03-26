from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import yaml

from .schema import (
    BoundaryConditionState,
    ComponentState,
    ConstraintState,
    HeatSourceState,
    MaterialState,
    ObjectiveState,
    SolverState,
    ThermalDesignState,
)


def _require_keys(data: dict, keys: list[str], context: str) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise ValueError(f"Missing keys in {context}: {missing}")


def load_state(path: str | Path) -> ThermalDesignState:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("State file must contain a top-level mapping.")

    _require_keys(
        raw,
        [
            "geometry",
            "components",
            "materials",
            "heat_sources",
            "boundary_conditions",
            "mesh",
            "solver",
            "constraints",
            "objectives",
        ],
        "state file",
    )

    components = [ComponentState(**item) for item in raw["components"]]
    materials = {name: MaterialState(**item) for name, item in raw["materials"].items()}
    heat_sources = [HeatSourceState(**item) for item in raw["heat_sources"]]
    boundary_conditions = [BoundaryConditionState(**item) for item in raw["boundary_conditions"]]
    solver = SolverState(**raw["solver"])
    constraints = [ConstraintState(**item) for item in raw["constraints"]]
    objectives = [ObjectiveState(**item) for item in raw["objectives"]]

    return ThermalDesignState(
        geometry=raw["geometry"],
        components=components,
        materials=materials,
        heat_sources=heat_sources,
        boundary_conditions=boundary_conditions,
        mesh=raw["mesh"],
        solver=solver,
        constraints=constraints,
        objectives=objectives,
        units=raw.get("units", {}),
        reference_conditions=raw.get("reference_conditions", {}),
        metadata=raw.get("metadata", {}),
    )


def save_state(state: ThermalDesignState, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "geometry": state.geometry,
        "components": [asdict(component) for component in state.components],
        "materials": {name: asdict(material) for name, material in state.materials.items()},
        "heat_sources": [asdict(source) for source in state.heat_sources],
        "boundary_conditions": [asdict(item) for item in state.boundary_conditions],
        "mesh": state.mesh,
        "solver": asdict(state.solver),
        "constraints": [asdict(item) for item in state.constraints],
        "objectives": [asdict(item) for item in state.objectives],
        "units": state.units,
        "reference_conditions": state.reference_conditions,
        "metadata": state.metadata,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
