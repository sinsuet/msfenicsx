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
