from statistics import median

from core.generator.layout_metrics import measure_layout_quality
from core.generator.pipeline import generate_case


MAIN_DECK = {"x_min": 0.05, "x_max": 0.95, "y_min": 0.05, "y_max": 0.72}


def test_measure_layout_quality_reports_compactness_fields() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11).to_dict()

    metrics = measure_layout_quality(case, placement_region=MAIN_DECK)

    assert metrics.component_count == 15
    assert metrics.component_area_ratio > 0.30
    assert metrics.bbox_fill_ratio > 0.30
    assert metrics.nearest_neighbor_gap_mean >= 0.0


def test_layout_quality_is_stable_across_seed_sample() -> None:
    fill_ratios = []
    for seed in range(1, 11):
        case = generate_case("scenarios/templates/s1_typical.yaml", seed=seed).to_dict()
        fill_ratios.append(measure_layout_quality(case, placement_region=MAIN_DECK).bbox_fill_ratio)

    assert median(fill_ratios) > 0.30
