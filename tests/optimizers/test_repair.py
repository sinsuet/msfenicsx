from pathlib import Path

import numpy as np
import pytest

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.geometry.layout_rules import required_clearance_gap
from optimizers.codec import extract_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.repair import repair_case_from_vector


SPEC_PATH = Path("scenarios/optimization/s1_typical_raw.yaml")
RADIATOR_SPAN_MAX = 0.48


def _spec():
    return load_optimization_spec(SPEC_PATH)


def _case():
    spec = _spec()
    return generate_benchmark_case(SPEC_PATH, spec)


def test_repair_case_from_vector_projects_sink_budget_and_restores_case_geometry() -> None:
    case = _case()
    spec = _spec()
    assert len({component["shape"] for component in case.components}) > 1
    vector = extract_decision_vector(case, spec)
    dense_cluster = (0.18, 0.18)
    for component_index in range(5):
        vector[component_index * 2] = dense_cluster[0]
        vector[component_index * 2 + 1] = dense_cluster[1]
    vector[-2] = 0.05
    vector[-1] = 0.95

    repaired = repair_case_from_vector(
        case,
        spec,
        np.asarray(vector, dtype=np.float64),
        radiator_span_max=RADIATOR_SPAN_MAX,
    )
    feature = repaired.boundary_features[0]

    assert_case_geometry_contracts(repaired)
    assert feature["start"] < feature["end"]
    assert feature["end"] - feature["start"] == pytest.approx(RADIATOR_SPAN_MAX)


def test_repair_case_from_vector_restores_mixed_shape_geometry() -> None:
    case = _case()
    spec = _spec()
    vector = extract_decision_vector(case, spec)

    for component_index in range(4):
        vector[component_index * 2] = 0.18
        vector[component_index * 2 + 1] = 0.18

    repaired = repair_case_from_vector(
        case,
        spec,
        np.asarray(vector, dtype=np.float64),
        radiator_span_max=RADIATOR_SPAN_MAX,
    )

    assert len({component["shape"] for component in repaired.components}) > 1
    assert_case_geometry_contracts(repaired)


def test_repair_case_from_vector_restores_required_clearance_gap() -> None:
    case = _case()
    spec = _spec()
    vector = extract_decision_vector(case, spec)

    vector[0] = 0.20
    vector[1] = 0.20
    vector[2] = 0.345
    vector[3] = 0.20

    repaired = repair_case_from_vector(
        case,
        spec,
        np.asarray(vector, dtype=np.float64),
        radiator_span_max=RADIATOR_SPAN_MAX,
    )

    left = repaired.components[0].to_dict() if hasattr(repaired.components[0], "to_dict") else repaired.components[0]
    right = repaired.components[1].to_dict() if hasattr(repaired.components[1], "to_dict") else repaired.components[1]
    clearance_by_family = {
        component["family_id"]: float(component.get("clearance", 0.0))
        for component in case.components
    }

    assert required_clearance_gap(left, right, clearance_by_family) >= 0.0


def test_repair_case_from_vector_refreshes_candidate_layout_metrics() -> None:
    case = _case()
    spec = _spec()
    vector = extract_decision_vector(case, spec)
    baseline_metrics = dict(case.provenance["layout_metrics"])

    for component_index in range(5):
        vector[component_index * 2] = 0.18
        vector[component_index * 2 + 1] = 0.18

    repaired = repair_case_from_vector(
        case,
        spec,
        np.asarray(vector, dtype=np.float64),
        radiator_span_max=RADIATOR_SPAN_MAX,
    )
    repaired_metrics = dict(repaired.provenance["layout_metrics"])

    assert "layout_context" in repaired.provenance
    assert repaired_metrics["centroid_dispersion"] > baseline_metrics["centroid_dispersion"]
