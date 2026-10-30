"""State preparation: field redaction and head-and-tail truncation before anything leaves."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = limit // 2
    tail = limit - head
    dropped = len(text) - limit
    return f"{text[:head]}…[{dropped} chars truncated]…{text[-tail:] if tail else ''}"


def prepare_state(state: Any, *, redact: frozenset[str], max_field_chars: int) -> Any:
    """Return a copy of ``state`` with redacted keys masked and long strings truncated.

    Redaction matches dict keys at any depth. Truncation applies to every string leaf,
    including a bare string state, so the result is always valid JSON.
    """
    if isinstance(state, str):
        return _truncate(state, max_field_chars)
    if isinstance(state, Mapping):
        return {
            key: REDACTED
            if key in redact
            else prepare_state(value, redact=redact, max_field_chars=max_field_chars)
            for key, value in state.items()
        }
    if isinstance(state, Sequence) and not isinstance(state, (bytes, bytearray)):
        return [prepare_state(v, redact=redact, max_field_chars=max_field_chars) for v in state]
    return state
