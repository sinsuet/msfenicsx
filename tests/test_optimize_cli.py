from pathlib import Path
import importlib.util
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_example_module():
    example_path = ROOT / "examples" / "03_optimize_multicomponent_case.py"
    spec = importlib.util.spec_from_file_location("optimize_example", example_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_args_supports_real_llm_flags():
    module = _load_example_module()

    args = module.parse_args(
        [
            "--real-llm",
            "--max-iters",
            "2",
            "--enable-thinking",
            "--continue-when-feasible",
            "--max-invalid-proposals",
            "10",
            "--model",
            "qwen3.5-plus",
        ]
    )

    assert args.real_llm is True
    assert args.max_iters == 2
    assert args.enable_thinking is True
    assert args.continue_when_feasible is True
    assert args.max_invalid_proposals == 10
    assert args.model == "qwen3.5-plus"


def test_run_example_passes_real_llm_options(monkeypatch, tmp_path):
    module = _load_example_module()
    captured = {}

    def fake_run_optimization_loop(**kwargs):
        captured.update(kwargs)
        return {"iterations": 1, "status": "stub", "last_run_id": "run_0001", "runs_root": str(tmp_path)}

    monkeypatch.setattr(module, "run_optimization_loop", fake_run_optimization_loop)

    module.run_example(
        runs_root=tmp_path,
        max_iters=1,
        dry_run_llm=False,
        enable_thinking=True,
        continue_when_feasible=True,
        max_invalid_proposals=10,
        model="qwen3.5-plus",
    )

    assert captured["dry_run_llm"] is False
    assert captured["enable_thinking"] is True
    assert captured["continue_when_feasible"] is True
    assert captured["max_invalid_proposals"] == 10
    assert captured["model"] == "qwen3.5-plus"
