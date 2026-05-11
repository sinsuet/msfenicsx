import math
from pathlib import Path

import pytest

from tools.export_stage_a_artifacts import (
    ALGORITHM_BASELINE_ARCHIVE_ROOT,
    ALGORITHM_BASELINE_OUTPUT_ROOT,
    MAIN_BLOCK_SEEDS,
    MAIN_OUTPUT_ROOT,
    MODEL_SENSITIVITY_LABELS,
    MODEL_SENSITIVITY_MAIN_SOURCES,
    S4_SEMANTIC_ABLATION_ROOT,
    S4_SEMANTIC_SEED11_SOURCES,
    S5_REPRESENTATIVE_SOURCES,
    S6_SEED23_MECHANISM_SOURCES,
    stage_a_manifest_updates,
    sorted_seed_text,
    stage_a_series_label_overrides,
)


def test_s6_seed23_mechanism_sources_are_three_way() -> None:
    assert list(S6_SEED23_MECHANISM_SOURCES) == [
        "raw_seed23",
        "llm_normal_seed23",
        "llm_feedback_off_seed23",
    ]
    assert S6_SEED23_MECHANISM_SOURCES["raw_seed23"].as_posix().endswith(
        "raw/seeds/seed-23"
    )
    assert S6_SEED23_MECHANISM_SOURCES["llm_normal_seed23"].as_posix().endswith(
        "llm-deepseek-v4-flash/seeds/seed-23"
    )
    assert S6_SEED23_MECHANISM_SOURCES["llm_feedback_off_seed23"].as_posix().endswith(
        "llm-feedback-off-deepseek-v4-flash/seeds/seed-23"
    )


def test_s5_seed23_representative_sources_are_raw_and_llm_only() -> None:
    assert list(S5_REPRESENTATIVE_SOURCES) == [
        "raw_seed23",
        "llm_seed23",
    ]
    assert S5_REPRESENTATIVE_SOURCES["raw_seed23"].as_posix().endswith(
        "raw/seeds/seed-23"
    )
    assert S5_REPRESENTATIVE_SOURCES["llm_seed23"].as_posix().endswith(
        "llm-deepseek-v4-flash/seeds/seed-23"
    )


def test_s4_semantic_ablation_export_sources_cover_seed11_three_way() -> None:
    assert S4_SEMANTIC_ABLATION_ROOT.as_posix().endswith(
        "0510_archive__raw_union_llm-deepseek_v4_flash_5seed"
    )
    assert list(S4_SEMANTIC_SEED11_SOURCES) == [
        "raw_seed11",
        "union_seed11",
        "llm_deepseek_v4_flash_seed11",
    ]
    assert S4_SEMANTIC_SEED11_SOURCES["raw_seed11"].as_posix().endswith(
        "raw/seeds/seed-11"
    )
    assert S4_SEMANTIC_SEED11_SOURCES["union_seed11"].as_posix().endswith(
        "union/seeds/seed-11"
    )
    assert S4_SEMANTIC_SEED11_SOURCES["llm_deepseek_v4_flash_seed11"].as_posix().endswith(
        "llm-deepseek-v4-flash/seeds/seed-11"
    )


def test_model_sensitivity_main_sources_are_four_llm_profiles() -> None:
    assert list(MODEL_SENSITIVITY_MAIN_SOURCES) == [
        "llm_deepseek_v4_flash_seed11",
        "llm_qwen3_6_plus_seed11",
        "llm_gpt_5_5_seed11",
        "llm_mimo_v2_5_seed11",
    ]
    assert MODEL_SENSITIVITY_LABELS == {
        "llm_deepseek_v4_flash_seed11": "DeepSeek-V4-Flash",
        "llm_qwen3_6_plus_seed11": "Qwen3.6-Plus",
        "llm_gpt_5_5_seed11": "GPT-5.5",
        "llm_mimo_v2_5_seed11": "MiMo-V2.5",
    }
    for key, path in MODEL_SENSITIVITY_MAIN_SOURCES.items():
        assert key.endswith("_seed11")
        assert path.as_posix().endswith("seeds/seed-11")


