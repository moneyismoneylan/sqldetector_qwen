"""Micro runner for low-spec environments."""

from __future__ import annotations

from typing import Any, Dict, List


async def run_micro(seed_url: str, cfg: Dict[str, Any]) -> List[dict]:  # pragma: no cover
    try:
        import httpx  # type: ignore
    except Exception:
        return [{"url": seed_url, "error": "httpx missing"}]

    async with httpx.AsyncClient(timeout=cfg.get("timeout_read", 5)) as client:
        try:
            resp = await client.get(seed_url)
            return [{"url": seed_url, "status": resp.status_code}]
        except Exception:
            return [{"url": seed_url, "error": "request failed"}]


__all__ = ["run_micro"]
