"""HTTP method override helpers."""

from __future__ import annotations

from typing import Dict


def build_override_headers(method: str) -> Dict[str, str]:
    return {"X-HTTP-Method-Override": method}


def should_enqueue(baseline: int, override: int) -> bool:
    return baseline != override


__all__ = ["build_override_headers", "should_enqueue"]
