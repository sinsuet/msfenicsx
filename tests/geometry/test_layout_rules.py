import pytest

from core.contracts.case_contracts import CaseContractError, assert_case_geometry_contracts
from core.generator.pipeline import generate_case
from core.geometry.layout_rules import (
    component_respects_keep_out_regions,
    component_within_domain,
    components_overlap,
)


def _rect_component(component_id: str, x: float, y: float, width: float, height: float) -> dict:
    return {
        "component_id": component_id,
        "role": "payload",
        "shape": "rect",
        "pose": {"x": x, "y": y, "rotation_deg": 0.0},
        "geometry": {"width": width, "height": height},
        "material_ref": "electronics_housing",
    }


def test_component_within_domain_accepts_component_inside_panel() -> None:
    component = _rect_component("comp-001", x=0.3, y=0.4, width=0.2, height=0.1)

    assert component_within_domain(component, {"width": 1.0, "height": 0.8})


def test_components_overlap_detects_positive_area_intersection() -> None:
    component_a = _rect_component("comp-a", x=0.3, y=0.4, width=0.2, height=0.1)
    component_b = _rect_component("comp-b", x=0.35, y=0.4, width=0.2, height=0.1)

    assert components_overlap(component_a, component_b)


def test_component_respects_keep_out_regions_rejects_intersection() -> None:
    component = _rect_component("comp-001", x=0.3, y=0.4, width=0.2, height=0.1)
    keep_out_regions = [
        {
            "region_id": "forbidden",
            "kind": "rect",
            "x_min": 0.25,
            "x_max": 0.45,
            "y_min": 0.35,
            "y_max": 0.5,
        }
    ]

    assert not component_respects_keep_out_regions(component, keep_out_regions)


def test_assert_case_geometry_contracts_accepts_reference_case() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)

    assert_case_geometry_contracts(case)


def test_assert_case_geometry_contracts_rejects_overlapping_components() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11).to_dict()
    case["components"].append(_rect_component("comp-002", x=0.3, y=0.35, width=0.16, height=0.09))

    with pytest.raises(CaseContractError, match="overlap"):
        assert_case_geometry_contracts(case)
