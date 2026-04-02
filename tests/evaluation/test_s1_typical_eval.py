from pathlib import Path

import yaml


def test_s1_typical_eval_objectives_and_radiator_constraint_metric() -> None:
    spec_path = Path("scenarios/evaluation/s1_typical_eval.yaml")
    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    objective_ids = [objective["objective_id"] for objective in payload["objectives"]]
    assert objective_ids == [
        "minimize_peak_temperature",
        "minimize_temperature_gradient_rms",
    ]

    constraint_metrics = [constraint["metric"] for constraint in payload["constraints"]]
    assert "case.total_radiator_span" in constraint_metrics
