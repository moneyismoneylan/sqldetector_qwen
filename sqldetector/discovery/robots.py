"""Minimal robots.txt fetcher."""

from __future__ import annotations

from urllib.parse import urljoin
import urllib.robotparser

from sqldetector.core.http_async import HttpClient


async def fetch_robots(client: HttpClient, base_url: str, respect: bool = True) -> dict:
    """Return crawl directives from ``base_url`` robots.txt."""

    if not respect:
        return {"allowed": True, "crawl_delay": 0.0}
    rp = urllib.robotparser.RobotFileParser()
    try:
        resp = await client.get(urljoin(base_url, "/robots.txt"))
        rp.parse(resp.text.splitlines())
    except Exception:
        return {"allowed": True, "crawl_delay": 0.0}
    return {"allowed": rp.can_fetch("*", base_url), "crawl_delay": rp.crawl_delay("*") or 0.0}

