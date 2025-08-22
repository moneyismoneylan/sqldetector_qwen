import asyncio

import httpx

from sqldetector.core.config import Settings
from sqldetector.core.http_async import HttpClient


def test_range_fetch_supported():
    calls: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers.get("Range"))
        assert calls[0] is not None
        return httpx.Response(206, headers={"Accept-Ranges": "bytes", "Content-Type": "text/html"}, text="part")

    transport = httpx.MockTransport(handler)
    settings = Settings(range_fetch_kb=1, transport=transport)

    async def run() -> None:
        async with HttpClient(settings) as client:
            resp = await client.get("http://test/")
            assert resp.status_code == 206

    asyncio.run(run())
    assert calls == ["bytes=0-1023"]


def test_range_fetch_fallback():
    calls: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers.get("Range"))
        if len(calls) == 1:
            return httpx.Response(200, headers={"Content-Type": "text/html"}, text="full")
        return httpx.Response(200, headers={"Content-Type": "text/html"}, text="full")

    transport = httpx.MockTransport(handler)
    settings = Settings(range_fetch_kb=1, transport=transport)

    async def run() -> None:
        async with HttpClient(settings) as client:
            resp = await client.get("http://test/")
            assert resp.status_code == 200

    asyncio.run(run())
    assert calls[0] == "bytes=0-1023" and calls[1] is None

