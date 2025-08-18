from __future__ import annotations

from sqldetector.plugin_registry import register


@register("db", "mysql_basic")
def hints(payload: str) -> list[str]:
    tips: list[str] = []
    if "SELECT" in payload.upper():
        tips.append("possible MySQL SELECT pattern")
    if "--" in payload:
        tips.append("inline comment detected")
    return tips
