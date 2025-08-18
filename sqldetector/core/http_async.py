from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from typing import Any, Dict, Optional

import httpx

from .errors import RetryBudgetExceeded, TimeoutError, WAFBlocked
from .config import Settings


class HttpClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None
        self._semaphores: Dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(settings.concurrency)
        )
        self._tokens = float(settings.rate_limit)
        self._last_refill = time.monotonic()
        self._retry_budget = settings.retry_budget
        self._failures = 0
        self._circuit_open_until = 0.0

    async def __aenter__(self) -> "HttpClient":
        self._client = httpx.AsyncClient(http2=True, transport=self.settings.transport)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        if self._client:
            await self._client.aclose()

    async def _acquire(self, url: str) -> asyncio.Semaphore:
        host = httpx.URL(url).host or ""
        sem = self._semaphores[host]
        await sem.acquire()
        return sem

    async def _rate_limit(self) -> None:
        now = time.monotonic()
        rate = float(self.settings.rate_limit)
        capacity = rate
        self._tokens = min(capacity, self._tokens + rate * (now - self._last_refill))
        self._last_refill = now
        if self._tokens < 1:
            await asyncio.sleep((1 - self._tokens) / rate)
            self._tokens = 0
        self._tokens -= 1

    async def _request_once(self, method: str, url: str, **kwargs) -> httpx.Response:
        await self._rate_limit()
        sem = await self._acquire(url)
        try:
            assert self._client is not None
            return await self._client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:  # pragma: no cover - exercised in tests
            raise TimeoutError(str(exc)) from exc
        finally:
            sem.release()

    async def _request_with_retries(self, method: str, url: str, **kwargs) -> httpx.Response:
        attempt = 0
        while True:
            if self._retry_budget <= 0:
                raise RetryBudgetExceeded("retry budget exhausted")
            self._retry_budget -= 1
            resp = await self._request_once(method, url, **kwargs)
            if resp.status_code >= 500:
                self._failures += 1
                if self._failures >= 3:
                    self._circuit_open_until = time.monotonic() + 1.0
                    raise WAFBlocked("circuit open")
                backoff = min(1, 0.1 * (2**attempt)) + random.random() * 0.05
                attempt += 1
                await asyncio.sleep(backoff)
                continue
            self._failures = 0
            return resp

    async def _hedged_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        first = asyncio.create_task(self._request_with_retries(method, url, **kwargs))
        await asyncio.sleep(self.settings.hedge_delay)
        second = asyncio.create_task(self._request_with_retries(method, url, **kwargs))
        done, pending = await asyncio.wait({first, second}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        return list(done)[0].result()

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if time.monotonic() < self._circuit_open_until:
            raise WAFBlocked("circuit open")
        if self.settings.hedge_delay > 0:
            return await self._hedged_request(method, url, **kwargs)
        return await self._request_with_retries(method, url, **kwargs)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)
