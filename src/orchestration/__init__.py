from .history_report import (
    collect_history_collection_summary,
    collect_history_summary,
    write_history_collection_summary,
    write_history_summary,
)
from .run_manager import RunManager

__all__ = [
    "RunManager",
    "rollback_to",
    "run_optimization_loop",
    "collect_history_collection_summary",
    "collect_history_summary",
    "write_history_collection_summary",
    "write_history_summary",
]


def __getattr__(name: str):
    if name == "rollback_to":
        from .rollback import rollback_to

        return rollback_to
    if name == "run_optimization_loop":
        from .optimize_loop import run_optimization_loop

        return run_optimization_loop
    raise AttributeError(name)
