from core.generator.layout_metrics import measure_layout_quality
from core.generator.pipeline import generate_case


MAIN_DECK = {"x_min": 0.07, "x_max": 0.93, "y_min": 0.06, "y_max": 0.69}
ACTIVE_DECK = {"x_min": 0.12, "x_max": 0.88, "y_min": 0.10, "y_max": 0.67}
DENSE_CORE = {"x_min": 0.24, "x_max": 0.76, "y_min": 0.18, "y_max": 0.55}


def test_measure_layout_quality_reports_v3_density_targets() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11).to_dict()

    metrics = measure_layout_quality(
        case,
        placement_region=MAIN_DECK,
        active_deck=ACTIVE_DECK,
        dense_core=DENSE_CORE,
    )

    assert metrics.component_count == 15
    assert metrics.component_area_ratio >= 0.44
    assert metrics.component_area_ratio <= 0.46
    assert metrics.bbox_fill_ratio >= 0.48
    assert metrics.nearest_neighbor_gap_mean >= 0.0


def test_layout_quality_is_stable_across_seed_sample_for_v3_density() -> None:
    ratios = []
    fill_ratios = []
    for seed in (11, 17, 23, 29, 31):
        case = generate_case("scenarios/templates/s1_typical.yaml", seed=seed).to_dict()
        metrics = measure_layout_quality(
            case,
            placement_region=MAIN_DECK,
            active_deck=ACTIVE_DECK,
            dense_core=DENSE_CORE,
        )
        ratios.append(metrics.component_area_ratio)
        fill_ratios.append(metrics.bbox_fill_ratio)

    assert min(ratios) >= 0.44
    assert max(ratios) <= 0.46
    assert min(fill_ratios) >= 0.48


def test_measure_layout_quality_reports_large_dense_core_void_ratio() -> None:
    compact_case = {
        "components": [
            _rect_component("a", 0.30, 0.28, 0.10, 0.10),
            _rect_component("b", 0.40, 0.28, 0.10, 0.10),
            _rect_component("c", 0.30, 0.38, 0.10, 0.10),
            _rect_component("d", 0.40, 0.38, 0.10, 0.10),
        ]
    }
    large_void_case = {
        "components": [
            _rect_component("a", 0.18, 0.16, 0.10, 0.10),
            _rect_component("b", 0.82, 0.16, 0.10, 0.10),
            _rect_component("c", 0.18, 0.62, 0.10, 0.10),
            _rect_component("d", 0.82, 0.62, 0.10, 0.10),
        ]
    }

    compact_metrics = measure_layout_quality(
        compact_case,
        placement_region=MAIN_DECK,
        active_deck=ACTIVE_DECK,
        dense_core=DENSE_CORE,
    )
    large_void_metrics = measure_layout_quality(
        large_void_case,
        placement_region=MAIN_DECK,
        active_deck=ACTIVE_DECK,
        dense_core=DENSE_CORE,
    )

    assert large_void_metrics.largest_dense_core_void_ratio > compact_metrics.largest_dense_core_void_ratio


def _rect_component(component_id: str, x: float, y: float, width: float, height: float) -> dict[str, object]:
    return {
        "component_id": component_id,
        "role": component_id,
        "shape": "rect",
        "pose": {"x": x, "y": y, "rotation_deg": 0.0},
        "geometry": {"width": width, "height": height},
        "material_ref": "electronics_housing",
    }
