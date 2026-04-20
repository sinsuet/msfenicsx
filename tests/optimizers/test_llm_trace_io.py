from __future__ import annotations

from pathlib import Path


def test_resolve_seed_trace_path_uses_traces_subdir_only(tmp_path: Path) -> None:
    from optimizers.traces.llm_trace_io import resolve_seed_trace_path

    seed_root = tmp_path / "seed-11"
    (seed_root / "traces").mkdir(parents=True, exist_ok=True)
    (seed_root / "llm_request_trace.jsonl").write_text("legacy-root-fallback\n", encoding="utf-8")

    assert resolve_seed_trace_path(seed_root, "llm_request_trace.jsonl") == (
        seed_root / "traces" / "llm_request_trace.jsonl"
    )


def test_resolve_seed_trace_path_does_not_descend_into_nested_seed_children(tmp_path: Path) -> None:
    from optimizers.traces.llm_trace_io import resolve_seed_trace_path

    seed_root = tmp_path / "seed-11"
    nested_root = seed_root / "opt-7" / "traces"
    nested_root.mkdir(parents=True, exist_ok=True)
    (nested_root / "controller_trace.jsonl").write_text("legacy-nested-fallback\n", encoding="utf-8")

    assert resolve_seed_trace_path(seed_root, "controller_trace.jsonl") == (
        seed_root / "traces" / "controller_trace.jsonl"
    )
