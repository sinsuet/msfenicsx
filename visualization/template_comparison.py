"""Template-level comparison rendering across single-mode experiment containers."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def render_template_comparisons(template_root: str | Path) -> dict[str, str]:
    root = Path(template_root)
    latest_by_mode = _discover_latest_experiments(root)
    outputs: dict[str, str] = {}
    comparison_specs = {
        "raw-vs-union": ["nsga2_raw", "nsga2_union"],
        "union-vs-llm": ["nsga2_union", "nsga2_llm"],
        "raw-vs-union-vs-llm": ["nsga2_raw", "nsga2_union", "nsga2_llm"],
    }
    for comparison_name, mode_ids in comparison_specs.items():
        if not all(mode_id in latest_by_mode for mode_id in mode_ids):
            continue
        experiment_payloads = [
            {
                "mode_id": mode_id,
                "experiment_root": str(latest_by_mode[mode_id]),
                "manifest": _load_json(latest_by_mode[mode_id] / "manifest.json"),
                "aggregate_summary": _load_json(latest_by_mode[mode_id] / "summaries" / "aggregate_summary.json"),
            }
            for mode_id in mode_ids
        ]
        body = "<h1>Template Comparison</h1>" + "".join(
            f"<h2>{html.escape(str(item['mode_id']))}</h2>"
            f"<p>{html.escape(str(item['experiment_root']))}</p>"
            f"<pre>{html.escape(json.dumps(item['aggregate_summary'], indent=2))}</pre>"
            for item in experiment_payloads
        )
        output_path = root / "comparisons" / comparison_name / "overview.html"
        _write_dashboard(output_path, "Template Comparison", body)
        outputs[comparison_name] = str(output_path)
    return outputs


def _discover_latest_experiments(template_root: Path) -> dict[str, Path]:
    experiments_root = template_root / "experiments"
    if not experiments_root.exists():
        return {}
    grouped: dict[str, list[Path]] = {}
    for path in experiments_root.iterdir():
        if not path.is_dir():
            continue
        mode_id = path.name.split("__", 1)[0]
        grouped.setdefault(mode_id, []).append(path)
    return {
        mode_id: sorted(paths)[-1]
        for mode_id, paths in grouped.items()
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_dashboard(path: Path, title: str, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        "<!DOCTYPE html><html><head>"
        f"<meta charset='utf-8'><title>{html.escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;margin:32px;background:#f6f1e6;color:#1f2933}"
        "pre{background:#fffaf2;border:1px solid #d7cab0;padding:12px;overflow:auto}</style>"
        "</head><body>"
        f"{body}</body></html>"
    )
    path.write_text(payload, encoding="utf-8")
    return path
