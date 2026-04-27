from __future__ import annotations

import pytest

from core.generator.pipeline import generate_case
from core.geometry.layout_rules import component_within_domain, components_violate_clearance


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


def test_s3_scale20_generates_twenty_legal_components_for_seed_11() -> None:
    case_payload = generate_case("scenarios/templates/s3_scale20.yaml", seed=11).to_dict()

    assert case_payload["case_meta"]["scenario_id"] == "s3_scale20"
    assert len(case_payload["components"]) == 20
    assert len(case_payload["loads"]) == 20
    _assert_no_clearance_violations(case_payload)


def test_s3_scale20_layout_metrics_hit_scale_band_for_seed_11() -> None:
    case_payload = generate_case("scenarios/templates/s3_scale20.yaml", seed=11).to_dict()
    metrics = case_payload["provenance"]["layout_metrics"]

    assert 0.52 <= metrics["component_area_ratio"] <= 0.55
    assert metrics["nearest_neighbor_gap_mean"] >= 0.0
    assert metrics["bbox_fill_ratio"] >= 0.45


def test_s3_scale20_seed_11_keeps_staged_hot_lane() -> None:
    case_payload = generate_case("scenarios/templates/s3_scale20.yaml", seed=11).to_dict()
    by_family = {component["family_id"]: component for component in case_payload["components"]}

    for family_id in ("c02", "c04", "c12"):
        assert float(by_family[family_id]["pose"]["x"]) >= 0.50
    assert float(by_family["c17"]["pose"]["y"]) >= 0.60


@pytest.mark.parametrize("seed", [11, 17, 23])
def test_s3_scale20_generation_is_stable_for_seed_sample(seed: int) -> None:
    case_payload = generate_case("scenarios/templates/s3_scale20.yaml", seed=seed).to_dict()

    assert len(case_payload["components"]) == 20
    _assert_no_clearance_violations(case_payload)
