from pathlib import Path

from optimizers.matrix.config import build_s5_s7_budgeted_matrix
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

    matrix = build_s5_s7_budgeted_matrix()
    index_path = run_matrix_block(
        matrix,
        matrix_root=tmp_path,
        block_id="M2_nsga2_union_budgeted",
        max_leaves=2,
    )

    assert index_path == tmp_path / "run_index.csv"
    assert calls == [("M2_nsga2_union_budgeted", "8"), ("M2_nsga2_union_budgeted", "8")]
    text = index_path.read_text(encoding="utf-8")
    assert "completed" in text


def test_run_matrix_block_uses_block_concurrency_cap(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def fake_run_rows(rows, *, matrix, leaves_by_key, max_workers):
        captured["max_workers"] = max_workers
        return [dict(row, status="completed") for row in rows]

    monkeypatch.setattr("optimizers.matrix.runner._run_rows_concurrently", fake_run_rows)

    matrix = build_s5_s7_budgeted_matrix()
    run_matrix_block(matrix, matrix_root=tmp_path, block_id="M1_raw_backbone_budgeted", max_leaves=2)

    assert captured["max_workers"] == 80


def test_run_matrix_block_can_generate_attempt_two_for_failed_rows(tmp_path: Path, monkeypatch) -> None:
    from optimizers.matrix.index import build_initial_index_rows, write_run_index

    matrix = build_s5_s7_budgeted_matrix()
    rows = build_initial_index_rows(matrix.expand_leaves()[:2], matrix_root=tmp_path)
    rows[0]["status"] = "failed"
    rows[1]["status"] = "completed"
    write_run_index(tmp_path / "run_index.csv", rows)

    monkeypatch.setattr("optimizers.matrix.runner._run_rows_concurrently", lambda rows, **kwargs: [dict(row, status="completed") for row in rows])

    run_matrix_block(matrix, matrix_root=tmp_path, block_id="M4_rerun_failed_budgeted")

    text = (tmp_path / "run_index.csv").read_text(encoding="utf-8")
    assert "attempt-2" in text
    assert ",2,1,completed," in text


def test_source_block_maps_all_llm_profiles() -> None:
    from optimizers.matrix.runner import _source_block_for_method

    assert _source_block_for_method("nsga2_llm_gpt_5_4") == "M3a_llm_gpt_5_4_budgeted"
    assert _source_block_for_method("nsga2_llm_qwen3_6_plus") == "M3b_llm_qwen3_6_plus_budgeted"
    assert _source_block_for_method("nsga2_llm_glm_5") == "M3c_llm_glm_5_budgeted"
    assert _source_block_for_method("nsga2_llm_minimax_m2_5") == "M3d_llm_minimax_m2_5_budgeted"
    assert _source_block_for_method("nsga2_llm_deepseek_v4_flash") == "M3e_llm_deepseek_v4_flash_budgeted"
    assert _source_block_for_method("nsga2_llm_gemma4") == "M3f_llm_gemma4_budgeted"
    assert _source_block_for_method("nsga2_llm_mimo_v2_5") == "M3g_llm_mimo_v2_5_budgeted"
