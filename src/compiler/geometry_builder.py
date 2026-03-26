from __future__ import annotations

from thermal_state import ThermalDesignState
from msfenicsx_viz import ComponentRect


def state_to_component_layout(state: ThermalDesignState) -> list[ComponentRect]:
    heat_source_by_component = {item.component: item.value for item in state.heat_sources}
    material_by_name = state.materials

    layout: list[ComponentRect] = []
    for label, component in enumerate(state.components, start=1):
        material = material_by_name[component.material]
        layout.append(
            ComponentRect(
                name=component.name,
                label=label,
                x0=component.x0,
                y0=component.y0,
                width=component.width,
                height=component.height,
                conductivity=material.conductivity,
                heat_source=heat_source_by_component.get(component.name, 0.0),
            )
        )
    return layout