def test_stage_a_label_overrides_are_paper_facing() -> None:
    labels = stage_a_series_label_overrides(
        {
            "raw_seed23": Path("a/raw/seeds/seed-23"),
            "llm_normal_seed23": Path("b/llm/seeds/seed-23"),
            "llm_feedback_off_seed23": Path("c/llm/seeds/seed-23"),
        },
        {
            "raw_seed23": "Raw seed23",
            "llm_normal_seed23": "LLM seed23",
            "llm_feedback_off_seed23": "Feedback-off LLM seed23",
        },
    )
    assert labels == {
        "a/raw/seeds/seed-23": "Raw seed23",
        "b/llm/seeds/seed-23": "LLM seed23",
        "c/llm/seeds/seed-23": "Feedback-off LLM seed23",
    }
    assert all("Normal" not in label and "normal" not in label for label in labels.values())


def test_s5_representative_label_uses_llm_without_normal_qualifier() -> None:
    labels = stage_a_series_label_overrides(
        {
            "raw_seed23": Path("a/raw/seeds/seed-23"),
            "llm_seed23": Path("b/llm/seeds/seed-23"),
        },
        {
            "raw_seed23": "Raw seed23",
            "llm_seed23": "LLM seed23",
        },
    )

    assert labels == {
        "a/raw/seeds/seed-23": "Raw seed23",
        "b/llm/seeds/seed-23": "LLM seed23",
    }
    assert all("Normal" not in label and "normal" not in label for label in labels.values())


def test_seed_text_uses_sorted_order_for_stage_a_blocks() -> None:
    assert MAIN_BLOCK_SEEDS["main_s4"] == [11, 13, 17, 19, 23]
    assert MAIN_BLOCK_SEEDS["main_s5"] == [11, 19, 23, 37, 41]
    assert MAIN_BLOCK_SEEDS["main_s6"] == [11, 13, 19, 21, 23]
    assert sorted_seed_text([23, 11, 19, 13, 21]) == "11/13/19/21/23"


def test_algorithm_baseline_export_sources_point_to_existing_archive() -> None:
    assert ALGORITHM_BASELINE_ARCHIVE_ROOT.as_posix().endswith(
        "0511_archive__algorithm_compare_raw"
    )
    assert ALGORITHM_BASELINE_OUTPUT_ROOT.as_posix().endswith(
        "paper_database/paper_experiment_db/figures/algorithm_baseline"
    )


def test_main_output_root_is_paper_facing() -> None:
    assert MAIN_OUTPUT_ROOT.as_posix().endswith(
        "paper_database/paper_experiment_db/figures/main"
    )


def test_block_aggregate_rows_preserve_igd_and_add_display_labels() -> None:
    from tools.export_stage_a_artifacts import _block_aggregate_rows

    rows = [
        {
            "block_id": "main_s5",
            "scenario_id": "s5_aggressive15",
            "method_slug": "raw",
            "normalized_final_igd_mean": "0.8",
            "final_igd_mean": "0.8",
        },
        {
            "block_id": "main_s5",
            "scenario_id": "s5_aggressive15",
            "method_slug": "llm",
            "normalized_final_igd_mean": "0.1",
            "final_igd_mean": "0.1",
        },
        {
            "block_id": "algorithm_baseline_s5",
            "scenario_id": "s5_aggressive15",
            "method_slug": "moead-raw",
            "normalized_final_igd_mean": "0.2",
        },
    ]

    filtered = _block_aggregate_rows(rows, "main_s5")

    assert [row["series_label"] for row in filtered] == ["raw", "LLM DeepSeek"]
    assert [row["normalized_final_igd_mean"] for row in filtered] == ["0.8", "0.1"]


