# Logging & Visualization Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the msfenicsx run output, trace logs, and visualization stack on matplotlib and content-addressed markdown prompts, fix the inverted colorbar, flatten the directory layout, and deliver publication-grade assets for raw/union/llm uniformly.

**Architecture:** Four new packages replace the hand-rolled SVG stack: `visualization/style/` (rcParams baseline), `visualization/figures/` (matplotlib figure modules), `optimizers/analytics/` (pure trace→artifact pipeline), plus content-addressed `prompts/<sha1>.md` for LLM bodies. Drivers emit only JSONL traces; the analytics layer recomputes all derived data. Two new CLI subcommands (`render-assets`, `compare-runs`) drive the downstream pipeline. Legacy `visualization/case_pages.py`, `figure_axes.py`, `figure_theme.py`, `static_assets.py` are deleted in a single migration cutover.

**Current contract note:** the final repository contract stores raster outputs directly in `figures/` and writes vector companions under sibling `pdf/` subdirectories such as `figures/pdf/` and `<compare-output>/figures/pdf/`, rather than mixing `.png` and `.pdf` files in the same directory.

**Tech Stack:** Python 3.11, matplotlib 3.x, numpy, pandas (for parquet), PyYAML, pytest. XeLaTeX via texlive-full on WSL2 Ubuntu 24.04 for downstream paper assembly (not required to run tests). Tsinghua apt mirror for fast texlive install.

**Spec:** [docs/superpowers/specs/2026-04-16-logging-visualization-refactor-design.md](../specs/2026-04-16-logging-visualization-refactor-design.md)

---

## 2026-04-20 Paper-Facing Contract Amendment

These bullets override any stale examples later in this plan:

- `evaluation_events.jsonl` rows must carry `solver_skipped` so downstream analytics can derive true PDE-attempt counts without hiding cheap rejects.
- Any figure axis labeled `PDE evaluations` must use the derived solver-attempt count, not raw optimizer `evaluation_index`.
- `layout_evolution` is a best-so-far spatial-milestone replay with preserved `step_<NNN>.png` frames, not a per-generation representative slideshow.

## Phase 0: Environment Prep (one-time, manual)

### Task 0: texlive-full via Tsinghua mirror

**Files:**
- Modify: `/etc/apt/sources.list.d/ubuntu.sources` (system-level, outside repo)

This is a one-time host setup, not a code task. Execute manually before running any matplotlib-driven figure rendering that needs LaTeX (optional — matplotlib works without LaTeX; only needed for paper phase).

- [ ] **Step 1: Backup apt sources**

```bash
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
```

- [ ] **Step 2: Switch to Tsinghua mirror**

```bash
sudo sed -i \
  -e 's|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
  -e 's|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
  /etc/apt/sources.list.d/ubuntu.sources
sudo apt update
```

- [ ] **Step 3: Install texlive-full**

```bash
sudo apt install -y texlive-full
```

Expected: ~6GB download, ~3-6 min on Tsinghua mirror.

- [ ] **Step 4: Verify xelatex + ctex**

```bash
xelatex --version
kpsewhich ctex.sty
fc-list | grep -i "noto serif cjk"
```

Expected: engine version line, absolute path to `ctex.sty`, at least one `Noto Serif CJK SC` entry.

- [ ] **Step 5: Refresh matplotlib font cache**

```bash
conda run -n msfenicsx python -c "import matplotlib.font_manager as fm; fm._load_fontmanager(try_read_cache=False)"
```

Expected: no output (silent success).

No commit — this is host setup, nothing to add to git.

---

## Phase 1: Style Baseline

### Task 1: Create `visualization/style/baseline.py`

**Files:**
- Create: `visualization/style/__init__.py`
- Create: `visualization/style/baseline.py`
- Create: `tests/visualization/test_style_baseline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/visualization/test_style_baseline.py
"""Verify the scientific rcParams baseline."""

from __future__ import annotations

import matplotlib


def test_apply_baseline_sets_expected_rcparams() -> None:
    import matplotlib.pyplot as plt
    from visualization.style.baseline import apply_baseline

    # Snapshot to restore afterwards
    original = matplotlib.rcParams.copy()
    try:
        apply_baseline()
        assert matplotlib.rcParams["font.family"][0] == "DejaVu Serif"
        assert matplotlib.rcParams["mathtext.fontset"] == "stix"
        assert float(matplotlib.rcParams["font.size"]) == 9.0
        assert float(matplotlib.rcParams["axes.linewidth"]) == 0.6
        assert matplotlib.rcParams["xtick.direction"] == "in"
        assert matplotlib.rcParams["ytick.direction"] == "in"
        assert matplotlib.rcParams["legend.frameon"] is False
        assert matplotlib.rcParams["figure.constrained_layout.use"] is True
    finally:
        matplotlib.rcParams.update(original)
        plt.close("all")


def test_palette_categorical_has_eight_okabe_ito_hex_values() -> None:
    from visualization.style.baseline import PALETTE_CATEGORICAL

    assert len(PALETTE_CATEGORICAL) == 8
    for entry in PALETTE_CATEGORICAL:
        assert entry.startswith("#") and len(entry) == 7


def test_dpi_constants() -> None:
    from visualization.style.baseline import DPI_DEFAULT, DPI_FIELD_HIRES, DPI_HIRES

    assert DPI_DEFAULT == 600
    assert DPI_HIRES == 1200
    assert DPI_FIELD_HIRES == 2400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/visualization/test_style_baseline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'visualization.style'`.

- [ ] **Step 3: Create the `__init__.py`**

```python
# visualization/style/__init__.py
"""Scientific visualization style baseline for matplotlib-based figures."""

from visualization.style.baseline import (
    BASE_FONT_SIZE,
    COLORMAP_GRADIENT,
    COLORMAP_TEMPERATURE,
    DPI_DEFAULT,
    DPI_FIELD_HIRES,
    DPI_HIRES,
    FONT_FAMILY,
    FONT_FAMILY_MATH,
    PALETTE_CATEGORICAL,
    apply_baseline,
)

__all__ = [
    "BASE_FONT_SIZE",
    "COLORMAP_GRADIENT",
    "COLORMAP_TEMPERATURE",
    "DPI_DEFAULT",
    "DPI_FIELD_HIRES",
    "DPI_HIRES",
    "FONT_FAMILY",
    "FONT_FAMILY_MATH",
    "PALETTE_CATEGORICAL",
    "apply_baseline",
]
```

- [ ] **Step 4: Create `baseline.py`**

```python
# visualization/style/baseline.py
"""Scientific rcParams baseline — IEEE/Elsevier double-column ready."""

from __future__ import annotations

import matplotlib

FONT_FAMILY: list[str] = ["DejaVu Serif", "Noto Serif CJK SC", "serif"]
FONT_FAMILY_MATH: str = "stix"
BASE_FONT_SIZE: int = 9

DPI_DEFAULT: int = 600
DPI_HIRES: int = 1200
DPI_FIELD_HIRES: int = 2400

COLORMAP_TEMPERATURE: str = "inferno"
COLORMAP_GRADIENT: str = "viridis"

# Okabe-Ito colorblind-safe palette.
PALETTE_CATEGORICAL: list[str] = [
    "#000000",
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]


def apply_baseline() -> None:
    """Apply the scientific baseline to matplotlib rcParams."""
    matplotlib.rcParams["font.family"] = FONT_FAMILY
    matplotlib.rcParams["font.serif"] = FONT_FAMILY
    matplotlib.rcParams["font.size"] = BASE_FONT_SIZE
    matplotlib.rcParams["mathtext.fontset"] = FONT_FAMILY_MATH
    matplotlib.rcParams["axes.linewidth"] = 0.6
    matplotlib.rcParams["axes.labelsize"] = BASE_FONT_SIZE
    matplotlib.rcParams["axes.titlesize"] = BASE_FONT_SIZE + 1
    matplotlib.rcParams["xtick.direction"] = "in"
    matplotlib.rcParams["ytick.direction"] = "in"
    matplotlib.rcParams["xtick.labelsize"] = BASE_FONT_SIZE - 1
    matplotlib.rcParams["ytick.labelsize"] = BASE_FONT_SIZE - 1
    matplotlib.rcParams["legend.frameon"] = False
    matplotlib.rcParams["legend.fontsize"] = BASE_FONT_SIZE - 1
    matplotlib.rcParams["figure.constrained_layout.use"] = True
    matplotlib.rcParams["savefig.bbox"] = "tight"
    matplotlib.rcParams["savefig.pad_inches"] = 0.02
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/visualization/test_style_baseline.py -v`
Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add visualization/style/__init__.py visualization/style/baseline.py tests/visualization/test_style_baseline.py
git commit -m "feat(viz): add matplotlib scientific style baseline

Central rcParams module with DejaVu Serif + Noto CJK fallback,
Okabe-Ito palette, inferno/viridis colormaps, and IEEE/Elsevier
double-column font size (9pt). Foundation for the figure factory."
```

---

## Phase 2: Correlation ID + Trace Schema Primitives

### Task 2: Correlation ID utility

**Files:**
- Create: `optimizers/traces/__init__.py`
- Create: `optimizers/traces/correlation.py`
- Create: `tests/optimizers/test_correlation_id.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_correlation_id.py
"""Correlation ID format and generation."""

from __future__ import annotations

import pytest


def test_format_decision_id_zero_padding() -> None:
    from optimizers.traces.correlation import format_decision_id

    assert format_decision_id(5, 42, 1) == "g005-e0042-d01"
    assert format_decision_id(0, 0, 0) == "g000-e0000-d00"
    assert format_decision_id(999, 9999, 99) == "g999-e9999-d99"


def test_format_decision_id_rejects_negative() -> None:
    from optimizers.traces.correlation import format_decision_id

    with pytest.raises(ValueError):
        format_decision_id(-1, 0, 0)


def test_parse_decision_id_roundtrip() -> None:
    from optimizers.traces.correlation import format_decision_id, parse_decision_id

    original = format_decision_id(12, 345, 7)
    parsed = parse_decision_id(original)
    assert parsed == (12, 345, 7)


def test_parse_decision_id_rejects_malformed() -> None:
    from optimizers.traces.correlation import parse_decision_id

    with pytest.raises(ValueError):
        parse_decision_id("g5-e42-d1")  # no padding
    with pytest.raises(ValueError):
        parse_decision_id("not-an-id")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_correlation_id.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimizers.traces'`.

- [ ] **Step 3: Create the module**

```python
# optimizers/traces/__init__.py
"""JSONL trace schema primitives shared across drivers."""

from optimizers.traces.correlation import format_decision_id, parse_decision_id

__all__ = ["format_decision_id", "parse_decision_id"]
```

