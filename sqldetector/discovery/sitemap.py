"""Minimal sitemap.xml parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from typing import List

from sqldetector.core.http_async import HttpClient


async def fetch_sitemap(client: HttpClient, base_url: str) -> List[str]:
    """Fetch sitemap.xml and return discovered URLs."""

    url = urljoin(base_url, "/sitemap.xml")
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        return [loc.text for loc in root.findall(".//{*}loc") if loc.text]
    except Exception:
        return []

