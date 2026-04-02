import json
from pathlib import Path

import numpy as np
import yaml

from core.io.scenario_runs import write_case_solution_bundle, write_run_bundle


def _field_exports() -> dict[str, object]:
    return {
        "arrays": {
            "temperature": np.array([[300.0, 301.0], [302.0, 303.0]], dtype=np.float64),
            "gradient_magnitude": np.array([[1.0, 1.5], [2.0, 2.5]], dtype=np.float64),
        },
        "field_view": {
            "panel_domain": {"width": 1.0, "height": 0.8},
            "temperature": {
                "grid_shape": [2, 2],
                "min": 300.0,
                "max": 303.0,
                "hotspot": {"x": 1.0, "y": 0.8, "value": 303.0},
                "contour_levels": [300.0, 301.5, 303.0],
            },
            "gradient_magnitude": {
                "grid_shape": [2, 2],
                "min": 1.0,
                "max": 2.5,
            },
            "layout": {
                "components": [{"component_id": "comp-001"}],
                "line_sinks": [{"feature_id": "sink-top-window"}],
            },
        },
    }


def test_write_run_bundle_creates_expected_layout(tmp_path: Path) -> None:
    output = write_run_bundle(
        tmp_path,
        scenario_id="panel-baseline",
        case_id="case-001",
        case_payload={"case_meta": {"case_id": "case-001"}},
        solution_payload={"solution_meta": {"case_id": "case-001"}},
        field_exports=_field_exports(),
    )

    assert (output / "case.yaml").exists()
    assert (output / "solution.yaml").exists()
    assert (output / "manifest.json").exists()
    assert (output / "logs").is_dir()
    assert (output / "fields").is_dir()
    assert (output / "summaries").is_dir()
    assert (output / "figures").is_dir()
    assert (output / "pages").is_dir()
    assert (output / "fields" / "temperature_grid.npz").exists()
    assert (output / "fields" / "gradient_magnitude_grid.npz").exists()
    assert (output / "summaries" / "field_view.json").exists()
    assert not (output / "tensors").exists()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    case_snapshot = yaml.safe_load((output / "case.yaml").read_text(encoding="utf-8"))
    solution_snapshot = yaml.safe_load((output / "solution.yaml").read_text(encoding="utf-8"))
    field_view = json.loads((output / "summaries" / "field_view.json").read_text(encoding="utf-8"))
    temperature_grid = np.load(output / "fields" / "temperature_grid.npz")["values"]

    assert manifest["case_snapshot"] == "case.yaml"
    assert manifest["solution_snapshot"] == "solution.yaml"
    assert manifest["field_exports"]["field_view"] == "summaries/field_view.json"
    assert case_snapshot["case_meta"]["case_id"] == "case-001"
    assert solution_snapshot["solution_meta"]["case_id"] == "case-001"
    assert field_view["temperature"]["grid_shape"] == [2, 2]
    assert temperature_grid.shape == (2, 2)


def test_write_case_solution_bundle_uses_case_ids_and_persists_field_exports(tmp_path: Path) -> None:
    output = write_case_solution_bundle(
        tmp_path,
        case={"case_meta": {"scenario_id": "panel-baseline", "case_id": "case-001"}},
        solution={"solution_meta": {"case_id": "case-001"}},
        field_exports=_field_exports(),
    )

    assert output == tmp_path / "panel-baseline" / "case-001"
    assert (output / "summaries" / "field_view.json").exists()
