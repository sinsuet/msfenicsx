from pathlib import Path

import pytest
import yaml

import optimizers.run_suite as run_suite_module
from optimizers.io import save_optimization_spec
from optimizers.models import OptimizationSpec
from optimizers.operator_pool.operators import approved_union_operator_ids_for_backbone
from optimizers.run_suite import run_benchmark_suite


def _write_small_raw_spec(tmp_path: Path) -> Path:
    spec = OptimizationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {
                "spec_id": "s1-typical-run-suite-policy-test",
                "description": "Regression spec for s1_typical single benchmark seed policy.",
            },
            "benchmark_source": {
                "template_path": "scenarios/templates/s1_typical.yaml",
                "seed": 11,
            },
            "design_variables": [
                {
                    "variable_id": "c01_x",
                    "path": "components[0].pose.x",
                    "lower_bound": 0.1,
                    "upper_bound": 0.9,
                },
                {
                    "variable_id": "c01_y",
                    "path": "components[0].pose.y",
                    "lower_bound": 0.1,
                    "upper_bound": 0.68,
                },
            ],
            "algorithm": {
                "family": "genetic",
                "backbone": "nsga2",
                "mode": "raw",
                "population_size": 4,
                "num_generations": 1,
                "seed": 7,
            },
            "evaluation_protocol": {
                "evaluation_spec_path": "scenarios/evaluation/s1_typical_eval.yaml",
                "legality_policy_id": "minimal_canonicalization",
            },
        }
    )
    spec_path = tmp_path / "nsga2_raw.yaml"
    save_optimization_spec(spec.to_dict(), spec_path)
    return spec_path


def _write_small_env_backed_llm_spec(tmp_path: Path) -> Path:
    spec = OptimizationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {
                "spec_id": "s1-typical-run-suite-llm-env-test",
                "description": "Regression spec for llm suite env overlay.",
            },
            "benchmark_source": {
                "template_path": "scenarios/templates/s1_typical.yaml",
                "seed": 11,
            },
            "design_variables": [
                {
                    "variable_id": "c01_x",
                    "path": "components[0].pose.x",
                    "lower_bound": 0.1,
                    "upper_bound": 0.9,
                },
                {
                    "variable_id": "c01_y",
                    "path": "components[0].pose.y",
                    "lower_bound": 0.1,
                    "upper_bound": 0.68,
                },
            ],
            "algorithm": {
                "family": "genetic",
                "backbone": "nsga2",
                "mode": "union",
                "population_size": 4,
                "num_generations": 1,
                "seed": 7,
            },
            "evaluation_protocol": {
                "evaluation_spec_path": "scenarios/evaluation/s1_typical_eval.yaml",
                "legality_policy_id": "projection_plus_local_restore",
            },
            "operator_control": {
                "controller": "llm",
                "registry_profile": "primitive_clean",
                "operator_pool": list(approved_union_operator_ids_for_backbone("genetic", "nsga2")),
                "controller_parameters": {
                    "provider": "openai-compatible",
                    "capability_profile": "chat_compatible_json",
                    "performance_profile": "balanced",
                    "model_env_var": "LLM_MODEL",
                    "api_key_env_var": "LLM_API_KEY",
                    "base_url_env_var": "LLM_BASE_URL",
                    "max_output_tokens": 256,
                },
            },
        }
    )
    spec_path = tmp_path / "nsga2_llm_env.yaml"
    save_optimization_spec(spec.to_dict(), spec_path)
    return spec_path


def test_run_benchmark_suite_rejects_multiple_benchmark_seeds_for_s1_typical(tmp_path: Path) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)

    with pytest.raises(ValueError, match="s1_typical.*single benchmark_seed"):
        run_benchmark_suite(
            optimization_spec_paths=[raw_spec_path],
            benchmark_seeds=[11, 17],
            scenario_runs_root=tmp_path / "scenario_runs",
            modes=["raw"],
        )


def test_run_benchmark_suite_single_mode_does_not_write_suite_comparison_outputs(tmp_path: Path, monkeypatch) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)

    monkeypatch.setattr(
        run_suite_module,
        "run_raw_optimization",
        lambda *args, **kwargs: type(
            "FakeRun",
            (),
            {
                "result": type(
                    "FakeResult",
                    (),
                    {
                        "run_meta": {
                            "run_id": "fixture-run",
                            "optimization_spec_id": "fixture-spec",
                            "evaluation_spec_id": "fixture-eval",
                        },
                        "history": [],
                        "pareto_front": [],
                    },
                )(),
                "representative_artifacts": {},
                "generation_summary_rows": [],
            },
        )(),
    )
    monkeypatch.setattr(run_suite_module, "write_optimization_artifacts", lambda *args, **kwargs: Path(args[0]))
    monkeypatch.setattr(run_suite_module, "write_run_manifest", lambda *args, **kwargs: Path(args[0]))

    render_calls: list[Path] = []

    def _fake_render_assets(target: Path, *, hires: bool = False) -> list[Path]:
        render_calls.append(Path(target))
        return [Path(target)]

    import optimizers.render_assets as render_assets_module

    monkeypatch.setattr(render_assets_module, "render_assets", _fake_render_assets)

    run_root = run_benchmark_suite(
        optimization_spec_paths=[raw_spec_path],
        benchmark_seeds=[11],
        scenario_runs_root=tmp_path / "scenario_runs",
        modes=["raw"],
    )

    assert render_calls == [run_root / "raw"]
    assert not (run_root / "comparison").exists()
    assert not (run_root / "comparisons").exists()


