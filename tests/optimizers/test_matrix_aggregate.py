from optimizers.matrix.aggregate import summarize_outcomes, paired_differences


def test_summarize_outcomes_reports_median_iqr_mean_std_and_feasible_rate() -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "10", "final_hypervolume": "0.1", "feasible": "true"},
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "12", "final_hypervolume": "0.2", "feasible": "true"},
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "14", "final_hypervolume": "0.3", "feasible": "false"},
    ]

    summary = summarize_outcomes(rows, metric="best_temperature_max")

    assert len(summary) == 1
    item = summary[0]
    assert item["scenario_id"] == "s5"
    assert item["method_id"] == "raw"
    assert item["n_runs"] == 3
    assert item["median"] == 12.0
    assert item["q1"] == 11.0
    assert item["q3"] == 13.0
    assert item["mean"] == 12.0
    assert round(item["std"], 6) == 2.0
    assert item["feasible_rate"] == 2 / 3


def test_paired_differences_compare_matched_replicate_seeds() -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "replicate_seed": "11", "best_temperature_max": "10"},
        {"scenario_id": "s5", "method_id": "raw", "replicate_seed": "17", "best_temperature_max": "12"},
        {"scenario_id": "s5", "method_id": "union", "replicate_seed": "11", "best_temperature_max": "8"},
        {"scenario_id": "s5", "method_id": "union", "replicate_seed": "17", "best_temperature_max": "10"},
    ]

    diffs = paired_differences(rows, baseline_method="raw", candidate_method="union", metric="best_temperature_max")

    assert diffs == [
        {
            "scenario_id": "s5",
            "replicate_seed": "11",
            "baseline_method": "raw",
            "candidate_method": "union",
            "baseline_value": 10.0,
            "candidate_value": 8.0,
            "difference": -2.0,
        },
        {
            "scenario_id": "s5",
            "replicate_seed": "17",
            "baseline_method": "raw",
            "candidate_method": "union",
            "baseline_value": 12.0,
            "candidate_value": 10.0,
            "difference": -2.0,
        },
    ]
