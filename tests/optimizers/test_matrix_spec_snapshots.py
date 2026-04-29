from pathlib import Path

import yaml

from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.spec_snapshots import write_leaf_spec_snapshot


def test_write_leaf_spec_snapshot_overrides_seed_budget_and_profile(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    leaf = next(item for item in matrix.expand_leaves() if item.method_id == "nsga2_llm_gpt_5_4" and item.scenario_id == "s5_aggressive15")

    snapshot = write_leaf_spec_snapshot(leaf, tmp_path)
    payload = yaml.safe_load(snapshot.read_text(encoding="utf-8"))

    assert snapshot.name == "s5_aggressive15__nsga2_llm_gpt_5_4__r11.yaml"
    assert leaf.replicate_seed == 11
    assert payload["benchmark_source"]["seed"] == 11
    assert payload["algorithm"]["seed"] == 1011
    assert payload["algorithm"]["population_size"] == 32
    assert payload["algorithm"]["num_generations"] == 16
    assert payload["operator_control"]["controller"] == "llm"
    assert payload["operator_control"]["controller_parameters"]["provider_profile"] == "gpt_5_4"
    assert payload["spec_meta"]["spec_id"] == "s5_aggressive15_nsga2_llm_gpt_5_4_r11"


def test_write_leaf_spec_snapshot_keeps_raw_without_operator_control(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    leaf = next(item for item in matrix.expand_leaves() if item.method_id == "spea2_raw" and item.scenario_id == "s6_aggressive20")

    snapshot = write_leaf_spec_snapshot(leaf, tmp_path)
    payload = yaml.safe_load(snapshot.read_text(encoding="utf-8"))

    assert payload["algorithm"]["family"] == "genetic"
    assert payload["algorithm"]["backbone"] == "spea2"
    assert payload["algorithm"]["mode"] == "raw"
    assert payload["algorithm"]["seed"] == 1011
    assert "operator_control" not in payload
