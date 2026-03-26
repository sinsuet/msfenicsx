from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentState:
    name: str
    x0: float
    y0: float
    width: float
    height: float
    material: str


@dataclass(frozen=True)
class MaterialState:
    conductivity: float


@dataclass(frozen=True)
class HeatSourceState:
    component: str
    value: float


@dataclass(frozen=True)
class BoundaryConditionState:
    type: str
    location: str
    value: float


@dataclass(frozen=True)
class ConstraintState:
    name: str
    op: str
    value: float


@dataclass(frozen=True)
class ObjectiveState:
    name: str
    sense: str


@dataclass(frozen=True)
class SolverState:
    kind: str
    linear_solver: str


@dataclass(frozen=True)
class DesignDomainState:
    x0: float
    y0: float
    width: float
    height: float


@dataclass(frozen=True)
class ThermalDesignState:
    geometry: dict
    components: list[ComponentState]
    materials: dict[str, MaterialState]
    heat_sources: list[HeatSourceState]
    boundary_conditions: list[BoundaryConditionState]
    mesh: dict
    solver: SolverState
    constraints: list[ConstraintState]
    objectives: list[ObjectiveState]
    units: dict
    reference_conditions: dict
    metadata: dict
