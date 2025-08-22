from __future__ import annotations

from typing import Dict
import statistics


DB_HINTS = {
    "mysql": ["mysql", "MariaDB"],
    "postgres": ["postgres", "psql"],
    "sqlserver": ["sql server", "microsoft"],
    "oracle": ["oracle"],
}


def fingerprint(headers: Dict[str, str], body: str) -> Dict[str, float]:
    """Return simple probability scores for common DBMS."""
    body_lower = body.lower()
    scores: Dict[str, float] = {}
    for name, hints in DB_HINTS.items():
        hits = sum(1 for h in hints if h in body_lower or h in str(headers).lower())
        if hits:
            scores[name] = min(1.0, hits / len(hints))
    return scores


def robust_timing(samples: list[float]) -> float:
    """Robust median estimate (Hodges–Lehmann)."""
    if not samples:
        return 0.0
    med = statistics.median(samples)
    return med
