import json
from pathlib import Path

from optimizers.benchmark_runner.run_events import RunEventWriter, append_summary_event


def test_run_event_writer_appends_jsonl_immediately(tmp_path: Path) -> None:
    path = tmp_path / "seed-11" / "traces" / "run_events.jsonl"

    with RunEventWriter(path) as writer:
        writer.write(
            "leaf_started",
            scenario_id="s5_aggressive15",
            method_id="nsga2_raw",
            mode="raw",
            llm_profile=None,
            seed=11,
            message="leaf started",
            metrics={"evaluations_total": 0},
        )
        assert path.exists()
        first_line = path.read_text(encoding="utf-8").strip()
        assert json.loads(first_line)["event"] == "leaf_started"

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["scenario_id"] == "s5_aggressive15"
    assert rows[0]["seed"] == 11
    assert rows[0]["metrics"] == {"evaluations_total": 0}


def test_append_summary_event_adds_terminal_payload(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "run_events.jsonl"
    append_summary_event(
        path,
        event="llm_runtime_summary",
        scenario_id="s5_aggressive15",
        method_id="llm:gpt",
        mode="llm",
        llm_profile="gpt",
        seed=11,
        summary={"llm_request_count": 3, "tokens_total": 42},
    )

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["event"] == "llm_runtime_summary"
    assert row["metrics"]["llm_request_count"] == 3
    assert row["metrics"]["tokens_total"] == 42
