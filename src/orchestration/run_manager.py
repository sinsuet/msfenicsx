from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from thermal_state import ThermalDesignState, save_state


class RunManager:
    def __init__(self, runs_root: str | Path):
        self.runs_root = Path(runs_root)
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.current_pointer_path = self.runs_root / "current_run.txt"

    def _existing_run_ids(self) -> list[int]:
        run_ids: list[int] = []
        for path in self.runs_root.glob("run_*"):
            if not path.is_dir():
                continue
            suffix = path.name.removeprefix("run_")
            if suffix.isdigit():
                run_ids.append(int(suffix))
        return sorted(run_ids)

    def next_run_name(self) -> str:
        existing = self._existing_run_ids()
        next_id = existing[-1] + 1 if existing else 1
        return f"run_{next_id:04d}"

    def create_run_dir(self) -> Path:
        run_dir = self.runs_root / self.next_run_name()
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "outputs").mkdir(exist_ok=True)
        self.set_current_run(run_dir.name)
        return run_dir

    def set_current_run(self, run_id: str) -> None:
        self.current_pointer_path.write_text(f"{run_id}\n", encoding="utf-8")

    def get_current_run(self) -> str | None:
        if not self.current_pointer_path.exists():
            return None
        return self.current_pointer_path.read_text(encoding="utf-8").strip() or None

    def save_state_snapshot(
        self,
        state: ThermalDesignState,
        run_dir: str | Path,
        *,
        filename: str = "state.yaml",
    ) -> Path:
        run_dir = Path(run_dir)
        path = run_dir / filename
        save_state(state, path)
        return path

    def write_json(self, run_dir: str | Path, filename: str, payload: dict[str, Any]) -> Path:
        run_dir = Path(run_dir)
        path = run_dir / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path
