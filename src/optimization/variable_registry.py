from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizationVariable:
    path: str
    label: str
    description: str
    category: str
    min_value: float
    max_value: float
    step_rule: str
    priority: int
    role: str
    joint_changes: str
    recommended_direction: str
    strategy_note: str


def build_current_case_variable_registry() -> list[OptimizationVariable]:
    return [
        OptimizationVariable(
            path="materials.spreader_material.conductivity",
            label="Spreader Conductivity",
            description="Increase or decrease heat spreader conductivity to improve lateral heat spreading.",
            category="material",
            min_value=20.0,
            max_value=500.0,
            step_rule="single-step ratio must stay within [0.5x, 2.0x]",
            priority=1,
            role="primary",
            joint_changes="allowed",
            recommended_direction="increase",
            strategy_note="Best first-line lever when chip peak temperature is too high.",
        ),
        OptimizationVariable(
            path="materials.base_material.conductivity",
            label="Base Plate Conductivity",
            description="Adjust base plate conductivity to change downstream heat extraction capacity.",
            category="material",
            min_value=5.0,
            max_value=250.0,
            step_rule="single-step ratio must stay within [0.5x, 2.0x]",
            priority=2,
            role="supporting",
            joint_changes="allowed",
            recommended_direction="increase",
            strategy_note="Useful when spreader tuning alone is no longer improving heat removal.",
        ),
        OptimizationVariable(
            path="components.2.width",
            label="Heat Spreader Width",
            description="Change spreader width inside the design domain to widen heat spreading area.",
            category="geometry",
            min_value=0.20,
            max_value=1.00,
            step_rule="single-step ratio must stay within [0.5x, 1.5x]",
            priority=1,
            role="primary",
            joint_changes="allowed",
            recommended_direction="increase",
            strategy_note="Good geometry lever when material-only tuning stalls.",
        ),
        OptimizationVariable(
            path="components.2.height",
            label="Heat Spreader Height",
            description="Change spreader height inside the design domain to alter thermal cross-section.",
            category="geometry",
            min_value=0.05,
            max_value=0.18,
            step_rule="single-step ratio must stay within [0.5x, 1.5x]",
            priority=1,
            role="primary",
            joint_changes="allowed",
            recommended_direction="increase",
            strategy_note="Pairs well with conductivity increases for coordinated spreading improvements.",
        ),
        OptimizationVariable(
            path="components.2.x0",
            label="Heat Spreader X Position",
            description="Move the spreader horizontally within the design domain to better align with the chip.",
            category="geometry",
            min_value=0.0,
            max_value=0.5,
            step_rule="single-step absolute move must stay within 25% of the design-domain width",
            priority=2,
            role="supporting",
            joint_changes="allowed",
            recommended_direction="move_toward_chip_center",
            strategy_note="Prefer smaller moves after size/material changes have established a stable direction.",
        ),
        OptimizationVariable(
            path="components.2.y0",
            label="Heat Spreader Y Position",
            description="Move the spreader vertically within the design domain while avoiding overlap with the chip.",
            category="geometry",
            min_value=0.20,
            max_value=0.40,
            step_rule="single-step absolute move must stay within 25% of the design-domain height",
            priority=2,
            role="supporting",
            joint_changes="allowed",
            recommended_direction="move_toward_chip_with_clearance",
            strategy_note="Use cautiously because legality limits are tighter than for conductivity changes.",
        ),
        OptimizationVariable(
            path="heat_sources.0.value",
            label="Chip Heat Source",
            description="Adjust the chip heat-source intensity for scenario exploration within the current SI-style teaching unit system.",
            category="load",
            min_value=5000.0,
            max_value=50000.0,
            step_rule="single-step ratio must stay within [0.5x, 1.5x]",
            priority=3,
            role="scenario",
            joint_changes="discouraged",
            recommended_direction="decrease",
            strategy_note="Use for what-if studies, not as the main design-improvement lever.",
        ),
    ]


def variable_registry_by_path() -> dict[str, OptimizationVariable]:
    return {item.path: item for item in build_current_case_variable_registry()}
