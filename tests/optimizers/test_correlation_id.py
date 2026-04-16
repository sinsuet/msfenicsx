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
