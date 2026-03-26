from __future__ import annotations


def component_bounds(components) -> tuple[float, float, float, float]:
    min_x = min(component.x0 for component in components)
    min_y = min(component.y0 for component in components)
    max_x = max(component.x0 + component.width for component in components)
    max_y = max(component.y0 + component.height for component in components)
    return min_x, min_y, max_x, max_y


def check_components_inside_envelope(components, envelope: tuple[float, float, float, float]) -> list[str]:
    min_x, min_y, max_x, max_y = envelope
    reasons: list[str] = []
    for component in components:
        if component.x0 < min_x or component.y0 < min_y:
            reasons.append(f"component {component.name} moves outside the current envelope")
            continue
        if component.x0 + component.width > max_x or component.y0 + component.height > max_y:
            reasons.append(f"component {component.name} moves outside the current envelope")
    return reasons


def rectangles_overlap(a, b) -> bool:
    return not (
        a.x0 + a.width <= b.x0
        or b.x0 + b.width <= a.x0
        or a.y0 + a.height <= b.y0
        or b.y0 + b.height <= a.y0
    )


def check_component_overlaps(components) -> list[str]:
    reasons: list[str] = []
    for idx, left in enumerate(components):
        for right in components[idx + 1 :]:
            if rectangles_overlap(left, right):
                reasons.append(f"component overlap detected between {left.name} and {right.name}")
    return reasons
