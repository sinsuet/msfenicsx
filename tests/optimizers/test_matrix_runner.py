from pathlib import Path

from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.runner import run_matrix_block


def test_run_matrix_block_writes_index_and_invokes_selected_leaves(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_run_leaf(row, *, evaluation_workers: int) -> dict[str, str]:
        calls.append((row["block_id"], str(evaluation_workers)))
        updated = dict(row)
        updated["status"] = "completed"
        updated["actual_evaluations"] = "512"
        updated["feasible_count"] = "9"
        return updated

    monkeypatch.setattr("optimizers.matrix.runner._run_leaf", fake_run_leaf)

    matrix = build_s5_s7_512eval_matrix()
    index_path = run_matrix_block(
        matrix,
        matrix_root=tmp_path,
        block_id="M2_nsga2_union_512eval",
        max_leaves=2,
    )

    assert index_path == tmp_path / "run_index.csv"
    assert calls == [("M2_nsga2_union_512eval", "8"), ("M2_nsga2_union_512eval", "8")]
    text = index_path.read_text(encoding="utf-8")
    assert "completed" in text


def test_run_matrix_block_uses_block_concurrency_cap(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def fake_run_rows(rows, *, matrix, leaves_by_key, max_workers):
        captured["max_workers"] = max_workers
        return [dict(row, status="completed") for row in rows]

    monkeypatch.setattr("optimizers.matrix.runner._run_rows_concurrently", fake_run_rows)

    matrix = build_s5_s7_512eval_matrix()
    run_matrix_block(matrix, matrix_root=tmp_path, block_id="M1_raw_backbone_512eval", max_leaves=2)

    assert captured["max_workers"] == 80


def test_run_matrix_block_can_generate_attempt_two_for_failed_rows(tmp_path: Path, monkeypatch) -> None:
    from optimizers.matrix.index import build_initial_index_rows, write_run_index

    matrix = build_s5_s7_512eval_matrix()
    rows = build_initial_index_rows(matrix.expand_leaves()[:2], matrix_root=tmp_path)
    rows[0]["status"] = "failed"
    rows[1]["status"] = "completed"
    write_run_index(tmp_path / "run_index.csv", rows)

    monkeypatch.setattr("optimizers.matrix.runner._run_rows_concurrently", lambda rows, **kwargs: [dict(row, status="completed") for row in rows])

    run_matrix_block(matrix, matrix_root=tmp_path, block_id="M4_rerun_failed_512eval")

    text = (tmp_path / "run_index.csv").read_text(encoding="utf-8")
    assert "attempt-2" in text
    assert ",2,1,completed," in text
