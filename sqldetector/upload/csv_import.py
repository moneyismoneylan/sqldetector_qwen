"""CSV/TSV upload SQLi tests."""

from __future__ import annotations

from typing import List

SAMPLE_ROWS = ["1,2,3", "a,b,c"]


def payload_rows() -> List[str]:
    return SAMPLE_ROWS.copy()


def has_error(response_text: str) -> bool:
    lowered = response_text.lower()
    return "sql" in lowered or "syntax" in lowered


__all__ = ["payload_rows", "has_error", "SAMPLE_ROWS"]
