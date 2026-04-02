from pathlib import Path

import yaml


def test_s1_typical_eval_objectives_and_radiator_constraint_metric() -> None:
    spec_path = Path("scenarios/evaluation/s1_typical_eval.yaml")
    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    objectives = payload["objectives"]
    objective_ids = [objective["objective_id"] for objective in objectives]
    assert objective_ids == [
        "minimize_peak_temperature",
        "minimize_temperature_gradient_rms",
    ]
    objective_metrics = [objective["metric"] for objective in objectives]
    assert objective_metrics == [
        "summary.temperature_max",
        "summary.temperature_gradient_rms",
    ]

    constraints = payload["constraints"]
    constraint_metrics = [constraint["metric"] for constraint in constraints]
    assert "case.total_radiator_span" in constraint_metrics
    assert any(metric.startswith("component.") and "-001." in metric for metric in constraint_metrics)
    assert any(metric.startswith("components.") for metric in constraint_metrics)