def test_block_archive_dense_nigd_uses_pooled_archive_reference(tmp_path: Path) -> None:
    from tools.export_stage_a_artifacts import (
        _apply_block_archive_dense_nigd,
        _write_rows_csv,
    )

    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    for run in (run_a, run_b):
        (run / "analytics").mkdir(parents=True)
        (run / "traces").mkdir(parents=True)

    _write_rows_csv(
        run_a / "analytics" / "pareto_front.csv",
        [{"temperature_max": 0.0, "temperature_gradient_rms": 1.0}],
    )
    _write_rows_csv(
        run_b / "analytics" / "pareto_front.csv",
        [{"temperature_max": 1.0, "temperature_gradient_rms": 0.0}],
    )
    (run_a / "traces" / "evaluation_events.jsonl").write_text(
        '{"status":"ok","objectives":{"temperature_max":0.0,"temperature_gradient_rms":1.0}}\n'
        '{"status":"ok","objectives":{"temperature_max":0.5,"temperature_gradient_rms":0.5}}\n',
        encoding="utf-8",
    )
    (run_b / "traces" / "evaluation_events.jsonl").write_text(
        '{"status":"ok","objectives":{"temperature_max":1.0,"temperature_gradient_rms":0.0}}\n',
        encoding="utf-8",
    )
    seed_rows = [
        {
            "block_id": "main_s5",
            "method_slug": "raw",
            "benchmark_seed": "11",
            "normalized_final_igd": "0",
            "source_run": run_a.as_posix(),
        },
        {
            "block_id": "main_s5",
            "method_slug": "llm",
            "benchmark_seed": "11",
            "normalized_final_igd": "0",
            "source_run": run_b.as_posix(),
        },
    ]

    updated_seed_rows, aggregate_rows, pairwise_rows = _apply_block_archive_dense_nigd(
        seed_rows,
        aggregate_rows=[
            {
                "block_id": "main_s5",
                "method_slug": "raw",
                "normalized_final_igd_mean": "0",
            },
            {
                "block_id": "main_s5",
                "method_slug": "llm",
                "normalized_final_igd_mean": "0",
            },
        ],
        pairwise_rows=[
            {
                "block_id": "main_s5",
                "benchmark_seed": "11",
                "left_method": "raw",
                "right_method": "llm",
            }
        ],
        sample_count=3,
    )

    by_method = {row["method_slug"]: row for row in updated_seed_rows}
    assert by_method["raw"]["igd_reference_scope"] == "main_s5:block_archive_dense"
    assert by_method["raw"]["igd_reference_point_count"] == 3
    assert by_method["raw"]["igd_reference_policy"] == "block_archive_dense_nigd"
    assert float(by_method["raw"]["normalized_final_igd"]) == pytest.approx(math.sqrt(2.0) / 2.0)
    assert float(by_method["llm"]["normalized_final_igd"]) == pytest.approx(math.sqrt(2.0) / 2.0)
    assert aggregate_rows[0]["normalized_final_igd_mean"] == pytest.approx(math.sqrt(2.0) / 2.0)
    assert pairwise_rows[0]["delta_normalized_final_igd"] == pytest.approx(0.0)


def test_archive_dense_nigd_does_not_renormalize_candidate_subset() -> None:
    from tools.export_stage_a_artifacts import _igd_on_normalized_points

    value = _igd_on_normalized_points(
        [(0.0, 0.0), (0.0, 0.2)],
        [(0.0, 0.0), (0.0, 0.5), (0.0, 1.0)],
    )

    assert value == pytest.approx((0.0 + 0.3 + 0.8) / 3.0)


