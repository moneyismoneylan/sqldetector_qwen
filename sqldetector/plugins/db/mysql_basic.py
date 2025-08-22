from __future__ import annotations

from functools import lru_cache

from sqldetector.plugin_registry import register


@register("db", "mysql_basic")
@lru_cache(maxsize=256)
def hints(payload: str) -> list[str]:
    """Return simple hints about the payload.

    ``lru_cache`` avoids recomputing results for repeated payloads which is
    common when scanning large request sets.  The function is intentionally
    side-effect free so caching is safe and improves throughput.
    """
    tips: list[str] = []
    upper = payload.upper()
    if "SELECT" in upper:
        tips.append("possible MySQL SELECT pattern")
    if "--" in payload:
        tips.append("inline comment detected")
    return tips
