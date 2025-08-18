from __future__ import annotations

from sqldetector.plugin_registry import register


@register("waf", "cloudflare_basic")
def detect(headers: dict) -> bool:
    lowered = {k.lower(): v for k, v in headers.items()}
    return "cf-ray" in lowered
