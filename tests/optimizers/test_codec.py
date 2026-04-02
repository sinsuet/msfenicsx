import numpy as np
import pytest

from core.generator.pipeline import generate_case
from optimizers.codec import DecisionVectorError, apply_decision_vector, extract_decision_vector
from optimizers.io import load_optimization_spec


def _case():
    return generate_case("scenarios/templates/s1_typical.yaml", seed=11)


def _spec():
    return load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")


def test_extract_and_apply_decision_vector_round_trip_for_s1_typical_layout_variables() -> None:
    case = _case()
    spec = _spec()

    vector = extract_decision_vector(case, spec)
    mutated_vector = vector.copy()
    mutated_vector[0] = 0.42
    mutated_vector[1] = 0.6
    mutated_vector[-2] = 0.12
    mutated_vector[-1] = 0.52
    mutated = apply_decision_vector(case, spec, mutated_vector)

    assert vector.shape == (32,)
    assert vector[0] == pytest.approx(case.components[0]["pose"]["x"])
    assert vector[1] == pytest.approx(case.components[0]["pose"]["y"])
    assert vector[-2] == pytest.approx(case.boundary_features[0]["start"])
    assert vector[-1] == pytest.approx(case.boundary_features[0]["end"])
    assert mutated.components[0]["pose"]["x"] == pytest.approx(0.42)
    assert mutated.components[0]["pose"]["y"] == pytest.approx(0.6)
    assert mutated.boundary_features[0]["start"] == pytest.approx(0.12)
    assert mutated.boundary_features[0]["end"] == pytest.approx(0.52)
    assert case.components[0]["pose"]["x"] == pytest.approx(vector[0])


def test_apply_decision_vector_rejects_out_of_bounds_values() -> None:
    vector = extract_decision_vector(_case(), _spec())
    vector[0] = 1.2

    with pytest.raises(DecisionVectorError):
        apply_decision_vector(_case(), _spec(), vector)
