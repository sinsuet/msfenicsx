from pathlib import Path

from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.index import build_initial_index_rows, failed_retry_rows, write_run_index, read_run_index


def test_run_index_round_trip(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    rows = build_initial_index_rows(matrix.expand_leaves()[:2], matrix_root=tmp_path)
    index_path = write_run_index(tmp_path / "run_index.csv", rows)

    loaded = read_run_index(index_path)

    assert len(loaded) == 2
    assert loaded[0]["matrix_id"] == "s5_s7_512eval"
    assert loaded[0]["attempt"] == "1"
    assert loaded[0]["status"] == "pending"
    assert loaded[0]["nominal_budget"] == "512"


def test_failed_retry_rows_create_attempt_two_only_for_failed_statuses(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    rows = build_initial_index_rows(matrix.expand_leaves()[:3], matrix_root=tmp_path)
    rows[0]["status"] = "completed"
    rows[1]["status"] = "failed"
    rows[2]["status"] = "render_failed"

    retries = failed_retry_rows(rows)

    assert [row["attempt"] for row in retries] == ["2", "2"]
    assert [row["status"] for row in retries] == ["pending", "pending"]
    assert [row["previous_attempt"] for row in retries] == ["1", "1"]