def test_run_benchmark_suite_multi_mode_builds_suite_comparisons(tmp_path: Path, monkeypatch) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)
    union_spec_path = tmp_path / "nsga2_union.yaml"
    union_payload = yaml.safe_load(Path("scenarios/optimization/s1_typical_raw.yaml").read_text(encoding="utf-8"))
    union_payload["spec_meta"] = {
        "spec_id": "s1-typical-run-suite-union-test",
        "description": "Regression spec for suite compare generation.",
    }
    union_payload["algorithm"]["population_size"] = 4
    union_payload["algorithm"]["num_generations"] = 1
    union_payload["algorithm"]["mode"] = "union"
    union_payload["algorithm"]["profile_path"] = "scenarios/optimization/profiles/s1_typical_union.yaml"
    union_payload["operator_control"] = {
        "controller": "random_uniform",
        "registry_profile": "primitive_clean",
        "operator_pool": list(approved_union_operator_ids_for_backbone("genetic", "nsga2")),
    }
    union_spec_path.write_text(yaml.safe_dump(union_payload, sort_keys=False), encoding="utf-8")

    monkeypatch.setattr(
        run_suite_module,
        "run_raw_optimization",
        lambda *args, **kwargs: type(
            "FakeRun",
            (),
            {
                "result": type(
                    "FakeResult",
                    (),
                    {
                        "run_meta": {
                            "run_id": "fixture-run",
                            "optimization_spec_id": "fixture-spec",
                            "evaluation_spec_id": "fixture-eval",
                        },
                        "history": [],
                        "pareto_front": [],
                    },
                )(),
                "representative_artifacts": {},
                "generation_summary_rows": [],
            },
        )(),
    )
    monkeypatch.setattr(run_suite_module, "run_union_optimization", run_suite_module.run_raw_optimization)
    monkeypatch.setattr(run_suite_module, "write_optimization_artifacts", lambda *args, **kwargs: Path(args[0]))
    monkeypatch.setattr(run_suite_module, "write_run_manifest", lambda *args, **kwargs: Path(args[0]))

    render_calls: list[Path] = []
    comparison_calls: list[Path] = []

    def _fake_render_assets(target: Path, *, hires: bool = False) -> list[Path]:
        render_calls.append(Path(target))
        return [Path(target)]

    def _fake_build_suite_comparisons(target: Path, *, hires: bool = False) -> dict:
        comparison_calls.append(Path(target))
        (Path(target) / "comparisons").mkdir(parents=True, exist_ok=True)
        return {"comparison_kind": "single_seed"}

    import optimizers.render_assets as render_assets_module

    monkeypatch.setattr(render_assets_module, "render_assets", _fake_render_assets)
    monkeypatch.setattr(run_suite_module, "build_suite_comparisons", _fake_build_suite_comparisons, raising=False)

    run_root = run_benchmark_suite(
        optimization_spec_paths=[raw_spec_path, union_spec_path],
        benchmark_seeds=[11],
        scenario_runs_root=tmp_path / "scenario_runs",
        modes=["raw", "union"],
    )

    assert render_calls == [run_root / "raw", run_root / "union"]
    assert comparison_calls == [run_root]
    assert not (run_root / "comparison").exists()


def test_run_benchmark_suite_llm_mode_uses_default_profile_overlay_when_runtime_env_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    llm_spec_path = _write_small_env_backed_llm_spec(tmp_path)

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    import optimizers.cli as cli_module
    import optimizers.render_assets as render_assets_module

    monkeypatch.setattr(
        cli_module,
        "load_provider_profile_overlay",
        lambda profile, **kwargs: {
            "LLM_API_KEY": "suite-key",
            "LLM_BASE_URL": "https://suite.example/v1",
            "LLM_MODEL": "qwen3.6-plus",
        },
        raising=False,
    )
    monkeypatch.setattr(run_suite_module, "write_optimization_artifacts", lambda *args, **kwargs: Path(args[0]))
    monkeypatch.setattr(run_suite_module, "write_run_manifest", lambda *args, **kwargs: Path(args[0]))
    monkeypatch.setattr(render_assets_module, "render_assets", lambda *args, **kwargs: [])
    captured: dict[str, str] = {}

    def _fake_run_union_optimization(*args, **kwargs):
        del args, kwargs
        import os

        captured["LLM_API_KEY"] = os.environ["LLM_API_KEY"]
        captured["LLM_BASE_URL"] = os.environ["LLM_BASE_URL"]
        captured["LLM_MODEL"] = os.environ["LLM_MODEL"]
        return type(
            "FakeRun",
            (),
            {
                "result": type(
                    "FakeResult",
                    (),
                    {
                        "run_meta": {
                            "run_id": "fixture-run",
                            "optimization_spec_id": "fixture-spec",
                            "evaluation_spec_id": "fixture-eval",
                        },
                        "history": [],
                        "pareto_front": [],
                    },
                )(),
                "representative_artifacts": {},
                "generation_summary_rows": [],
            },
        )()

    monkeypatch.setattr(run_suite_module, "run_union_optimization", _fake_run_union_optimization)

    run_benchmark_suite(
        optimization_spec_paths=[llm_spec_path],
        benchmark_seeds=[11],
        scenario_runs_root=tmp_path / "scenario_runs",
        modes=["llm"],
    )

    assert captured == {
        "LLM_API_KEY": "suite-key",
        "LLM_BASE_URL": "https://suite.example/v1",
        "LLM_MODEL": "qwen3.6-plus",
    }
