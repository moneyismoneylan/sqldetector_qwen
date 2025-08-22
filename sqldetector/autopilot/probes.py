"""Small network probe utilities used by AutoPilot."""
from __future__ import annotations

from typing import Any, Dict, Optional

try:  # optional
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None


def fetch_robots_txt(url: str, client: Any) -> Optional[str]:
    if not requests:
        return None
    try:
        resp = client.get(f"{url.rstrip('/')}/robots.txt", timeout=5)
        if resp.status_code < 400:
            return resp.text
    except Exception:
        return None
    return None


def fetch_sitemap_xml(url: str, client: Any) -> Optional[str]:
    if not requests:
        return None
    try:
        resp = client.get(f"{url.rstrip('/')}/sitemap.xml", timeout=5)
        if resp.status_code < 400:
            return resp.text
    except Exception:
        return None
    return None
