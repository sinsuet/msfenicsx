"""Text-wrapping helpers for scientific SVG figure exports."""

from __future__ import annotations


def wrap_text_lines(text: str, *, max_chars: int, max_lines: int) -> list[str]:
    normalized = " ".join(str(text).split())
    if max_chars <= 0 or max_lines <= 0:
        return []
    if not normalized:
        return [""]

    lines: list[str] = []
    remaining = normalized
    while remaining and len(lines) < max_lines:
        if len(remaining) <= max_chars:
            lines.append(remaining)
            remaining = ""
            break

        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at <= 0:
            split_at = max_chars
        lines.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    if remaining:
        if not lines:
            return ["..."[:max_chars]]
        visible = max(0, max_chars - 3)
        lines[-1] = lines[-1][:visible].rstrip() + "..."
    return lines
