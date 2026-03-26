from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from orchestration.demo_dataset import prepare_demo_dataset_workspace


def test_prepare_demo_dataset_archives_old_runs_and_creates_clean_targets(tmp_path):
    runs_root = tmp_path / "runs"
    (runs_root / "run_0001").mkdir(parents=True)
    (runs_root / "run_0001" / "marker.txt").write_text("old-run", encoding="utf-8")
    (runs_root / "current_run.txt").write_text("run_0001\n", encoding="utf-8")

    result = prepare_demo_dataset_workspace(tmp_path, archive_label="demo_official")

    archived_runs = tmp_path / "runs_archive" / "demo_official" / "runs"
    demo_runs_root = tmp_path / "demo_runs" / "official_10_iter"

    assert archived_runs.exists()
    assert (archived_runs / "run_0001" / "marker.txt").exists()
    assert (archived_runs / "current_run.txt").exists()
    assert Path(result["archived_runs_root"]) == archived_runs
    assert Path(result["demo_runs_root"]) == demo_runs_root
    assert (tmp_path / "runs").exists()
    assert list((tmp_path / "runs").iterdir()) == []
    assert demo_runs_root.exists()
    assert list(demo_runs_root.iterdir()) == []


def test_prepare_demo_dataset_archives_existing_demo_runs(tmp_path):
    demo_runs_root = tmp_path / "demo_runs" / "official_10_iter"
    (demo_runs_root / "run_0001").mkdir(parents=True)
    (demo_runs_root / "run_0001" / "marker.txt").write_text("demo-run", encoding="utf-8")

    result = prepare_demo_dataset_workspace(tmp_path, archive_label="demo_retry")

    archived_demo_runs = tmp_path / "runs_archive" / "demo_retry" / "demo_runs" / "official_10_iter"

    assert archived_demo_runs.exists()
    assert (archived_demo_runs / "run_0001" / "marker.txt").exists()
    assert Path(result["demo_runs_root"]) == demo_runs_root
    assert demo_runs_root.exists()
    assert list(demo_runs_root.iterdir()) == []