def test_update_igd_fields_rewrites_csv_rows_and_summary_json(tmp_path: Path) -> None:
    import csv
    import json

    from tools.export_stage_a_artifacts import _update_igd_fields_in_export_bundle

    table = tmp_path / "tables" / "mode_metrics.csv"
    table.parent.mkdir(parents=True)
    table.write_text(
        "mode,run,final_igd,igd_direction\n"
        "raw,/tmp/run-a,0.0,lower_is_better\n"
        "llm,/tmp/run-b,0.0,lower_is_better\n",
        encoding="utf-8",
    )
    summary_table = tmp_path / "tables" / "summary_table.csv"
    summary_table.write_text(
        "mode,series_label,final_igd,igd_direction\n"
        "raw,Raw,0.0,lower_is_better\n"
        "llm,LLM,0.0,lower_is_better\n",
        encoding="utf-8",
    )
    analytics = tmp_path / "analytics"
    analytics.mkdir()
    summary_json = analytics / "summary_rows.json"
    summary_json.write_text(
        json.dumps(
            {
                "rows": [
                    {"run": "/tmp/run-a", "final_igd": 0.0},
                    {"run": "/tmp/run-b", "final_igd": 0.0},
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    _update_igd_fields_in_export_bundle(
        tmp_path,
            values_by_run={
                "/tmp/run-a": 0.25,
                "/tmp/run-b": 0.125,
            },
            values_by_label={
                "Raw": 0.25,
                "LLM": 0.125,
            },
            policy="test_dense_nigd",
            reference_point_count=201,
        )

    rows = list(csv.DictReader(table.open(newline="", encoding="utf-8")))
    assert [float(row["final_igd"]) for row in rows] == [0.25, 0.125]
    assert [row["igd_reference_policy"] for row in rows] == ["test_dense_nigd", "test_dense_nigd"]

    summary_rows = list(csv.DictReader(summary_table.open(newline="", encoding="utf-8")))
    assert [float(row["final_igd"]) for row in summary_rows] == [0.25, 0.125]
    assert [row["igd_reference_policy"] for row in summary_rows] == ["test_dense_nigd", "test_dense_nigd"]

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert [row["final_igd"] for row in payload["rows"]] == [0.25, 0.125]
    assert [row["igd_reference_policy"] for row in payload["rows"]] == ["test_dense_nigd", "test_dense_nigd"]


def test_update_igd_fields_uses_local_mode_metrics_for_summary_without_run(tmp_path: Path) -> None:
    import csv

    from tools.export_stage_a_artifacts import _update_igd_fields_in_export_bundle

    table = tmp_path / "by_seed" / "seed-41" / "comparison" / "tables" / "mode_metrics.csv"
    table.parent.mkdir(parents=True)
    table.write_text(
        "mode,series_label,run,final_igd,igd_direction\n"
        "raw,raw,/tmp/nsga2,0.0,lower_is_better\n"
        "raw,SPEA2 raw,/tmp/spea2,0.0,lower_is_better\n",
        encoding="utf-8",
    )
    summary_table = table.parent / "summary_table.csv"
    summary_table.write_text(
        "mode,series_label,final_igd,igd_direction\n"
        "raw,raw,0.0,lower_is_better\n"
        "raw,SPEA2 raw,0.0,lower_is_better\n",
        encoding="utf-8",
    )

    _update_igd_fields_in_export_bundle(
        tmp_path,
        values_by_run={
            "/tmp/nsga2": 0.17,
            "/tmp/spea2": 0.06,
        },
        policy="test_dense_nigd",
        reference_point_count=201,
    )

    rows = list(csv.DictReader(summary_table.open(newline="", encoding="utf-8")))
    assert [float(row["final_igd"]) for row in rows] == [0.17, 0.06]
    assert [row["igd_reference_policy"] for row in rows] == ["test_dense_nigd", "test_dense_nigd"]


def test_stage_a_manifest_updates_use_seed23_representative_and_sorted_seeds() -> None:
    updates = stage_a_manifest_updates()

    assert "representative_case_s5_seed23" in updates["blocks"]
    assert "representative_case_s5_seed11" not in updates["blocks"]
    assert updates["blocks"]["main_s5"]["seeds"] == [11, 19, 23, 37, 41]
    assert updates["blocks"]["main_s6"]["seeds"] == [11, 13, 19, 21, 23]
    representative_ids = {row["id"] for row in updates["representative_cases"]}
    assert "s5_seed23_raw_llm_representatives" in representative_ids
    assert "s5_seed11_raw_llm_representatives" not in representative_ids


def test_duckdb_csv_import_uses_explicit_csv_dialect(tmp_path: Path) -> None:
    import duckdb

    from tools.export_stage_a_artifacts import _create_duckdb_table_from_csv

    csv_path = tmp_path / "claim_evidence.csv"
    csv_path.write_text(
        "claim_id,block_id,status,comparison_manifest,aggregate_table,by_seed_root,figure_root,notes\n"
        "E-S6-FEEDBACK-001,mechanism_ablation_s6_seed23,diagnostic,"
        "paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/manifest.json,"
        "paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/tables/mode_metrics.csv,,"
        "paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation,"
        "Three-way single-seed diagnostic; excluded from S6 main aggregate.\n",
        encoding="utf-8",
    )

    con = duckdb.connect(":memory:")
    try:
        _create_duckdb_table_from_csv(con, csv_path)
        rows = con.execute('SELECT claim_id, by_seed_root FROM "claim_evidence"').fetchall()
    finally:
        con.close()

    assert rows == [("E-S6-FEEDBACK-001", None)]


def test_artifact_index_refresh_removes_legacy_s6_metrics_row(tmp_path: Path) -> None:
    import csv

    from tools.export_stage_a_artifacts import _append_or_replace_artifact_index_rows

    path = tmp_path / "artifact_index.csv"
    path.write_text(
        "scenario_id,method_slug,seed,artifact_name,artifact_path,exists\n"
        "s6_aggressive20,mechanism-ablation-seed23,23,"
        "tables/s6_seed23_mechanism_ablation_metrics.csv,missing.csv,True\n",
        encoding="utf-8",
    )

    _append_or_replace_artifact_index_rows(
        path,
        [
            {
                "scenario_id": "s6_aggressive20",
                "method_slug": "mechanism-ablation-seed23",
                "seed": "23",
                "artifact_name": "tables/mode_metrics.csv",
                "artifact_path": "paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/tables/mode_metrics.csv",
                "exists": "True",
            }
        ],
    )

    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    assert [row["artifact_name"] for row in rows] == ["tables/mode_metrics.csv"]


def test_claim_evidence_refresh_replaces_stage_a_rows(tmp_path: Path) -> None:
    import csv

    from tools.export_stage_a_artifacts import _append_or_replace_claim_evidence_rows

    path = tmp_path / "claim_evidence.csv"
    path.write_text(
        "claim_id,block_id,status,comparison_manifest,aggregate_table,by_seed_root,figure_root,notes\n"
        "E-S6-FEEDBACK-001,mechanism_ablation_s6_seed23,diagnostic,old.json,old.csv,,old_figures,old notes\n",
        encoding="utf-8",
    )

    _append_or_replace_claim_evidence_rows(
        path,
        [
            {
                "claim_id": "E-S6-FEEDBACK-001",
                "block_id": "mechanism_ablation_s6_seed23",
                "status": "diagnostic",
                "comparison_manifest": "new.json",
                "aggregate_table": "mode_metrics.csv",
                "by_seed_root": "",
                "figure_root": "figures",
                "notes": "diagnostic only",
            }
        ],
    )

    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    assert rows == [
        {
            "claim_id": "E-S6-FEEDBACK-001",
            "block_id": "mechanism_ablation_s6_seed23",
            "status": "diagnostic",
            "comparison_manifest": "new.json",
            "aggregate_table": "mode_metrics.csv",
            "by_seed_root": "",
            "figure_root": "figures",
            "notes": "diagnostic only",
        }
    ]


def test_seed_figure_shortcuts_preserve_existing_bundle_files(tmp_path: Path) -> None:
    from tools.export_stage_a_artifacts import _copy_seed_figure_shortcuts

    source = tmp_path / "source" / "seed-11"
    figures = source / "figures"
    figures.mkdir(parents=True)
    (figures / "hypervolume_progress.png").write_bytes(b"fake-png")

    output = tmp_path / "bundle"
    output.mkdir()
    (output / "manifest.json").write_text('{"keep": true}\n', encoding="utf-8")
    (output / "tables").mkdir()
    (output / "tables" / "mode_metrics.csv").write_text("mode\nraw\n", encoding="utf-8")

    _copy_seed_figure_shortcuts(output, {"raw_seed11": source})

    assert (output / "manifest.json").exists()
    assert (output / "tables" / "mode_metrics.csv").exists()
    assert (output / "raw_seed11" / "hypervolume_progress.png").exists()


def test_seed_figure_shortcuts_copy_search_trajectory_node_summary(tmp_path: Path) -> None:
    from tools.export_stage_a_artifacts import _copy_seed_figure_shortcuts

    source = tmp_path / "source" / "seed-23"
    figures = source / "figures"
    figures.mkdir(parents=True)
    (figures / "search_trajectory_network.png").write_bytes(b"network")
    (figures / "search_trajectory_nodes_by_vector.png").write_bytes(b"nodes")

    output = tmp_path / "bundle"
    _copy_seed_figure_shortcuts(output, {"llm_seed23": source})

    assert (output / "llm_seed23" / "search_trajectory_network.png").exists()
    assert (output / "llm_seed23" / "search_trajectory_nodes_by_vector.png").exists()
