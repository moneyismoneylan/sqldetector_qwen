from __future__ import annotations

"""Connection pre-warmer for HTTP/2 clients."""

import asyncio
from typing import Iterable

import httpx


async def prewarm_connections(hosts: Iterable[str], client: httpx.AsyncClient) -> None:
    """Open idle connections to ``hosts`` using the provided client.

    Errors are suppressed – the goal is simply to populate the connection pool
    for targets that are likely to be requested shortly afterwards.
    """

    tasks = []
    for host in hosts:
        url = host if host.startswith("http") else f"https://{host}"
        tasks.append(client.get(url, timeout=1.0))
    await asyncio.gather(*tasks, return_exceptions=True)
