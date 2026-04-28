from __future__ import annotations

from pathlib import Path
import json

import pytest

from optimizers.io import load_optimization_spec


@pytest.mark.parametrize(
    ("path", "family", "backbone"),
    [
        ("scenarios/optimization/s1_typical_cmopso_raw.yaml", "swarm", "cmopso"),
        ("scenarios/optimization/s1_typical_spea2_raw.yaml", "genetic", "spea2"),
        ("scenarios/optimization/s1_typical_moead_raw.yaml", "decomposition", "moead"),
    ],
)
def test_s1_additional_algorithm_specs_are_raw_only(
    path: str,
    family: str,
    backbone: str,
) -> None:
    assert Path(path).is_file()

    spec = load_optimization_spec(path)

    assert spec.algorithm["family"] == family
    assert spec.algorithm["backbone"] == backbone
    assert spec.algorithm["mode"] == "raw"
    assert spec.operator_control is None


@pytest.mark.parametrize(
    ("path", "family", "backbone"),
    [
        ("scenarios/optimization/s2_staged_spea2_raw.yaml", "genetic", "spea2"),
        ("scenarios/optimization/s2_staged_cmopso_raw.yaml", "swarm", "cmopso"),
        ("scenarios/optimization/s2_staged_moead_raw.yaml", "decomposition", "moead"),
    ],
)
def test_s2_additional_algorithm_specs_are_raw_only(
    path: str,
    family: str,
    backbone: str,
) -> None:
    assert Path(path).is_file()

    spec = load_optimization_spec(path)

    assert spec.algorithm["family"] == family
    assert spec.algorithm["backbone"] == backbone
    assert spec.algorithm["mode"] == "raw"
    assert spec.operator_control is None


def test_s1_additional_algorithms_do_not_add_union_or_llm_specs() -> None:
    forbidden_specs = [
        "scenarios/optimization/s1_typical_cmopso_union.yaml",
        "scenarios/optimization/s1_typical_cmopso_llm.yaml",
        "scenarios/optimization/s1_typical_spea2_union.yaml",
        "scenarios/optimization/s1_typical_spea2_llm.yaml",
    ]

    assert all(not Path(path).exists() for path in forbidden_specs)


def test_s2_additional_algorithms_do_not_add_union_or_llm_specs() -> None:
    forbidden_specs = [
        "scenarios/optimization/s2_staged_cmopso_union.yaml",
        "scenarios/optimization/s2_staged_cmopso_llm.yaml",
        "scenarios/optimization/s2_staged_spea2_union.yaml",
        "scenarios/optimization/s2_staged_spea2_llm.yaml",
    ]

    assert all(not Path(path).exists() for path in forbidden_specs)


def test_layout_panel_metadata_uses_manifest_algorithm_label(tmp_path: Path) -> None:
    from optimizers.render_assets import _layout_panel_metadata

    run_root = tmp_path / "spea2_run"
    run_root.mkdir()
    (run_root / "run.yaml").write_text(
        "\n".join(
            [
                "mode: raw",
                "seeds:",
                "  benchmark: 11",
                "algorithm:",
                "  family: genetic",
                "  backbone: spea2",
                "  label: SPEA2",
                "specs:",
                "  optimization: scenarios/optimization/s1_typical_spea2_raw.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    metadata = _layout_panel_metadata(run_root)

    assert metadata["Algorithm"] == "SPEA2"


def test_collect_run_payload_uses_manifest_algorithm_label(tmp_path: Path) -> None:
    from optimizers.comparison_artifacts import _collect_run_payload

    run_root = tmp_path / "cmopso_raw"
    (run_root / "traces").mkdir(parents=True)
    (run_root / "run.yaml").write_text(
        "\n".join(
            [
                "mode: raw",
                "seeds:",
                "  benchmark: 11",
                "  algorithm: 7",
                "algorithm:",
                "  family: swarm",
                "  backbone: cmopso",
                "  label: CMOPSO",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (run_root / "traces" / "evaluation_events.jsonl").write_text(
        json.dumps(
            {
                "generation": 0,
                "eval_index": 1,
                "objectives": {
                    "temperature_max": 320.0,
                    "temperature_gradient_rms": 3.0,
                },
                "constraints": {"violation": 0.0},
                "status": "ok",
                "timing": {"cheap_ms": 1.0, "solve_ms": 10.0},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "optimization_result.json").write_text(
        json.dumps(
            {
                "history": [
                    {
                        "evaluation_index": 1,
                        "generation": 0,
                        "source": "optimizer",
                        "feasible": True,
                        "solver_skipped": False,
                        "objective_values": {
                            "minimize_peak_temperature": 320.0,
                            "minimize_temperature_gradient_rms": 3.0,
                        },
                        "constraint_values": {"radiator_span_budget": 0.0},
                    }
                ],
                "run_meta": {"algorithm_seed": 7},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    payload = _collect_run_payload(run_root)

    assert payload["summary_row"]["algorithm"] == "CMOPSO"
    assert payload["series_label"] == "CMOPSO raw"


def test_compare_pairwise_rows_use_series_labels_for_raw_algorithms() -> None:
    from optimizers.comparison_artifacts import _pairwise_deltas

    rows = [
        {"mode": "raw", "algorithm": "NSGA-II", "series_label": "raw", "first_feasible_pde_eval": 2},
        {"mode": "raw", "algorithm": "CMOPSO", "series_label": "CMOPSO raw", "first_feasible_pde_eval": 3},
    ]

    pairwise = _pairwise_deltas(rows)

    assert pairwise[0]["left_label"] == "raw"
    assert pairwise[0]["right_label"] == "CMOPSO raw"
    assert pairwise[0]["left_mode"] == "raw"
    assert pairwise[0]["right_mode"] == "raw"
