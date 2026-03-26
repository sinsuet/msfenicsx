from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from compiler.single_run import run_case_from_state_file


def test_single_run_from_state_generates_outputs(tmp_path):
    result = run_case_from_state_file(
        ROOT / "states" / "baseline_multicomponent.yaml",
        output_root=tmp_path,
    )

    assert Path(result["overview_html"]).exists()
    assert Path(result["summary_txt"]).exists()


def test_single_run_reports_temperature_units_in_metrics(tmp_path):
    result = run_case_from_state_file(
        ROOT / "states" / "baseline_multicomponent.yaml",
        output_root=tmp_path,
    )

    assert result["metrics"]["units"]["temperature"] == "degC"
    assert result["metrics"]["reference_conditions"]["ambient_temperature"] == 25.0
