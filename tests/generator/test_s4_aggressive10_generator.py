from __future__ import annotations

from core.generator.pipeline import generate_case
from core.geometry.layout_rules import component_within_domain, components_violate_clearance


TEMPLATE = "scenarios/templates/s4_aggressive10.yaml"


def _clearance_by_family(case_payload: dict) -> dict[str, float]:
    return {
        str(component.get("family_id", "")): float(component.get("clearance", 0.0))
        for component in case_payload["components"]
        if component.get("family_id") is not None
    }


def _assert_no_clearance_violations(case_payload: dict) -> None:
    clearance_by_family = _clearance_by_family(case_payload)
    components = case_payload["components"]
    for index, component in enumerate(components):
        assert component_within_domain(component, case_payload["panel_domain"])
        for other in components[index + 1 :]:
            assert not components_violate_clearance(component, other, clearance_by_family), (
                f"clearance violation between {component['component_id']} and {other['component_id']}"
            )


def test_s4_aggressive10_generates_legal_seed_11_case() -> None:
    case_payload = generate_case(TEMPLATE, seed=11).to_dict()

    assert case_payload["case_meta"]["scenario_id"] == "s4_aggressive10"
    assert len(case_payload["components"]) == 10
    assert len(case_payload["loads"]) == 10
    _assert_no_clearance_violations(case_payload)


def test_s4_aggressive10_seed_11_keeps_top_sink_and_load_shape() -> None:
    case_payload = generate_case(TEMPLATE, seed=11).to_dict()

    assert len(case_payload["boundary_features"]) == 1
    sink = case_payload["boundary_features"][0]
    assert sink["kind"] == "line_sink"
    assert sink["edge"] == "top"
    assert 0.39 <= float(sink["end"]) - float(sink["start"]) <= 0.41

    total_load = sum(float(load["total_power"]) for load in case_payload["loads"])
    assert 98.0 <= total_load <= 106.0


def test_s4_aggressive10_seed_11_layout_metrics_are_in_low_dimensional_dense_band() -> None:
    case_payload = generate_case(TEMPLATE, seed=11).to_dict()
    metrics = case_payload["provenance"]["layout_metrics"]

    assert 0.27 <= metrics["component_area_ratio"] <= 0.31
    assert metrics["nearest_neighbor_gap_mean"] >= 0.0
    assert metrics["bbox_fill_ratio"] >= 0.35
