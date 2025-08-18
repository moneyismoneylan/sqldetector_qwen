"""Very small WAF fingerprinting helper.

The real project would ship a comprehensive catalogue of WAF signatures and run
several HTTP probes.  For unit tests and examples we implement a tiny subset
that looks for well known markers in the response headers or body.
"""

from __future__ import annotations

import httpx


async def identify(url: str, client: httpx.AsyncClient | None = None) -> str:
    """Return a simple WAF fingerprint for ``url``.

    The function performs a single HTTP ``GET`` request and inspects headers and
    body for known markers.  Currently only very small heuristics for Cloudflare
    and generic blocks are implemented.  Unknown responses return ``"unknown"``.
    """

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True
    try:
        resp = await client.get(url)
        text = resp.text.lower()
        server = resp.headers.get("Server", "").lower()
        if "cloudflare" in server or "cloudflare" in text:
            return "cloudflare"
        if resp.status_code == 403 or "access denied" in text:
            return "generic"
        return "unknown"
    finally:
        if close_client:
            await client.aclose()

