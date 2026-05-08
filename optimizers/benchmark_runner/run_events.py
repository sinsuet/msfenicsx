"""Streaming run event JSONL helpers."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


class RunEventWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._handle: TextIO | None = None
        self._started = time.monotonic()

    def __enter__(self) -> "RunEventWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def write(
        self,
        event: str,
        *,
        scenario_id: str,
        method_id: str,
        mode: str,
        llm_profile: str | None,
        seed: int,
        message: str = "",
        metrics: dict[str, Any] | None = None,
        generation: int | None = None,
    ) -> None:
        if self._handle is None:
            raise RuntimeError("RunEventWriter must be used as a context manager.")
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
            "event": str(event),
            "scenario_id": str(scenario_id),
            "method_id": str(method_id),
            "mode": str(mode),
            "llm_profile": llm_profile,
            "seed": int(seed),
            "elapsed_seconds": float(time.monotonic() - self._started),
            "message": str(message),
            "metrics": dict(metrics or {}),
        }
        if generation is not None:
            payload["generation"] = int(generation)
        self._handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
        self._handle.flush()


def append_summary_event(
    path: str | Path,
    *,
    event: str,
    scenario_id: str,
    method_id: str,
    mode: str,
    llm_profile: str | None,
    seed: int,
    summary: dict[str, Any],
) -> None:
    with RunEventWriter(path) as writer:
        writer.write(
            event,
            scenario_id=scenario_id,
            method_id=method_id,
            mode=mode,
            llm_profile=llm_profile,
            seed=seed,
            message=event,
            metrics=dict(summary),
        )
