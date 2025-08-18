import asyncio

import httpx
import pytest
from typing import Any

from sqldetector.core.config import Settings
from sqldetector.core.errors import RetryBudgetExceeded, WAFBlocked
from sqldetector.core.http_async import HttpClient


@pytest.mark.asyncio
async def test_retry_succeeds():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(500)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    settings = Settings(legal_ack=True, transport=transport)
    async with HttpClient(settings) as client:
        resp = await client.get("http://test/")
        assert resp.status_code == 200
        assert attempts == 3


@pytest.mark.asyncio
async def test_retry_budget_exceeded():
    def handler(request):
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    settings = Settings(legal_ack=True, transport=transport, retry_budget=2)
    async with HttpClient(settings) as client:
        with pytest.raises(RetryBudgetExceeded):
            await client.get("http://test/")


@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    settings = Settings(legal_ack=True, transport=transport, retry_budget=10)
    async with HttpClient(settings) as client:
        with pytest.raises(WAFBlocked):
            await client.get("http://test/")
        with pytest.raises(WAFBlocked):
            await client.get("http://test/")
    assert calls >= 3


@pytest.mark.asyncio
async def test_hedged_request_returns_fastest():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(0.2)
            return httpx.Response(200, text="slow")
        await asyncio.sleep(0.05)
        return httpx.Response(200, text="fast")

    transport = httpx.MockTransport(handler)
    settings = Settings(legal_ack=True, transport=transport, hedge_delay=0.05)
    async with HttpClient(settings) as client:
        resp = await client.get("http://test/")
        assert resp.text == "fast"
    assert calls >= 2


@pytest.mark.asyncio
async def test_client_configures_timeouts_and_limits(monkeypatch):
    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def request(self, *args, **kwargs):
            return httpx.Response(200)

        async def aclose(self):
            pass

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    settings = Settings(
        legal_ack=True,
        timeout_connect=1,
        timeout_read=2,
        timeout_write=3,
        timeout_pool=4,
        max_connections=10,
        max_keepalive_connections=5,
    )
    async with HttpClient(settings):
        pass
    timeout = captured["timeout"]
    limits = captured["limits"]
    assert timeout.connect == 1
    assert timeout.read == 2
    assert timeout.write == 3
    assert timeout.pool == 4
    assert limits.max_connections == 10
    assert limits.max_keepalive_connections == 5
