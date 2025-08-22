"""Simple parameter type inference helpers."""
from __future__ import annotations

import re
from typing import Optional


_PATTERNS = {
    "numeric": re.compile(r"^-?\d+$"),
    "timestamp": re.compile(r"^\d{4}-\d{2}-\d{2}"),
    "slug": re.compile(r"^[a-z0-9-]+$"),
}


def infer(name: str, value: str) -> str:
    """Infer a coarse parameter type.

    The heuristic is intentionally small but deterministic for tests.
    """
    if _PATTERNS["numeric"].match(value):
        return "numeric"
    if _PATTERNS["timestamp"].match(value):
        return "timestamp"
    if _PATTERNS["slug"].match(value):
        return "slug"
    if name.lower().endswith("id"):
        return "id"
    if " " in value:
        return "search"
    return "text"
