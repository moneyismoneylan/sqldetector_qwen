from __future__ import annotations

"""Helpers for partial HTTP fetches."""

import httpx


async def probe_range(session: httpx.AsyncClient, url: str, kb: int):
    """Fetch up to ``kb`` kilobytes from ``url``.

    A ``HEAD`` request is issued first to check for ``Accept-Ranges`` support
    and to obtain the full size.  If the body is larger than ``kb`` kilobytes a
    ranged ``GET`` is performed.  Otherwise the function falls back to a normal
    ``GET``.
    """

    if kb <= 0:
        resp = await session.get(url)
        return resp.content, resp.headers

    head = await session.head(url)
    if head.headers.get("accept-ranges") and head.headers.get("content-length"):
        size = int(head.headers["content-length"])
        if size > kb * 1024:
            headers = {"Range": f"bytes=0-{kb * 1024 - 1}"}
            resp = await session.get(url, headers=headers)
            return resp.content, resp.headers
    resp = await session.get(url)
    return resp.content, resp.headers
