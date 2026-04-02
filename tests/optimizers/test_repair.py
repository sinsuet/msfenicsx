from pathlib import Path

import numpy as np
import pytest

from core.contracts.case_contracts import assert_case_geometry_contracts
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
