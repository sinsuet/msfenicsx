from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from orchestration.rollback import rollback_to
from orchestration.run_manager import RunManager
from thermal_state.load_save import load_state


def test_run_manager_creates_incremental_run_directory_and_state_snapshot(tmp_path):
    manager = RunManager(tmp_path)
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")

    run_dir = manager.create_run_dir()
    state_path = manager.save_state_snapshot(state, run_dir)

    assert run_dir.name == "run_0001"
    assert state_path.exists()
    assert (tmp_path / "current_run.txt").read_text(encoding="utf-8").strip() == "run_0001"


def test_rollback_to_updates_current_run_pointer(tmp_path):
    manager = RunManager(tmp_path)

    run_1 = manager.create_run_dir()
    run_2 = manager.create_run_dir()

    rollback_to(tmp_path, run_1.name)

    assert run_1.exists()
    assert run_2.exists()
    assert (tmp_path / "current_run.txt").read_text(encoding="utf-8").strip() == "run_0001"