```python
# optimizers/traces/correlation.py
"""Correlation IDs link controller decisions → LLM bodies → operator ops → evaluations."""

from __future__ import annotations

import re

_DECISION_ID_RE = re.compile(r"^g(\d{3})-e(\d{4})-d(\d{2})$")


def format_decision_id(generation: int, eval_index: int, decision_index: int) -> str:
    """Build a canonical decision id `g{gen:03d}-e{eval:04d}-d{dec:02d}`."""
    if generation < 0 or eval_index < 0 or decision_index < 0:
        raise ValueError(
            f"decision id components must be non-negative; got gen={generation}, "
            f"eval={eval_index}, dec={decision_index}"
        )
    return f"g{generation:03d}-e{eval_index:04d}-d{decision_index:02d}"


def parse_decision_id(value: str) -> tuple[int, int, int]:
    """Parse a decision id back into `(generation, eval_index, decision_index)`."""
    match = _DECISION_ID_RE.match(value)
    if match is None:
        raise ValueError(f"malformed decision id: {value!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_correlation_id.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/traces/__init__.py optimizers/traces/correlation.py tests/optimizers/test_correlation_id.py
git commit -m "feat(traces): add decision_id correlation primitive

Canonical g{gen:03d}-e{eval:04d}-d{dec:02d} format with format + parse
roundtrip. Foundation for linking controller traces, LLM request/response
traces, operator traces, and evaluation events."
```

### Task 3: JSONL writer helper

**Files:**
- Create: `optimizers/traces/jsonl_writer.py`
- Create: `tests/optimizers/test_jsonl_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_jsonl_writer.py
"""JSONL append writer used by all trace sinks."""

from __future__ import annotations

import json
from pathlib import Path


def test_append_jsonl_creates_file_and_appends(tmp_path: Path) -> None:
    from optimizers.traces.jsonl_writer import append_jsonl

    target = tmp_path / "trace.jsonl"
    append_jsonl(target, {"a": 1})
    append_jsonl(target, {"a": 2})

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"a": 2}


def test_append_jsonl_enforces_single_line_per_record(tmp_path: Path) -> None:
    from optimizers.traces.jsonl_writer import append_jsonl

    target = tmp_path / "trace.jsonl"
    append_jsonl(target, {"nested": {"x": 1}, "list": [1, 2, 3]})

    content = target.read_text(encoding="utf-8")
    # Exactly one newline at the end, no internal newlines in the record.
    assert content.count("\n") == 1
    assert "\n" not in content.rstrip("\n")


def test_write_jsonl_batch_truncates(tmp_path: Path) -> None:
    from optimizers.traces.jsonl_writer import write_jsonl_batch

    target = tmp_path / "trace.jsonl"
    write_jsonl_batch(target, [{"a": 1}])
    write_jsonl_batch(target, [{"a": 2}, {"a": 3}])

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 2}
    assert json.loads(lines[1]) == {"a": 3}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_jsonl_writer.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
# optimizers/traces/jsonl_writer.py
"""Streaming JSONL writers — append for live traces, batch for rewrites."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    """Append a single JSON record as one line (UTF-8, no BOM, LF newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(record), ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
        handle.write("\n")


def write_jsonl_batch(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    """Write (truncating) a JSONL file from an iterable of records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(dict(record), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
```

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_jsonl_writer.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/traces/jsonl_writer.py tests/optimizers/test_jsonl_writer.py
git commit -m "feat(traces): add JSONL append/batch writers

UTF-8 no-BOM, LF newline, one record per line, tight separators.
Used by all new-schema trace sinks."
```

### Task 4: Content-addressed prompt store

**Files:**
- Create: `optimizers/traces/prompt_store.py`
- Create: `tests/optimizers/test_prompt_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_prompt_store.py
"""Content-addressed prompt markdown store (sha1 of body)."""

from __future__ import annotations

from pathlib import Path


