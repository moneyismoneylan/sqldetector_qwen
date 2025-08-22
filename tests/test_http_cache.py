import asyncio

import httpx

from sqldetector.core.config import Settings
from sqldetector.core.http_async import HttpClient


def test_http_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            assert "If-None-Match" not in request.headers
            return httpx.Response(200, headers={"ETag": "abc", "Content-Type": "text/plain"}, text="hello")
        assert request.headers.get("If-None-Match") == "abc"
        return httpx.Response(304)

    transport = httpx.MockTransport(handler)
    settings = Settings(http_cache_enabled=True, transport=transport)

    async def run() -> None:
        async with HttpClient(settings) as client:
            r1 = await client.get("http://test/")
            assert r1.text == "hello"
            r2 = await client.get("http://test/")
            assert r2.text == "hello"

    asyncio.run(run())

