from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from compiler.single_run import run_case_from_state, run_case_from_state_file
from thermal_state.load_save import load_state


def run_example(
    *,
    output_root: str | Path | None = None,
    nx: int | None = None,
    ny: int | None = None,
) -> dict[str, str]:
    if output_root is None:
        output_root = ROOT / "outputs" / "02_multicomponent_steady_heat"
    state_path = ROOT / "states" / "baseline_multicomponent.yaml"
    if nx is None and ny is None:
        return run_case_from_state_file(state_path, output_root=output_root)

    state = load_state(state_path)
    mesh = dict(state.mesh)
    if nx is not None:
        mesh["nx"] = nx
    if ny is not None:
        mesh["ny"] = ny
    state = replace(state, mesh=mesh)
    return run_case_from_state(state, output_root=output_root)


if __name__ == "__main__":
    run_example()
