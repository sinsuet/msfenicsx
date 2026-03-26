from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from optimization.variable_registry import build_current_case_variable_registry


def test_variable_registry_contains_expected_paths():
    registry = build_current_case_variable_registry()
    paths = [item.path for item in registry]

    assert "materials.spreader_material.conductivity" in paths
    assert "materials.base_material.conductivity" in paths
    assert "components.2.width" in paths
    assert "components.2.height" in paths
    assert "components.2.x0" in paths
    assert "heat_sources.0.value" in paths
