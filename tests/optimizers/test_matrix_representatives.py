from optimizers.matrix.representatives import plan_compare_bundles, select_best_hv_representatives, select_knee_point


def test_select_best_hv_representatives_picks_best_successful_run_per_cell() -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "status": "completed", "final_hypervolume": "0.2", "run_root": "run-a"},
        {"scenario_id": "s5", "method_id": "raw", "status": "completed", "final_hypervolume": "0.5", "run_root": "run-b"},
        {"scenario_id": "s5", "method_id": "raw", "status": "failed", "final_hypervolume": "0.9", "run_root": "run-c"},
        {"scenario_id": "s5", "method_id": "union", "status": "completed", "final_hypervolume": "0.4", "run_root": "run-d"},
    ]

    selected = select_best_hv_representatives(rows)

    assert selected == [
        {"scenario_id": "s5", "method_id": "raw", "run_root": "run-b", "final_hypervolume": 0.5},
        {"scenario_id": "s5", "method_id": "union", "run_root": "run-d", "final_hypervolume": 0.4},
    ]


def test_select_knee_point_picks_point_nearest_ideal_after_minmax_scaling() -> None:
    points = [
        {"candidate_id": "a", "temperature_max": "100", "gradient_rms": "50"},
        {"candidate_id": "b", "temperature_max": "80", "gradient_rms": "80"},
        {"candidate_id": "c", "temperature_max": "60", "gradient_rms": "120"},
    ]

    assert select_knee_point(points) == "b"


def test_plan_compare_bundles_pairs_key_methods_within_scenario() -> None:
    representatives = [
        {"scenario_id": "s5", "method_id": "nsga2_raw", "run_root": "raw"},
        {"scenario_id": "s5", "method_id": "nsga2_union", "run_root": "union"},
        {"scenario_id": "s5", "method_id": "nsga2_llm_gpt_5_4", "run_root": "llm"},
    ]

    plans = plan_compare_bundles(representatives)

    assert plans == [
        {"scenario_id": "s5", "baseline_run": "raw", "candidate_run": "union", "compare_id": "s5__nsga2_raw__vs__nsga2_union"},
        {"scenario_id": "s5", "baseline_run": "union", "candidate_run": "llm", "compare_id": "s5__nsga2_union__vs__nsga2_llm_gpt_5_4"},
    ]
