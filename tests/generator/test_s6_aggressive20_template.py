from __future__ import annotations

import pytest

from core.generator.pipeline import generate_case
from core.geometry.layout_rules import component_within_domain, components_violate_clearance


S6_TEMPLATE = "scenarios/templates/s6_aggressive20.yaml"


@pytest.fixture(scope="module")
def seed_11_case_payload() -> dict:
    return generate_case(S6_TEMPLATE, seed=11).to_dict()


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


def test_s6_aggressive20_generates_twenty_legal_components_for_seed_11(seed_11_case_payload: dict) -> None:
    case_payload = seed_11_case_payload

    assert case_payload["case_meta"]["scenario_id"] == "s6_aggressive20"
    assert len(case_payload["components"]) == 20
    assert len(case_payload["loads"]) == 20
    _assert_no_clearance_violations(case_payload)


def test_s6_aggressive20_generates_top_edge_sink_for_seed_11(seed_11_case_payload: dict) -> None:
    case_payload = seed_11_case_payload

    assert len(case_payload["boundary_features"]) == 1
    sink = case_payload["boundary_features"][0]
    assert sink["kind"] == "line_sink"
    assert sink["edge"] == "top"
    assert 0.08 <= float(sink["start"]) < float(sink["end"]) <= 0.53
    assert 0.44 <= float(sink["end"]) - float(sink["start"]) <= 0.46


def test_s6_aggressive20_layout_metrics_hit_dense_20_component_band_for_seed_11(seed_11_case_payload: dict) -> None:
    case_payload = seed_11_case_payload
    metrics = case_payload["provenance"]["layout_metrics"]

    assert 0.48 <= metrics["component_area_ratio"] <= 0.50
    assert metrics["nearest_neighbor_gap_mean"] >= 0.0
    assert metrics["bbox_fill_ratio"] >= 0.45


def test_s6_aggressive20_total_load_matches_template_band(seed_11_case_payload: dict) -> None:
    case_payload = seed_11_case_payload

    total_power = sum(float(load["total_power"]) for load in case_payload["loads"])
    assert 155.0 <= total_power <= 166.0