def test_store_prompt_deduplicates_identical_bodies(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    body = "# System\n\nYou are a helpful operator controller.\n"

    ref1 = store.store(kind="request", body=body, model="gpt-5.4", decision_id="g000-e0001-d00")
    ref2 = store.store(kind="request", body=body, model="gpt-5.4", decision_id="g000-e0002-d00")

    assert ref1 == ref2
    md_files = sorted((tmp_path / "prompts").glob("*.md"))
    assert len(md_files) == 1


def test_store_prompt_different_bodies_produce_different_refs(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    ref_a = store.store(kind="request", body="abc", model="gpt-5.4", decision_id="g000-e0000-d00")
    ref_b = store.store(kind="request", body="xyz", model="gpt-5.4", decision_id="g000-e0001-d00")

    assert ref_a != ref_b


def test_stored_markdown_has_yaml_frontmatter(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    ref = store.store(
        kind="response",
        body="OK.",
        model="gpt-5.4",
        decision_id="g005-e0042-d01",
    )
    content = (tmp_path / ref).read_text(encoding="utf-8")
    # YAML frontmatter between triple-dash markers.
    assert content.startswith("---\n")
    assert "\n---\n" in content[4:]
    assert "kind: response" in content
    assert "sha1:" in content
    assert "model: gpt-5.4" in content
    assert "g005-e0042-d01" in content


def test_store_prompt_extends_decision_ids_on_dedup(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    body = "shared body"
    store.store(kind="request", body=body, model="m", decision_id="g000-e0001-d00")
    store.store(kind="request", body=body, model="m", decision_id="g000-e0002-d00")

    md_files = list((tmp_path / "prompts").glob("*.md"))
    assert len(md_files) == 1
    content = md_files[0].read_text(encoding="utf-8")
    assert "g000-e0001-d00" in content
    assert "g000-e0002-d00" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_prompt_store.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
# optimizers/traces/prompt_store.py
"""Content-addressed markdown store: prompts/<sha1>.md with YAML frontmatter."""

from __future__ import annotations

import datetime as _dt
import hashlib
from pathlib import Path


class PromptStore:
    """Store prompt/response bodies as deduplicated markdown files."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def store(self, *, kind: str, body: str, model: str, decision_id: str) -> str:
        """Write body to `prompts/<sha1>.md`; return the relative ref path."""
        if kind not in {"request", "response"}:
            raise ValueError(f"kind must be 'request' or 'response'; got {kind!r}")
        digest = hashlib.sha1(body.encode("utf-8")).hexdigest()
        self._root.mkdir(parents=True, exist_ok=True)
        target = self._root / f"{digest}.md"
        ref = f"prompts/{digest}.md"

        if target.exists():
            self._extend_decision_ids(target, decision_id)
            return ref

        now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        frontmatter = (
            "---\n"
            f"kind: {kind}\n"
            f"sha1: {digest}\n"
            f"model: {model}\n"
            f"decision_ids: [{decision_id}]\n"
            f"first_seen_at: {now}\n"
            "---\n\n"
        )
        target.write_text(frontmatter + body, encoding="utf-8")
        return ref

    def _extend_decision_ids(self, target: Path, decision_id: str) -> None:
        content = target.read_text(encoding="utf-8")
        marker = "decision_ids: ["
        start = content.find(marker)
        if start == -1:
            return  # non-conforming file; leave alone
        open_bracket = start + len(marker) - 1
        close_bracket = content.find("]", open_bracket)
        if close_bracket == -1:
            return
        existing_raw = content[open_bracket + 1 : close_bracket]
        existing = [item.strip() for item in existing_raw.split(",") if item.strip()]
        if decision_id in existing:
            return
        existing.append(decision_id)
        replacement = f"decision_ids: [{', '.join(existing)}]"
        new_content = content[:start] + replacement + content[close_bracket + 1 :]
        target.write_text(new_content, encoding="utf-8")
```

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_prompt_store.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/traces/prompt_store.py tests/optimizers/test_prompt_store.py
git commit -m "feat(traces): add content-addressed prompt store

sha1-addressed markdown files with YAML frontmatter. Identical prompt
bodies dedupe to one file; decision_ids list extends on rehit. Replaces
inline multi-KB prompt strings in llm_request_trace.jsonl."
```

---

## Phase 3: Analytics Layer

### Task 5: JSONL loaders

**Files:**
- Create: `optimizers/analytics/__init__.py`
- Create: `optimizers/analytics/loaders.py`
- Create: `tests/optimizers/test_analytics_loaders.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_analytics_loaders.py
"""JSONL loaders stream trace rows into typed dicts."""

from __future__ import annotations

import json
from pathlib import Path


def _write_lines(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def test_iter_jsonl_yields_each_record(tmp_path: Path) -> None:
    from optimizers.analytics.loaders import iter_jsonl

    target = tmp_path / "t.jsonl"
    _write_lines(target, [{"a": 1}, {"a": 2}, {"a": 3}])

    rows = list(iter_jsonl(target))
    assert rows == [{"a": 1}, {"a": 2}, {"a": 3}]


def test_iter_jsonl_ignores_blank_lines(tmp_path: Path) -> None:
    from optimizers.analytics.loaders import iter_jsonl

    target = tmp_path / "t.jsonl"
    target.write_text('{"a":1}\n\n{"a":2}\n', encoding="utf-8")

    rows = list(iter_jsonl(target))
    assert rows == [{"a": 1}, {"a": 2}]


def test_iter_jsonl_missing_file_yields_empty(tmp_path: Path) -> None:
    from optimizers.analytics.loaders import iter_jsonl

    rows = list(iter_jsonl(tmp_path / "missing.jsonl"))
    assert rows == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_analytics_loaders.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
# optimizers/analytics/__init__.py
"""Pure trace → artifact analytics package."""
```

```python
# optimizers/analytics/loaders.py
"""Stream JSONL trace files into dict records."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield each JSONL record in `path`; yield nothing if file is absent."""
    path = Path(path)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)
```

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_analytics_loaders.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/analytics/__init__.py optimizers/analytics/loaders.py tests/optimizers/test_analytics_loaders.py
git commit -m "feat(analytics): add JSONL streaming loader"
```

### Task 6: Pareto + hypervolume computation

**Files:**
- Create: `optimizers/analytics/pareto.py`
- Create: `tests/optimizers/test_analytics_pareto.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_analytics_pareto.py
"""Pareto filtering and 2D hypervolume."""

from __future__ import annotations

import math


def test_pareto_minimization_filters_dominated_points() -> None:
    from optimizers.analytics.pareto import pareto_front_indices

    # Minimization in both objectives.
    objectives = [
        (1.0, 5.0),  # non-dominated
        (2.0, 4.0),  # non-dominated
        (3.0, 3.0),  # non-dominated
        (4.0, 6.0),  # dominated by (2,4)
        (5.0, 2.0),  # non-dominated
    ]
    idx = pareto_front_indices(objectives)
    assert idx == [0, 1, 2, 4]


def test_hypervolume_2d_against_reference_point() -> None:
    from optimizers.analytics.pareto import hypervolume_2d

    # Single point (3,3) with reference (5,5): HV = 2 × 2 = 4.
    hv = hypervolume_2d([(3.0, 3.0)], reference_point=(5.0, 5.0))
    assert math.isclose(hv, 4.0, rel_tol=1e-9)


def test_hypervolume_2d_multiple_points() -> None:
    from optimizers.analytics.pareto import hypervolume_2d

    # Points (1,4), (2,3), (4,1) vs ref (5,5).
    # Stepwise: (1,4)→(2,3)→(4,1) contributes
    #   (2-1)*(5-4) + (4-2)*(5-3) + (5-4)*(5-1) = 1 + 4 + 4 = 9
    hv = hypervolume_2d([(1.0, 4.0), (2.0, 3.0), (4.0, 1.0)], reference_point=(5.0, 5.0))
    assert math.isclose(hv, 9.0, rel_tol=1e-9)


def test_hypervolume_2d_ignores_dominated_points() -> None:
    from optimizers.analytics.pareto import hypervolume_2d

    points = [(1.0, 4.0), (2.0, 3.0), (4.0, 1.0), (3.0, 4.0)]  # (3,4) is dominated
    hv = hypervolume_2d(points, reference_point=(5.0, 5.0))
    assert math.isclose(hv, 9.0, rel_tol=1e-9)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_analytics_pareto.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Create `pareto.py`**

```python
# optimizers/analytics/pareto.py
"""Pareto filtering and exact 2D hypervolume (minimization)."""

from __future__ import annotations

from collections.abc import Sequence


def pareto_front_indices(objectives: Sequence[tuple[float, float]]) -> list[int]:
    """Return indices of non-dominated points under minimization."""
    result: list[int] = []
    for i, (a1, a2) in enumerate(objectives):
        dominated = False
        for j, (b1, b2) in enumerate(objectives):
            if i == j:
                continue
            if b1 <= a1 and b2 <= a2 and (b1 < a1 or b2 < a2):
                dominated = True
                break
        if not dominated:
            result.append(i)
    return result


def hypervolume_2d(
    points: Sequence[tuple[float, float]],
    *,
    reference_point: tuple[float, float],
) -> float:
    """Exact 2D hypervolume under minimization against `reference_point`."""
    idx = pareto_front_indices(list(points))
    front = sorted((points[i] for i in idx), key=lambda p: p[0])
    ref_x, ref_y = reference_point
    hv = 0.0
    prev_x = ref_x
    for x, y in reversed(front):
        # height from this point's y up to the reference y.
        height = ref_y - y
        width = prev_x - x
        if width > 0 and height > 0:
            hv += width * height
        prev_x = x
    return hv
```

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_analytics_pareto.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/analytics/pareto.py tests/optimizers/test_analytics_pareto.py
git commit -m "feat(analytics): add Pareto filter + exact 2D hypervolume"
```

### Task 7: Per-generation rollups

**Files:**
- Create: `optimizers/analytics/rollups.py`
- Create: `tests/optimizers/test_analytics_rollups.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_analytics_rollups.py
"""Roll up evaluation events into per-generation summaries."""

from __future__ import annotations


def test_rollup_per_generation_counts_and_objectives() -> None:
    from optimizers.analytics.rollups import rollup_per_generation

    events = [
        {
            "generation": 0,
            "status": "ok",
            "objectives": {"temperature_max": 320.0, "temperature_gradient_rms": 3.0},
        },
        {
            "generation": 0,
            "status": "ok",
            "objectives": {"temperature_max": 310.0, "temperature_gradient_rms": 2.5},
        },
        {
            "generation": 0,
            "status": "infeasible_cheap",
            "objectives": None,
        },
        {
            "generation": 1,
            "status": "ok",
            "objectives": {"temperature_max": 305.0, "temperature_gradient_rms": 2.2},
        },
    ]
    rows = rollup_per_generation(events, reference_point=(330.0, 5.0))
    assert [r["generation"] for r in rows] == [0, 1]
    assert rows[0]["num_feasible"] == 2
    assert rows[0]["num_infeasible"] == 1
    assert rows[0]["population_size"] == 3
    assert rows[0]["hypervolume"] > 0.0
    assert rows[1]["hypervolume"] >= rows[0]["hypervolume"]  # monotone on this data


def test_rollup_per_generation_empty_input() -> None:
    from optimizers.analytics.rollups import rollup_per_generation

    assert rollup_per_generation([], reference_point=(1.0, 1.0)) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_analytics_rollups.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `rollups.py`**

```python
# optimizers/analytics/rollups.py
"""Per-generation rollups over evaluation events."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from optimizers.analytics.pareto import hypervolume_2d


def rollup_per_generation(
    events: Iterable[dict[str, Any]],
    *,
    reference_point: tuple[float, float],
) -> list[dict[str, Any]]:
    """Return one summary dict per generation, sorted by generation index."""
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        buckets[int(event["generation"])].append(event)

    seen_points: list[tuple[float, float]] = []
    summaries: list[dict[str, Any]] = []
    for generation in sorted(buckets):
        rows = buckets[generation]
        feasible = [r for r in rows if r.get("status") == "ok" and r.get("objectives")]
        for row in feasible:
            obj = row["objectives"]
            seen_points.append(
                (float(obj["temperature_max"]), float(obj["temperature_gradient_rms"]))
            )
        hv = hypervolume_2d(seen_points, reference_point=reference_point) if seen_points else 0.0
        front_points = [
            (float(r["objectives"]["temperature_max"]), float(r["objectives"]["temperature_gradient_rms"]))
            for r in feasible
        ]
        summaries.append(
            {
                "generation": generation,
                "population_size": len(rows),
                "num_feasible": len(feasible),
                "num_infeasible": len(rows) - len(feasible),
                "front_objectives": front_points,
                "hypervolume": hv,
            }
        )
    return summaries
```

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_analytics_rollups.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/analytics/rollups.py tests/optimizers/test_analytics_rollups.py
git commit -m "feat(analytics): add per-generation rollup with cumulative HV"
```

### Task 8: Operator × phase heatmap

**Files:**
- Create: `optimizers/analytics/heatmap.py`
- Create: `tests/optimizers/test_analytics_heatmap.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_analytics_heatmap.py
"""Operator × phase usage heatmap."""

from __future__ import annotations


def test_operator_phase_heatmap_counts() -> None:
    from optimizers.analytics.heatmap import operator_phase_heatmap

    operator_rows = [
        {"operator_name": "global_explore", "decision_id": "g000-e0001-d00"},
        {"operator_name": "local_refine", "decision_id": "g001-e0010-d00"},
        {"operator_name": "global_explore", "decision_id": "g001-e0011-d00"},
        {"operator_name": "slide_sink", "decision_id": None},  # raw/union
    ]
    controller_rows = [
        {"decision_id": "g000-e0001-d00", "phase": "prefeasible"},
        {"decision_id": "g001-e0010-d00", "phase": "post_feasible_recover"},
        {"decision_id": "g001-e0011-d00", "phase": "post_feasible_expand"},
    ]
    grid = operator_phase_heatmap(operator_rows, controller_rows)

    assert grid["global_explore"]["prefeasible"] == 1
    assert grid["global_explore"]["post_feasible_expand"] == 1
    assert grid["local_refine"]["post_feasible_recover"] == 1
    assert grid["slide_sink"]["n/a"] == 1


def test_operator_phase_heatmap_no_controller_rows_single_na_column() -> None:
    from optimizers.analytics.heatmap import operator_phase_heatmap

    operator_rows = [
        {"operator_name": "native_sbx_pm", "decision_id": None},
        {"operator_name": "native_sbx_pm", "decision_id": None},
    ]
    grid = operator_phase_heatmap(operator_rows, [])
    assert grid["native_sbx_pm"] == {"n/a": 2}
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with ImportError.

- [ ] **Step 3: Create `heatmap.py`**

```python
# optimizers/analytics/heatmap.py
"""Operator × controller-phase usage grid."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any


def operator_phase_heatmap(
    operator_rows: Iterable[dict[str, Any]],
    controller_rows: Iterable[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Build `{operator: {phase: count}}` indexed via decision_id."""
    phase_by_decision: dict[str, str] = {
        str(row["decision_id"]): str(row.get("phase", "n/a"))
        for row in controller_rows
        if row.get("decision_id")
    }
    grid: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for op_row in operator_rows:
        operator = str(op_row["operator_name"])
        decision_id = op_row.get("decision_id")
        phase = phase_by_decision.get(str(decision_id), "n/a") if decision_id else "n/a"
        grid[operator][phase] += 1
    return {op: dict(counts) for op, counts in grid.items()}
```

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_analytics_heatmap.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/analytics/heatmap.py tests/optimizers/test_analytics_heatmap.py
git commit -m "feat(analytics): add operator × phase usage heatmap"
```

### Task 9: Decision outcomes (llm-specific analytics)

**Files:**
- Create: `optimizers/analytics/decisions.py`
- Create: `tests/optimizers/test_analytics_decisions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_analytics_decisions.py
"""Per-decision outcome table: applied? HV gain? token cost?"""

from __future__ import annotations


def test_decision_outcomes_joins_controller_and_llm_rows() -> None:
    from optimizers.analytics.decisions import decision_outcomes

    controller_rows = [
        {"decision_id": "g000-e0001-d00", "phase": "prefeasible", "operator_selected": "g_exp"},
        {"decision_id": "g001-e0010-d00", "phase": "post_feasible_expand", "operator_selected": "l_ref"},
    ]
    llm_response_rows = [
        {"decision_id": "g000-e0001-d00", "tokens": {"total": 300}, "latency_ms": 850},
        {"decision_id": "g001-e0010-d00", "tokens": {"total": 500}, "latency_ms": 1200},
    ]
    operator_rows = [
        {
            "decision_id": "g000-e0001-d00",
            "parents": ["ind1"],
            "offspring": ["ind2"],
        },
    ]
    rows = decision_outcomes(controller_rows, llm_response_rows, operator_rows)
    assert len(rows) == 2
    by_id = {r["decision_id"]: r for r in rows}
    assert by_id["g000-e0001-d00"]["applied"] is True
    assert by_id["g001-e0010-d00"]["applied"] is False
    assert by_id["g000-e0001-d00"]["tokens_total"] == 300
    assert by_id["g001-e0010-d00"]["tokens_total"] == 500
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with ImportError.

- [ ] **Step 3: Create `decisions.py`**

```python
# optimizers/analytics/decisions.py
"""Per-controller-decision outcome analytics (llm runs only)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def decision_outcomes(
    controller_rows: Iterable[dict[str, Any]],
    llm_response_rows: Iterable[dict[str, Any]],
    operator_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join controller/llm/operator rows by decision_id into one row each."""
    llm_by_id = {str(r["decision_id"]): r for r in llm_response_rows}
    op_ids_applied = {
        str(r["decision_id"])
        for r in operator_rows
        if r.get("decision_id") and r.get("offspring")
    }

    out: list[dict[str, Any]] = []
    for controller_row in controller_rows:
        decision_id = str(controller_row["decision_id"])
        llm_row = llm_by_id.get(decision_id, {})
        tokens = (llm_row.get("tokens") or {}).get("total", 0)
        out.append(
            {
                "decision_id": decision_id,
                "phase": controller_row.get("phase"),
                "operator_selected": controller_row.get("operator_selected"),
                "applied": decision_id in op_ids_applied,
                "tokens_total": int(tokens),
                "latency_ms": float(llm_row.get("latency_ms", 0.0)),
            }
        )
    return out
```

- [ ] **Step 4: Run tests**

Expected: 1 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/analytics/decisions.py tests/optimizers/test_analytics_decisions.py
git commit -m "feat(analytics): add per-decision outcome join"
```

---

## Phase 4: Figure Factory (starts with the colorbar regression lock)

### Task 10: Colorbar orientation regression lock

**Files:**
- Create: `tests/visualization/test_heatfield_orientation.py`
- Create: `visualization/figures/__init__.py`
- Create: `visualization/figures/temperature_field.py`

This task establishes the regression lock BEFORE the implementation exists. Red-green-refactor on the single bug that motivated the entire refactor.

- [ ] **Step 1: Write the failing test**

```python
# tests/visualization/test_heatfield_orientation.py
"""Regression lock for the inverted-colorbar bug at old figure_axes.py:44.

After rendering, the highest-valued input pixel must map to the top of the
rendered colorbar (not the bottom, as the legacy hand-rolled SVG did).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def test_temperature_field_colorbar_hot_at_top(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from visualization.figures.temperature_field import render_temperature_field

    # Grid with a single obvious hotspot at (row=1, col=1), cool elsewhere.
    grid = np.array(
        [
            [290.0, 290.0, 290.0],
            [290.0, 360.0, 290.0],
            [290.0, 290.0, 290.0],
        ]
    )
    xs = np.array([0.0, 0.5, 1.0])
    ys = np.array([0.0, 0.5, 1.0])

    output = tmp_path / "temperature.png"
    fig, im, cbar = render_temperature_field(
        grid=grid,
        xs=xs,
        ys=ys,
        output=output,
        return_artifacts=True,
    )

    # Colorbar ticks must be oriented low-at-bottom, high-at-top.
    ymin, ymax = cbar.ax.get_ylim()
    assert ymax > ymin, "colorbar y-axis must increase upward"

    # The max value displayed must correspond to the actual max input value.
    assert im.norm.vmax >= 360.0 - 1e-9
    assert im.norm.vmin <= 290.0 + 1e-9

    assert output.exists() and output.stat().st_size > 0
    plt.close(fig)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/visualization/test_heatfield_orientation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'visualization.figures'`.

- [ ] **Step 3: Create `figures/__init__.py` + `temperature_field.py`**

```python
# visualization/figures/__init__.py
"""Matplotlib figure factory — one module per figure kind."""
```

```python
# visualization/figures/temperature_field.py
"""Temperature field heatmap with CORRECTLY oriented colorbar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from visualization.style.baseline import (
    COLORMAP_TEMPERATURE,
    DPI_DEFAULT,
    DPI_FIELD_HIRES,
    apply_baseline,
)


def render_temperature_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    hires: bool = False,
    return_artifacts: bool = False,
) -> tuple[Any, Any, Any] | None:
    """Render a temperature field with inferno colormap and a native colorbar.

    Relies on matplotlib's `fig.colorbar(im, ax=ax)` for orientation — the
    hand-built legacy renderer inverted it.
    """
    apply_baseline()
    shading = "gouraud" if hires else "auto"

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_TEMPERATURE, shading=shading)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Temperature (K)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)

    # Also emit a PDF sibling if output is a png.
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))

    if return_artifacts:
        return fig, im, cbar
    plt.close(fig)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n msfenicsx pytest tests/visualization/test_heatfield_orientation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/visualization/test_heatfield_orientation.py visualization/figures/__init__.py visualization/figures/temperature_field.py
git commit -m "feat(viz): temperature field figure with correct colorbar orientation

Fixes the inverted-gradient bug that originated in the hand-rolled
render_colorbar_panel at visualization/figure_axes.py:44. Uses
fig.colorbar() which matplotlib orients correctly by default.
Regression test locks hot-at-top invariant."
```

### Task 11: Gradient field figure

**Files:**
- Create: `visualization/figures/gradient_field.py`

Structurally identical to temperature_field but with the viridis colormap and a different label; the same colorbar invariant applies so no separate regression test is needed beyond Task 10.

- [ ] **Step 1: Create the module**

```python
# visualization/figures/gradient_field.py
"""Gradient-magnitude field with viridis colormap."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from visualization.style.baseline import (
    COLORMAP_GRADIENT,
    DPI_DEFAULT,
    DPI_FIELD_HIRES,
    apply_baseline,
)


def render_gradient_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    hires: bool = False,
) -> None:
    """Render the gradient magnitude field."""
    apply_baseline()
    shading = "gouraud" if hires else "auto"

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_GRADIENT, shading=shading)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label(r"$|\nabla T|$ (K/m)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)
```

- [ ] **Step 2: Commit**

```bash
git add visualization/figures/gradient_field.py
git commit -m "feat(viz): gradient field figure with viridis colormap"
```

### Task 12: Pareto front figure

**Files:**
- Create: `visualization/figures/pareto.py`
- Create: `tests/visualization/test_pareto_figure.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/visualization/test_pareto_figure.py
"""Pareto figure renders PDF + PNG at expected DPI."""

from __future__ import annotations

from pathlib import Path


def test_render_pareto_front_writes_pdf_and_png(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from visualization.figures.pareto import render_pareto_front

    output = tmp_path / "pareto_front.png"
    render_pareto_front(
        fronts={
            "llm": [(320.0, 3.0), (315.0, 3.5), (310.0, 4.1)],
        },
        output=output,
    )
    assert output.exists()
    assert (tmp_path / "pareto_front.pdf").exists()


def test_render_pareto_front_overlay_multiple_modes(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from visualization.figures.pareto import render_pareto_front

    output = tmp_path / "pareto_front.png"
    render_pareto_front(
        fronts={
            "raw": [(325.0, 3.2)],
            "union": [(322.0, 3.1)],
            "llm": [(320.0, 3.0)],
        },
        output=output,
    )
    assert output.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with ImportError.

- [ ] **Step 3: Create the module**

```python
# visualization/figures/pareto.py
"""Pareto-front plot for single-mode and overlay variants."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt

from visualization.style.baseline import (
    DPI_DEFAULT,
    DPI_HIRES,
    PALETTE_CATEGORICAL,
    apply_baseline,
)


def render_pareto_front(
    *,
    fronts: Mapping[str, Sequence[tuple[float, float]]],
    output: Path,
    hires: bool = False,
) -> None:
    """Render one Pareto curve per mode overlaid on a single axis."""
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.5, 2.6))

    for idx, (mode, points) in enumerate(fronts.items()):
        if not points:
            continue
        ordered = sorted(points, key=lambda p: p[0])
        xs = [p[0] for p in ordered]
        ys = [p[1] for p in ordered]
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        ax.plot(xs, ys, color=color, marker="o", markersize=3, linewidth=1.0, label=mode)

    ax.set_xlabel(r"$T_{\max}$ (K)")
    ax.set_ylabel(r"$\nabla T_{\mathrm{rms}}$ (K/m)")
    if len(fronts) > 1:
        ax.legend()

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)
```

- [ ] **Step 4: Run tests**

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add visualization/figures/pareto.py tests/visualization/test_pareto_figure.py
git commit -m "feat(viz): Pareto-front figure with multi-mode overlay"
```

### Task 13: Hypervolume progress + optional IQR band

**Files:**
- Create: `visualization/figures/hypervolume.py`

- [ ] **Step 1: Create the module**

```python
# visualization/figures/hypervolume.py
"""Hypervolume progress curve; single-run and multi-seed IQR-band variants."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from visualization.style.baseline import (
    DPI_DEFAULT,
    DPI_HIRES,
    PALETTE_CATEGORICAL,
    apply_baseline,
)


def render_hypervolume_progress(
    *,
    series: dict[str, Sequence[tuple[int, float]]],
    output: Path,
    hires: bool = False,
) -> None:
    """Render `{mode: [(generation, hv), ...]}` as a line plot."""
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.5, 2.6))

    for idx, (mode, points) in enumerate(series.items()):
        if not points:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        ax.plot(xs, ys, color=color, linewidth=1.2, label=mode)

    ax.set_xlabel("Generation")
    ax.set_ylabel("Hypervolume")
    if len(series) > 1:
        ax.legend()

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)


def render_hypervolume_iqr_band(
    *,
    generations: Sequence[int],
    median: Sequence[float],
    p25: Sequence[float],
    p75: Sequence[float],
    output: Path,
    hires: bool = False,
    color: str | None = None,
) -> None:
    """Render a single-mode median line with 25-75 percentile band."""
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    stroke = color or PALETTE_CATEGORICAL[1]
    xs = np.asarray(generations)
    ax.fill_between(xs, p25, p75, color=stroke, alpha=0.25, linewidth=0)
    ax.plot(xs, median, color=stroke, linewidth=1.4)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Hypervolume (median, 25-75 IQR)")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)
```

- [ ] **Step 2: Commit**

```bash
git add visualization/figures/hypervolume.py
git commit -m "feat(viz): hypervolume progress + IQR-band variants"
```

### Task 14: Operator heatmap figure

**Files:**
- Create: `visualization/figures/operator_heatmap.py`

- [ ] **Step 1: Create the module**

```python
# visualization/figures/operator_heatmap.py
"""Operator × phase usage heatmap."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from visualization.style.baseline import DPI_DEFAULT, DPI_HIRES, apply_baseline


def render_operator_heatmap(
    *,
    grid: dict[str, dict[str, int]],
    output: Path,
    hires: bool = False,
) -> None:
    """Render `{operator: {phase: count}}` as a heatmap."""
    apply_baseline()
    operators = sorted(grid.keys())
    phases: list[str] = []
    for op in operators:
        for phase in grid[op]:
            if phase not in phases:
                phases.append(phase)
    phases.sort(key=lambda p: (p == "n/a", p))

    matrix = np.zeros((len(operators), len(phases)), dtype=float)
    for i, op in enumerate(operators):
        for j, phase in enumerate(phases):
            matrix[i, j] = grid[op].get(phase, 0)

    fig_w = max(3.5, 0.6 * len(phases) + 2.0)
    fig_h = max(2.6, 0.35 * len(operators) + 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(matrix, aspect="auto", cmap="magma")
    ax.set_xticks(range(len(phases)))
    ax.set_xticklabels(phases, rotation=30, ha="right")
    ax.set_yticks(range(len(operators)))
    ax.set_yticklabels(operators)
    for i in range(len(operators)):
        for j in range(len(phases)):
            count = int(matrix[i, j])
            if count:
                ax.text(j, i, str(count), ha="center", va="center", color="white", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)
```

- [ ] **Step 2: Commit**

```bash
git add visualization/figures/operator_heatmap.py
git commit -m "feat(viz): operator × phase heatmap figure"
```

### Task 15: Layout evolution animated GIF

**Files:**
- Create: `visualization/figures/layout_evolution.py`

- [ ] **Step 1: Create the module**

```python
# visualization/figures/layout_evolution.py
"""Animated GIF of component layouts across generations, with frame pngs preserved."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter
from matplotlib.patches import Rectangle

from visualization.style.baseline import DPI_DEFAULT, PALETTE_CATEGORICAL, apply_baseline


def render_layout_evolution(
    *,
    frames: Sequence[dict],
    output_gif: Path,
    frames_dir: Path,
    fps: float = 2.0,
) -> None:
    """Render an animated GIF plus `frames_dir/gen_<NNN>.png` for each frame.

    `frames[i]` is `{"generation": int, "components": [{"x": float, "y": float,
    "w": float, "h": float}, ...]}`.
    """
    apply_baseline()
    output_gif = Path(output_gif)
    frames_dir = Path(frames_dir)
    output_gif.parent.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    writer = PillowWriter(fps=fps)
    with writer.saving(fig, str(output_gif), dpi=DPI_DEFAULT):
        for frame in frames:
            ax.cla()
            ax.set_xlim(0.0, 1.0)
            ax.set_ylim(0.0, 1.0)
            ax.set_aspect("equal")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_title(f"gen {int(frame['generation'])}")
            for idx, comp in enumerate(frame["components"]):
                rect = Rectangle(
                    (comp["x"] - comp["w"] / 2, comp["y"] - comp["h"] / 2),
                    comp["w"],
                    comp["h"],
                    facecolor=PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)],
                    edgecolor="black",
                    linewidth=0.4,
                    alpha=0.8,
                )
                ax.add_patch(rect)
            writer.grab_frame()
            frame_path = frames_dir / f"gen_{int(frame['generation']):03d}.png"
            fig.savefig(frame_path, dpi=DPI_DEFAULT)
    plt.close(fig)
```

- [ ] **Step 2: Commit**

```bash
git add visualization/figures/layout_evolution.py
git commit -m "feat(viz): animated layout-evolution GIF with frame pngs preserved"
```

---

## Phase 5: New-Schema Trace Writers in Drivers

### Task 16: Add new-schema evaluation_events writer

**Files:**
- Modify: `optimizers/run_telemetry.py`
- Modify: `tests/optimizers/test_run_telemetry.py` (only if pre-existing tests need alignment)

The existing `build_evaluation_events` already produces JSONL rows but with the legacy schema. Replace it with the § 4.1 schema.

- [ ] **Step 1: Read the current function**

Read [optimizers/run_telemetry.py](optimizers/run_telemetry.py) to see the existing signature and internal fields.

- [ ] **Step 2: Write a new test for the new schema**

Append to `tests/optimizers/test_run_telemetry.py`:

```python
def test_build_evaluation_events_new_schema_has_required_fields() -> None:
    from optimizers.run_telemetry import build_evaluation_events

    # Build from a minimally shaped fake history — engineer fills in fields that
    # match the real input structure observed in existing driver tests.
    history = [
        {
            "generation": 0,
            "individuals": [
                {
                    "individual_id": "g000-i00",
                    "status": "ok",
                    "objectives": {"temperature_max": 315.0, "temperature_gradient_rms": 2.7},
                    "constraints": {
                        "total_radiator_span": 0.6,
                        "radiator_span_max": 0.8,
                        "violation": 0.0,
                    },
                    "timing": {"cheap_ms": 1.2, "solve_ms": 850.0},
                    "decision_id": "g000-e0000-d00",
                }
            ],
        }
    ]
    rows = build_evaluation_events(history)
    assert len(rows) == 1
    row = rows[0]
    for key in (
        "decision_id",
        "generation",
        "eval_index",
        "individual_id",
        "objectives",
        "constraints",
        "status",
        "timing",
    ):
        assert key in row, f"missing {key}"
    assert row["objectives"]["temperature_max"] == 315.0
    assert row["status"] == "ok"
```

- [ ] **Step 3: Run test — expect current implementation may pass or fail depending on legacy shape**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_run_telemetry.py -v -k test_build_evaluation_events_new_schema_has_required_fields`

- [ ] **Step 4: Update `build_evaluation_events` to emit the § 4.1 schema**

Replace the function body so each row contains exactly the § 4.1 keys. A monotonic `eval_index` counter is maintained across generations.

```python
def build_evaluation_events(history: list[dict]) -> list[dict]:
    """§ 4.1 evaluation_events rows — one per evaluation."""
    rows: list[dict] = []
    eval_index = 0
    for generation_entry in history:
        generation = int(generation_entry["generation"])
        for individual in generation_entry["individuals"]:
            rows.append(
                {
                    "decision_id": individual.get("decision_id"),
                    "generation": generation,
                    "eval_index": eval_index,
                    "individual_id": str(individual["individual_id"]),
                    "objectives": individual.get("objectives"),
                    "constraints": individual.get("constraints"),
                    "status": individual.get("status", "ok"),
                    "timing": individual.get("timing", {}),
                }
            )
            eval_index += 1
    return rows
```

- [ ] **Step 5: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_run_telemetry.py -v`
Expected: all tests touching `build_evaluation_events` pass. If legacy tests broke because they asserted the old schema, update them to the new schema — the old schema is deleted.

- [ ] **Step 6: Commit**

```bash
git add optimizers/run_telemetry.py tests/optimizers/test_run_telemetry.py
git commit -m "refactor(telemetry): switch evaluation_events to spec § 4.1 schema

Emits decision_id, generation, eval_index, individual_id, objectives,
constraints, status, timing. No legacy fields."
```

### Task 17: Add operator_trace.jsonl writer for all drivers

**Files:**
- Create: `optimizers/traces/operator_trace.py`
- Create: `tests/optimizers/test_operator_trace.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_operator_trace.py
"""operator_trace.jsonl emitter — all modes, § 4.3 schema."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def test_emit_operator_trace_row_shape(tmp_path: Path) -> None:
    from optimizers.traces.operator_trace import emit_operator_trace

    target = tmp_path / "operator_trace.jsonl"
    emit_operator_trace(
        target,
        generation=3,
        operator_name="global_explore",
        parents=["g003-i00"],
        offspring=["g003-i10"],
        params={"sigma": 0.1},
        wall_ms=42.1,
        decision_id="g003-e0030-d00",
    )
    row = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert row["operator_name"] == "global_explore"
    assert row["generation"] == 3
    assert row["parents"] == ["g003-i00"]
    assert row["offspring"] == ["g003-i10"]
    assert row["decision_id"] == "g003-e0030-d00"
    assert row["wall_ms"] == 42.1
    expected_digest = hashlib.sha1(b'{"sigma":0.1}').hexdigest()
    assert row["params_digest"] == expected_digest


def test_emit_operator_trace_null_decision_for_raw_union(tmp_path: Path) -> None:
    from optimizers.traces.operator_trace import emit_operator_trace

    target = tmp_path / "operator_trace.jsonl"
    emit_operator_trace(
        target,
        generation=0,
        operator_name="native_sbx_pm",
        parents=["g000-i00", "g000-i01"],
        offspring=["g000-i10"],
        params={},
        wall_ms=1.1,
        decision_id=None,
    )
    row = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert row["decision_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
# optimizers/traces/operator_trace.py
"""Emit operator_trace.jsonl rows — spec § 4.3 schema, used by all drivers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.traces.jsonl_writer import append_jsonl


def emit_operator_trace(
    path: Path,
    *,
    generation: int,
    operator_name: str,
    parents: Sequence[str],
    offspring: Sequence[str],
    params: Mapping[str, Any],
    wall_ms: float,
    decision_id: str | None,
) -> None:
    """Append one § 4.3 operator_trace record."""
    params_serialized = json.dumps(dict(params), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha1(params_serialized.encode("utf-8")).hexdigest()
    append_jsonl(
        path,
        {
            "decision_id": decision_id,
            "generation": int(generation),
            "operator_name": str(operator_name),
            "parents": list(parents),
            "offspring": list(offspring),
            "params_digest": digest,
            "wall_ms": float(wall_ms),
        },
    )
```

- [ ] **Step 4: Run tests**

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/traces/operator_trace.py tests/optimizers/test_operator_trace.py
git commit -m "feat(traces): operator_trace.jsonl emitter for all drivers"
```

### Task 18: Controller trace writer (spec § 4.4)

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py` (lines around 126-214)
- Create: `tests/optimizers/test_controller_trace_new_schema.py`

- [ ] **Step 1: Read the current llm_controller trace code**

Read [optimizers/operator_pool/llm_controller.py](optimizers/operator_pool/llm_controller.py) around lines 126-214 to identify the existing `self.request_trace.append(...)` and `self.response_trace.append(...)` sites.

- [ ] **Step 2: Write the new-schema test**

```python
# tests/optimizers/test_controller_trace_new_schema.py
"""LLM controller writes § 4.4 controller_trace.jsonl records."""

from __future__ import annotations

import json
from pathlib import Path


def test_controller_trace_records_have_new_schema(tmp_path: Path) -> None:
    """A canned controller invocation emits a § 4.4 record referencing a prompt ref."""
    # This test depends on an existing test fixture that stands up a
    # fake LLM response. Engineer: locate the existing controller test
    # fixture in tests/optimizers/test_llm_controller*.py and reuse the
    # smallest fake harness. Here we assert only the schema of the
    # emitted record.
    from optimizers.traces.prompt_store import PromptStore
    from optimizers.operator_pool.llm_controller import LLMController

    # Engineer: construct a LLMController with a stub client that returns a
    # fixed response, point it at `tmp_path / "run"`, call one decide(),
    # then read `tmp_path/run/traces/controller_trace.jsonl`.
    # Assertions:
    trace_path = tmp_path / "run" / "traces" / "controller_trace.jsonl"
    # (harness elided — engineer fills in based on existing fixtures)
    # After one decide():
    assert trace_path.exists()
    rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    row = rows[0]
    for key in (
        "decision_id",
        "phase",
        "operator_selected",
        "operator_pool_snapshot",
        "input_state_digest",
        "prompt_ref",
        "rationale",
        "fallback_used",
        "latency_ms",
    ):
        assert key in row
    assert row["prompt_ref"].startswith("prompts/")
    assert row["prompt_ref"].endswith(".md")
```

Note — this test is marked `skip` initially because it requires harness wiring already present in other controller tests. The engineer copies from `tests/optimizers/test_llm_controller.py` and adapts.

```python
import pytest

pytestmark = pytest.mark.skip(reason="requires harness wiring — see test_llm_controller.py")
```

- [ ] **Step 3: Update the controller to emit new schema**

In `optimizers/operator_pool/llm_controller.py`, replace the legacy `self.request_trace.append(...)` / `self.response_trace.append(...)` path with a new `_emit_controller_trace()` method that uses `append_jsonl` + `PromptStore`:

```python
from optimizers.traces.correlation import format_decision_id
from optimizers.traces.jsonl_writer import append_jsonl
from optimizers.traces.prompt_store import PromptStore
```

Then at each decision site, after a successful LLM call:

```python
prompt_ref = self._prompt_store.store(
    kind="request",
    body=prompt_body,
    model=self._model,
    decision_id=decision_id,
)
response_ref = self._prompt_store.store(
    kind="response",
    body=response_body,
    model=self._model,
    decision_id=decision_id,
)
append_jsonl(
    self._controller_trace_path,
    {
        "decision_id": decision_id,
        "phase": phase,
        "operator_selected": operator_name,
        "operator_pool_snapshot": list(self._operator_pool),
        "input_state_digest": input_state_digest,
        "prompt_ref": prompt_ref,
        "rationale": rationale,
        "fallback_used": fallback_used,
        "latency_ms": latency_ms,
    },
)
append_jsonl(
    self._llm_request_trace_path,
    {
        "decision_id": decision_id,
        "prompt_ref": prompt_ref,
        "model": self._model,
        "http_status": http_status,
        "retries": retries,
        "latency_ms": latency_ms,
    },
)
append_jsonl(
    self._llm_response_trace_path,
    {
        "decision_id": decision_id,
        "response_ref": response_ref,
        "model": self._model,
        "tokens": tokens,
        "finish_reason": finish_reason,
        "http_status": http_status,
        "retries": retries,
        "latency_ms": latency_ms,
    },
)
```

Delete the legacy `self.request_trace = []` / `self.response_trace = []` in-memory buffers and their corresponding JSON writers further downstream — all traces stream to disk via `append_jsonl` now.

- [ ] **Step 4: Update existing controller tests that asserted the legacy schema**

Find `tests/optimizers/test_llm_controller*.py` tests that inspect `self.request_trace` or `self.response_trace` in-memory buffers; update them to read the new JSONL files from disk, or delete assertions that are no longer meaningful.

- [ ] **Step 5: Run the controller test suite**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller.py tests/optimizers/test_controller_trace_new_schema.py -v`
Expected: all non-skipped tests pass.

- [ ] **Step 6: Commit**

```bash
git add optimizers/operator_pool/llm_controller.py tests/optimizers/test_llm_controller.py tests/optimizers/test_controller_trace_new_schema.py
git commit -m "refactor(llm-controller): emit § 4.4 controller_trace + externalized prompts

Trace lines now narrow (<1KB) and grep-friendly; full prompt and
response bodies live in content-addressed prompts/<sha1>.md."
```

---

## Phase 6: Run Directory Layout + Run Manifest

### Task 19: Run manifest writer

**Files:**
- Create: `optimizers/run_manifest.py`
- Create: `tests/optimizers/test_run_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_run_manifest.py
"""Run manifest (run.yaml) top-level fields."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_write_run_manifest_round_trips(tmp_path: Path) -> None:
    from optimizers.run_manifest import write_run_manifest

    target = tmp_path / "run.yaml"
    write_run_manifest(
        target,
        mode="llm",
        benchmark_seed=11,
        algorithm_seed=7,
        optimization_spec_path="scenarios/optimization/s1_typical_llm.yaml",
        evaluation_spec_path="scenarios/evaluation/s1_typical_eval.yaml",
        population_size=10,
        num_generations=5,
        wall_seconds=42.0,
    )
    payload = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert payload["mode"] == "llm"
    assert payload["seeds"]["benchmark"] == 11
    assert payload["seeds"]["algorithm"] == 7
    assert payload["algorithm"]["population_size"] == 10
    assert payload["algorithm"]["num_generations"] == 5
    assert payload["timing"]["wall_seconds"] == 42.0
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
# optimizers/run_manifest.py
"""Write the canonical run.yaml manifest at the top of each run."""

from __future__ import annotations

from pathlib import Path

import yaml


def write_run_manifest(
    path: Path,
    *,
    mode: str,
    benchmark_seed: int,
    algorithm_seed: int,
    optimization_spec_path: str,
    evaluation_spec_path: str,
    population_size: int,
    num_generations: int,
    wall_seconds: float,
) -> None:
    """Write run.yaml with the top-level schema agreed in § 3.1."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": mode,
        "seeds": {"benchmark": int(benchmark_seed), "algorithm": int(algorithm_seed)},
        "specs": {
            "optimization": optimization_spec_path,
            "evaluation": evaluation_spec_path,
        },
        "algorithm": {
            "population_size": int(population_size),
            "num_generations": int(num_generations),
        },
        "timing": {"wall_seconds": float(wall_seconds)},
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
```

- [ ] **Step 4: Run tests**

Expected: 1 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/run_manifest.py tests/optimizers/test_run_manifest.py
git commit -m "feat(optimizers): add run.yaml manifest writer"
```

### Task 20: Flat representative layout

**Files:**
- Modify: `optimizers/artifacts.py` (the `_write_representative_bundle` / `_initialize_representative_bundle_root` area)
- Create: `tests/optimizers/test_representative_layout.py`

The spec § 3.1 requires representative depth to drop to 3 levels: `representatives/<id>/fields/*.npz` plus `case.yaml`, `solution.yaml`, `evaluation.yaml` at the top of the representative dir. No separate `figures/` or `summaries/` subdirs inside representative; figures are rendered centrally.

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_representative_layout.py
"""Representative bundle layout — flat, 3-level max."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def test_write_representative_bundle_flat_layout(tmp_path: Path) -> None:
    from optimizers.artifacts import write_representative_bundle

    repr_root = tmp_path / "representatives" / "knee"
    write_representative_bundle(
        repr_root,
        case_yaml="{}",
        solution_yaml="{}",
        evaluation_yaml="{}",
        temperature_grid=np.zeros((4, 4)),
        gradient_grid=np.zeros((4, 4)),
    )

    # Allowed top-level entries
    expected_top = {"case.yaml", "solution.yaml", "evaluation.yaml", "fields"}
    actual_top = {p.name for p in repr_root.iterdir()}
    assert actual_top == expected_top

    # fields/ contains only the two npz files
    fields = set(p.name for p in (repr_root / "fields").iterdir())
    assert fields == {"temperature_grid.npz", "gradient_magnitude_grid.npz"}

    # No figures/ or summaries/ subdir inside the representative
    assert not (repr_root / "figures").exists()
    assert not (repr_root / "summaries").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL — `write_representative_bundle` does not yet exist as a public function with that signature.

- [ ] **Step 3: Add the public function to `optimizers/artifacts.py`**

Replace (or add alongside and delete the old one in Phase 9) the existing representative writer with:

```python
# optimizers/artifacts.py  (add near existing representative code)
import numpy as np


def write_representative_bundle(
    root: Path,
    *,
    case_yaml: str,
    solution_yaml: str,
    evaluation_yaml: str,
    temperature_grid: np.ndarray,
    gradient_grid: np.ndarray,
) -> None:
    """Write the flat § 3.1 representative layout.

    Layout:
      representatives/<id>/case.yaml
      representatives/<id>/solution.yaml
      representatives/<id>/evaluation.yaml
      representatives/<id>/fields/temperature_grid.npz
      representatives/<id>/fields/gradient_magnitude_grid.npz
    """
    root = Path(root)
    (root / "fields").mkdir(parents=True, exist_ok=True)
    (root / "case.yaml").write_text(case_yaml, encoding="utf-8")
    (root / "solution.yaml").write_text(solution_yaml, encoding="utf-8")
    (root / "evaluation.yaml").write_text(evaluation_yaml, encoding="utf-8")
    np.savez_compressed(root / "fields" / "temperature_grid.npz", grid=temperature_grid)
    np.savez_compressed(root / "fields" / "gradient_magnitude_grid.npz", grid=gradient_grid)
```

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_representative_layout.py -v`
Expected: 1 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/artifacts.py tests/optimizers/test_representative_layout.py
git commit -m "feat(artifacts): flat 3-level representative bundle layout"
```

### Task 21: Multi-seed layout switch

**Files:**
- Create: `optimizers/run_layout.py`
- Create: `tests/optimizers/test_multi_seed_layout.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_multi_seed_layout.py
"""Flat for N=1, seeds/seed-<n>/ for N>=2, with aggregate gate semantics tested explicitly."""

from __future__ import annotations

from pathlib import Path


def test_resolve_seed_run_root_flat_for_single_seed(tmp_path: Path) -> None:
    from optimizers.run_layout import resolve_seed_run_root

    run_root = tmp_path / "0416_2030__llm"
    path = resolve_seed_run_root(run_root, seed=11, total_seeds=1)
    assert path == run_root


def test_resolve_seed_run_root_wraps_for_multiple_seeds(tmp_path: Path) -> None:
    from optimizers.run_layout import resolve_seed_run_root

    run_root = tmp_path / "0416_2030__llm"
    path = resolve_seed_run_root(run_root, seed=11, total_seeds=3)
    assert path == run_root / "seeds" / "seed-11"


def test_should_write_aggregate_true_only_for_three_or_more(tmp_path: Path) -> None:
    from optimizers.run_layout import should_write_aggregate

    assert should_write_aggregate(total_seeds=1) is False
    assert should_write_aggregate(total_seeds=2) is False
    assert should_write_aggregate(total_seeds=3) is True
    assert should_write_aggregate(total_seeds=30) is True
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
# optimizers/run_layout.py
"""Directory layout switches — single-seed flat vs multi-seed wrapped."""

from __future__ import annotations

from pathlib import Path


def resolve_seed_run_root(run_root: Path, *, seed: int, total_seeds: int) -> Path:
    """Return the directory a single seed's artifacts live under.

    - N=1: flat (run_root itself)
    - N>=2: run_root / "seeds" / "seed-<n>"
    """
    if total_seeds < 1:
        raise ValueError(f"total_seeds must be >= 1; got {total_seeds}")
    if total_seeds == 1:
        return Path(run_root)
    return Path(run_root) / "seeds" / f"seed-{int(seed)}"


def should_write_aggregate(*, total_seeds: int) -> bool:
    """Aggregate statistics are only meaningful with >=3 seeds."""
    return total_seeds >= 3
```

- [ ] **Step 4: Run tests**

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/run_layout.py tests/optimizers/test_multi_seed_layout.py
git commit -m "feat(optimizers): add run layout switches (flat vs seeds/, aggregate gate)"
```

---

## Phase 7: CLI Integration

### Task 22: Pop/gen CLI overrides

**Files:**
- Modify: `optimizers/cli.py` — `optimize-benchmark` and `run-benchmark-suite` subparsers
- Create: `tests/optimizers/test_cli_pop_gen_overrides.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_cli_pop_gen_overrides.py
"""CLI --population-size / --num-generations overrides."""

from __future__ import annotations


def test_build_parser_accepts_pop_gen_overrides() -> None:
    from optimizers.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(
        [
            "optimize-benchmark",
            "--optimization-spec",
            "scenarios/optimization/s1_typical_llm.yaml",
            "--output-root",
            "./scenario_runs/smoke",
            "--population-size",
            "10",
            "--num-generations",
            "5",
        ]
    )
    assert args.population_size == 10
    assert args.num_generations == 5


def test_apply_algorithm_overrides_mutates_spec_dict() -> None:
    from optimizers.cli import apply_algorithm_overrides

    spec_dict = {"algorithm": {"population_size": 32, "num_generations": 16}}
    apply_algorithm_overrides(spec_dict, population_size=10, num_generations=5)
    assert spec_dict["algorithm"]["population_size"] == 10
    assert spec_dict["algorithm"]["num_generations"] == 5


def test_apply_algorithm_overrides_noop_when_absent() -> None:
    from optimizers.cli import apply_algorithm_overrides

    spec_dict = {"algorithm": {"population_size": 32, "num_generations": 16}}
    apply_algorithm_overrides(spec_dict, population_size=None, num_generations=None)
    assert spec_dict["algorithm"]["population_size"] == 32
    assert spec_dict["algorithm"]["num_generations"] == 16
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL — parser rejects unknown args.

- [ ] **Step 3: Modify `build_parser` in [optimizers/cli.py](optimizers/cli.py)**

Add to both `optimize_parser` and `suite_parser`:

```python
optimize_parser.add_argument("--population-size", type=_positive_int, default=None)
optimize_parser.add_argument("--num-generations", type=_positive_int, default=None)

suite_parser.add_argument("--population-size", type=_positive_int, default=None)
suite_parser.add_argument("--num-generations", type=_positive_int, default=None)
```

Add the helper:

```python
def apply_algorithm_overrides(
    spec_dict: dict,
    *,
    population_size: int | None,
    num_generations: int | None,
) -> None:
    """Overwrite `algorithm.population_size` / `num_generations` when provided."""
    if population_size is not None:
        spec_dict.setdefault("algorithm", {})["population_size"] = int(population_size)
    if num_generations is not None:
        spec_dict.setdefault("algorithm", {})["num_generations"] = int(num_generations)
```

Wire into the `optimize-benchmark` branch: after `load_optimization_spec()` but before constructing the driver, call `apply_algorithm_overrides(optimization_spec._raw_dict, ...)` — or adjust the call to fit the existing `OptimizationSpec` shape (engineer confirms by reading [optimizers/io.py](optimizers/io.py)).

- [ ] **Step 4: Run tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_cli_pop_gen_overrides.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/cli.py tests/optimizers/test_cli_pop_gen_overrides.py
git commit -m "feat(cli): add --population-size / --num-generations overrides

Enables 10×5 smoke runs without mutating scenario spec files."
```

### Task 23: `render-assets` subcommand

**Files:**
- Create: `optimizers/render_assets.py`
- Modify: `optimizers/cli.py` — new subparser
- Create: `tests/visualization/test_render_assets_fixtures.py`

- [ ] **Step 1: Write the failing end-to-end test**

```python
# tests/visualization/test_render_assets_fixtures.py
"""End-to-end: synthetic trace bundle → render-assets → asserts all outputs."""

from __future__ import annotations

import json
from pathlib import Path


def _seed_run_bundle(run_root: Path) -> None:
    """Create a tiny run bundle with the minimum traces needed for analytics."""
    traces = run_root / "traces"
    traces.mkdir(parents=True, exist_ok=True)

    (traces / "evaluation_events.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "decision_id": None,
                    "generation": 0,
                    "eval_index": 0,
                    "individual_id": "g000-i00",
                    "objectives": {"temperature_max": 320.0, "temperature_gradient_rms": 3.0},
                    "constraints": {"total_radiator_span": 0.6, "radiator_span_max": 0.8, "violation": 0.0},
                    "status": "ok",
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                },
                {
                    "decision_id": None,
                    "generation": 1,
                    "eval_index": 1,
                    "individual_id": "g001-i00",
                    "objectives": {"temperature_max": 310.0, "temperature_gradient_rms": 2.5},
                    "constraints": {"total_radiator_span": 0.55, "radiator_span_max": 0.8, "violation": 0.0},
                    "status": "ok",
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "operator_trace.jsonl").write_text(
        json.dumps(
            {
                "decision_id": None,
                "generation": 1,
                "operator_name": "native_sbx_pm",
                "parents": ["g000-i00"],
                "offspring": ["g001-i00"],
                "params_digest": "a" * 40,
                "wall_ms": 1.2,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_render_assets_produces_required_outputs(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from optimizers.render_assets import render_run_assets

    run_root = tmp_path / "0416_2030__raw"
    _seed_run_bundle(run_root)

    render_run_assets(run_root, hires=False)

    assert (run_root / "analytics" / "hypervolume.csv").exists()
    assert (run_root / "analytics" / "operator_phase_heatmap.csv").exists()
    assert (run_root / "figures" / "hypervolume_progress.png").exists()
    assert (run_root / "figures" / "hypervolume_progress.pdf").exists()
    assert (run_root / "figures" / "operator_phase_heatmap.png").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with `ModuleNotFoundError: No module named 'optimizers.render_assets'`.

- [ ] **Step 3: Create the orchestrator**

```python
# optimizers/render_assets.py
"""Read traces, compute analytics, render figures and tables."""

from __future__ import annotations

import csv
from pathlib import Path

from optimizers.analytics.heatmap import operator_phase_heatmap
from optimizers.analytics.loaders import iter_jsonl
from optimizers.analytics.rollups import rollup_per_generation
from visualization.figures.hypervolume import render_hypervolume_progress
from visualization.figures.operator_heatmap import render_operator_heatmap

REFERENCE_POINT = (400.0, 20.0)   # § 5 reference point for s1_typical


def render_run_assets(run_root: Path, *, hires: bool = False) -> None:
    run_root = Path(run_root)
    traces = run_root / "traces"
    analytics = run_root / "analytics"
    figures = run_root / "figures"
    analytics.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    events = list(iter_jsonl(traces / "evaluation_events.jsonl"))
    summaries = rollup_per_generation(events, reference_point=REFERENCE_POINT)

    with (analytics / "hypervolume.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["generation", "hypervolume"])
        for summary in summaries:
            writer.writerow([summary["generation"], summary["hypervolume"]])

    render_hypervolume_progress(
        series={run_root.name.split("__", 1)[-1]: [(s["generation"], s["hypervolume"]) for s in summaries]},
        output=figures / "hypervolume_progress.png",
        hires=hires,
    )

    operator_rows = list(iter_jsonl(traces / "operator_trace.jsonl"))
    controller_rows = list(iter_jsonl(traces / "controller_trace.jsonl"))
    grid = operator_phase_heatmap(operator_rows, controller_rows)

    with (analytics / "operator_phase_heatmap.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        phases: list[str] = []
        for counts in grid.values():
            for phase in counts:
                if phase not in phases:
                    phases.append(phase)
        writer.writerow(["operator", *phases])
        for operator, counts in sorted(grid.items()):
            writer.writerow([operator, *(counts.get(p, 0) for p in phases)])

    if grid:
        render_operator_heatmap(grid=grid, output=figures / "operator_phase_heatmap.png", hires=hires)
```

- [ ] **Step 4: Add the CLI subparser**

In [optimizers/cli.py](optimizers/cli.py) `build_parser`:

```python
render_parser = subparsers.add_parser("render-assets")
render_parser.add_argument("--run", required=True)
render_parser.add_argument("--hires", action="store_true")
```

In `main`:

```python
if args.command == "render-assets":
    from optimizers.render_assets import render_run_assets
    render_run_assets(Path(args.run), hires=args.hires)
    return 0
```

- [ ] **Step 5: Run tests**

Run: `conda run -n msfenicsx pytest tests/visualization/test_render_assets_fixtures.py -v`
Expected: 1 PASS.

- [ ] **Step 6: Commit**

```bash
git add optimizers/render_assets.py optimizers/cli.py tests/visualization/test_render_assets_fixtures.py
git commit -m "feat(cli): add render-assets subcommand

Idempotent pipeline: traces/ → analytics/ → figures/ + tables/.
Rerunnable independently of the driver."
```

### Task 24: `compare-runs` subcommand

**Files:**
- Create: `optimizers/compare_runs.py`
- Modify: `optimizers/cli.py`
- Create: `tests/optimizers/test_compare_runs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/optimizers/test_compare_runs.py
"""compare-runs builds Pareto overlay + summary table across 2+ runs."""

from __future__ import annotations

import json
from pathlib import Path


def _seed_run(run_root: Path, label: str) -> None:
    (run_root / "traces").mkdir(parents=True, exist_ok=True)
    (run_root / "traces" / "evaluation_events.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "decision_id": None,
                    "generation": g,
                    "eval_index": g,
                    "individual_id": f"{label}-g{g}",
                    "objectives": {
                        "temperature_max": 320.0 - g,
                        "temperature_gradient_rms": 3.0 - 0.1 * g,
                    },
                    "constraints": {"total_radiator_span": 0.5, "radiator_span_max": 0.8, "violation": 0.0},
                    "status": "ok",
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                }
            )
            for g in range(3)
        )
        + "\n",
        encoding="utf-8",
    )


def test_compare_runs_writes_overlay_and_summary(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from optimizers.compare_runs import compare_runs

    run_a = tmp_path / "0416_2030__raw"
    run_b = tmp_path / "0416_2035__llm"
    _seed_run(run_a, "raw")
    _seed_run(run_b, "llm")

    output = tmp_path / "comparisons" / "0416_2100__raw_vs_llm"
    compare_runs(runs=[run_a, run_b], output=output)

    assert (output / "pareto_overlay.png").exists()
    assert (output / "pareto_overlay.pdf").exists()
    assert (output / "summary_table.csv").exists()
    assert (output / "inputs.yaml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
# optimizers/compare_runs.py
"""Cross-mode comparison: Pareto overlay + summary table."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

import yaml

from optimizers.analytics.loaders import iter_jsonl
from optimizers.analytics.pareto import pareto_front_indices
from visualization.figures.pareto import render_pareto_front


def _extract_final_front(run_root: Path) -> list[tuple[float, float]]:
    events = list(iter_jsonl(run_root / "traces" / "evaluation_events.jsonl"))
    feasible = [e for e in events if e.get("status") == "ok" and e.get("objectives")]
    points = [
        (float(e["objectives"]["temperature_max"]), float(e["objectives"]["temperature_gradient_rms"]))
        for e in feasible
    ]
    if not points:
        return []
    idx = pareto_front_indices(points)
    return [points[i] for i in idx]


def _mode_of(run_root: Path) -> str:
    name = run_root.name
    return name.split("__", 1)[-1] if "__" in name else name


def compare_runs(*, runs: Sequence[Path], output: Path) -> None:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    fronts: dict[str, list[tuple[float, float]]] = {}
    rows: list[dict] = []
    for run_root in runs:
        mode = _mode_of(Path(run_root))
        front = _extract_final_front(Path(run_root))
        fronts[mode] = front
        if front:
            t_min = min(p[0] for p in front)
            g_min = min(p[1] for p in front)
            rows.append({"mode": mode, "run": str(run_root), "t_max_min": t_min, "grad_rms_min": g_min, "front_size": len(front)})
        else:
            rows.append({"mode": mode, "run": str(run_root), "t_max_min": None, "grad_rms_min": None, "front_size": 0})

    render_pareto_front(fronts=fronts, output=output / "pareto_overlay.png")

    with (output / "summary_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "run", "t_max_min", "grad_rms_min", "front_size"])
        writer.writeheader()
        writer.writerows(rows)

    (output / "inputs.yaml").write_text(
        yaml.safe_dump({"runs": [str(r) for r in runs]}, sort_keys=False),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Add the CLI subparser**

In [optimizers/cli.py](optimizers/cli.py) `build_parser`:

```python
compare_parser = subparsers.add_parser("compare-runs")
compare_parser.add_argument("--run", required=True, action="append")
compare_parser.add_argument("--output", required=True)
```

In `main`:

```python
if args.command == "compare-runs":
    from optimizers.compare_runs import compare_runs
    compare_runs(runs=[Path(r) for r in args.run], output=Path(args.output))
    return 0
```

- [ ] **Step 5: Run tests**

Expected: 1 PASS.

- [ ] **Step 6: Commit**

```bash
git add optimizers/compare_runs.py optimizers/cli.py tests/optimizers/test_compare_runs.py
git commit -m "feat(cli): add compare-runs subcommand

Pareto overlay + CSV summary + inputs manifest across any number of
single-mode runs. No side effects on source runs."
```

### Task 25: Driver integration — auto-render at end of `optimize-benchmark`

**Files:**
- Modify: `optimizers/cli.py` — `optimize-benchmark` branch
- Modify: `optimizers/cli.py` — add `--skip-render` flag

- [ ] **Step 1: Add the flag**

In `build_parser`:

```python
optimize_parser.add_argument("--skip-render", action="store_true")
suite_parser.add_argument("--skip-render", action="store_true")
```

- [ ] **Step 2: Wire the call**

In the `optimize-benchmark` branch of `main`, after the driver call (`run_raw_optimization`, `run_union_optimization`, or the llm equivalent), add:

```python
if not args.skip_render:
    from optimizers.render_assets import render_run_assets
    render_run_assets(run.output_root, hires=False)
```

Engineer verifies `run.output_root` is the right attribute on the returned `OptimizationRun` object by reading the driver source.

- [ ] **Step 3: Smoke test (manual)**

```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --output-root ./scenario_runs/s1_typical/smoke-raw \
  --population-size 10 --num-generations 5 \
  --evaluation-workers 2
```

Expected: exits 0, and `./scenario_runs/s1_typical/smoke-raw/<timestamp>__raw/figures/` contains at least `hypervolume_progress.png`.

- [ ] **Step 4: Commit**

```bash
git add optimizers/cli.py
git commit -m "feat(cli): auto-render assets at end of optimize-benchmark

Adds --skip-render flag for fast-loop debugging."
```

---

## Phase 8: Migration Cleanup

### Task 26: Delete legacy visualization modules and tests

**Files:**
- Delete: `visualization/case_pages.py`
- Delete: `visualization/figure_axes.py`
- Delete: `visualization/figure_theme.py`
- Delete: `visualization/static_assets.py` (if no longer imported by the new figures package — engineer confirms with `rg "from visualization.static_assets"` first)
- Delete: `tests/visualization/test_case_pages.py`
- Delete: `tests/visualization/test_comparison_pages.py`
- Delete: `tests/visualization/test_figure_system.py`
- Delete: `tests/visualization/test_llm_pages.py`
- Delete: `tests/visualization/test_llm_reports.py`
- Delete: `tests/visualization/test_mode_pages.py`

- [ ] **Step 1: Verify nothing new imports the legacy modules**

Run:

```bash
conda run -n msfenicsx python -c "import ast, pathlib; [print(p) for p in pathlib.Path('.').rglob('*.py') if any(x in p.read_text() for x in ('from visualization.case_pages', 'from visualization.figure_axes', 'from visualization.figure_theme', 'from visualization.static_assets'))]"
```

Expected output: only the legacy test files listed above. If any new module in `visualization/figures/` or `optimizers/render_assets.py` imports these, refactor the import first.

- [ ] **Step 2: Delete**

```bash
git rm visualization/case_pages.py visualization/figure_axes.py visualization/figure_theme.py visualization/static_assets.py
git rm tests/visualization/test_case_pages.py tests/visualization/test_comparison_pages.py tests/visualization/test_figure_system.py tests/visualization/test_llm_pages.py tests/visualization/test_llm_reports.py tests/visualization/test_mode_pages.py
```

- [ ] **Step 3: Also remove the legacy in-memory trace buffers in the driver**

If the `run_raw_optimization`, `run_union_optimization`, or llm driver still writes legacy trace JSON files (not JSONL), remove those writers now. Engineer greps:

```bash
conda run -n msfenicsx grep -rn "write_json\|controller_trace.json\b\|request_trace.json\b\|response_trace.json\b" optimizers/ | grep -v analytics | grep -v render_assets
```

Remove each hit that refers to legacy `.json` (not `.jsonl`) writers for controller/request/response traces.

- [ ] **Step 4: Run kept tests**

```bash
conda run -n msfenicsx pytest -v \
  tests/visualization/test_heatfield_orientation.py \
  tests/visualization/test_render_assets_fixtures.py \
  tests/optimizers/test_multi_seed_layout.py \
  tests/optimizers/test_style_baseline.py \
  tests/optimizers/test_correlation_id.py \
  tests/optimizers/test_jsonl_writer.py \
  tests/optimizers/test_prompt_store.py \
  tests/optimizers/test_analytics_loaders.py \
  tests/optimizers/test_analytics_pareto.py \
  tests/optimizers/test_analytics_rollups.py \
  tests/optimizers/test_analytics_heatmap.py \
  tests/optimizers/test_analytics_decisions.py \
  tests/optimizers/test_operator_trace.py \
  tests/optimizers/test_run_manifest.py \
  tests/optimizers/test_representative_layout.py \
  tests/optimizers/test_cli_pop_gen_overrides.py \
  tests/optimizers/test_compare_runs.py \
  tests/optimizers/test_llm_controller.py
```

Expected: all PASS. If `test_llm_controller.py` fails because of the switch to new-schema traces, update assertions to read from the JSONL files.

- [ ] **Step 5: Commit**

```bash
git commit -m "chore: delete legacy visualization and trace modules

Removes case_pages.py, figure_axes.py (source of the inverted-colorbar
bug), figure_theme.py, static_assets.py, and the six legacy visualization
tests they served. Drivers now emit only new-schema JSONL traces."
```

---

## Phase 9: Smoke Verification

### Task 27: Smoke harness script

**Files:**
- Create: `scripts/smoke_render_assets.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# Smoke test: run raw/union/llm at 10×5 and verify outputs.
set -euo pipefail

SCENARIO_ROOT="./scenario_runs/s1_typical/smoke"
MODES=("raw" "union" "llm")

rm -rf "$SCENARIO_ROOT"

for mode in "${MODES[@]}"; do
    echo "=== smoke: $mode ==="
    conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
        --optimization-spec "scenarios/optimization/s1_typical_${mode}.yaml" \
        --output-root "${SCENARIO_ROOT}-${mode}" \
        --population-size 10 --num-generations 5 \
        --evaluation-workers 2
done

echo "=== verifying outputs ==="
for mode in "${MODES[@]}"; do
    run_dir=$(find "${SCENARIO_ROOT}-${mode}" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    for required in \
        "traces/evaluation_events.jsonl" \
        "traces/operator_trace.jsonl" \
        "analytics/hypervolume.csv" \
        "figures/hypervolume_progress.png" \
        "figures/hypervolume_progress.pdf" \
        "figures/operator_phase_heatmap.png" \
        "run.yaml"
    do
        if [[ ! -f "${run_dir}/${required}" ]]; then
            echo "MISSING: ${run_dir}/${required}"
            exit 1
        fi
    done
    echo "ok: ${mode}"
done

echo "=== all smokes passed ==="
```

- [ ] **Step 2: Make it executable and run it**

```bash
chmod +x scripts/smoke_render_assets.sh
bash scripts/smoke_render_assets.sh
```

Expected: each mode completes in ~3-5 minutes; final `all smokes passed` line.

- [ ] **Step 3: Commit**

```bash
git add scripts/smoke_render_assets.sh
git commit -m "feat(scripts): add 10×5 smoke harness for all three modes"
```

### Task 28: Final test pass

- [ ] **Step 1: Run the minimum test matrix**

```bash
conda run -n msfenicsx pytest -v \
  tests/visualization/test_heatfield_orientation.py \
  tests/visualization/test_render_assets_fixtures.py \
  tests/optimizers/test_multi_seed_layout.py
```

Expected: 3 files, all green.

- [ ] **Step 2: Quick sanity scan for stray legacy references**

```bash
conda run -n msfenicsx grep -rn "figure_theme\|case_pages\|static_assets\|figure_axes" optimizers/ visualization/ tests/ || echo "no stray legacy references"
```

Expected: the "no stray legacy references" line.

- [ ] **Step 3: If all pass, the refactor is complete. Final status commit if anything needs touching up; otherwise done.**

No commit needed if steps 1-2 are clean.

---

## Success Criteria Checklist

At the end of implementation, verify the spec's § 11 success criteria:

- [ ] All three modes produce identical top-level layout under `scenario_runs/s1_typical/<MMDD_HHMM>__<mode>/`.
- [ ] Representative figure paths are at most 3 levels deep (`representatives/<id>/fields/<file>.npz`).
- [ ] No empty `logs/` directories anywhere in a fresh run bundle.
- [ ] `test_heatfield_orientation.py` passes: high-value input pixel → top of rendered colorbar.
- [ ] `render-assets` on a 10×5 smoke run completes in <60s and produces all required outputs.
- [ ] Every line in `llm_request_trace.jsonl` is under 1KB; prompt bodies live in `prompts/<sha1>.md`.
- [ ] The three kept test files run in <30s on WSL2.

---

## Deferred Scope (flagged during self-review)

The following spec requirements are intentionally **not** implemented in this plan. They are either blocked on upstream signals that the current controller does not emit, or on multi-seed benchmark support that § 3.4 defers to a separate spec.

| Spec section | Requirement | Why deferred |
|---|---|---|
| § 4.2 | `generation_summary.jsonl` schema alignment | The existing writer already produces this file; aligning its keys to the spec fields (`hypervolume`, `controller_phase`, etc.) is a narrow follow-up. The analytics layer reads `evaluation_events.jsonl` directly, so rollups do not block on this. |
| § 5.1 | `optimizers/analytics/correlate.py` | Its function (joining traces by `decision_id`) is done inline in Task 9 (`decisions.py`) and Task 23 (`render_run_assets`). Extracting a shared helper is fine later if a second caller appears. |
| § 5.1 | `optimizers/analytics/guardrails.py` | Requires the controller to emit guardrail-activation events. Task 18 carries `fallback_used` but not the full timeline (operator-pool shrinks, JSON parse failures). Upstream signal work is a follow-up. |
| § 5.1 / § 5.4 | `optimizers/analytics/aggregate/{iqr,attainment,stats}.py` | Descriptive rollups can exist for N>=2, but the heavier inferential-statistics layer is only meaningful with N>=3 seeds. § 3.4 defers benchmark-level multi-seed experiment design to a separate spec. Task 21 already puts the layout switches in place so aggregation modules can be added without touching figures or CLI. |
| § 5.2 | `pareto.parquet` | Task 23 writes `hypervolume.csv` + `operator_phase_heatmap.csv` which cover the smoke-path needs. Parquet requires `pyarrow`; migrate when analytics grow vector columns that CSV can't hold. |
| § 5.3 | `phase_alignment.csv`, `cost_per_improvement.csv`, `guardrail_timeline.csv` | Phase-alignment depends on post-hoc phase labeling (feasibility-ratio thresholds) not yet implemented; cost-per-improvement depends on per-decision HV-delta which requires correlating consecutive `generation_summary.jsonl` rows with `controller_trace.jsonl` — another follow-up once controller traces land. Guardrail timeline depends on the § 5.1 `guardrails.py` module. |
| § 7 | `visualization/figures/guardrail_timeline.py` | Blocked on § 5.3 `guardrail_timeline.csv`. |

If the engineer finishes this plan and wants to pick up any deferred item, each is self-contained and follows the same pattern as its sibling (e.g., `correlate.py` is a pure joiner over `iter_jsonl`; add a test + module the same way Task 5 did).
- [ ] `xelatex` and `ctex.sty` are available (Phase 0 completed).
