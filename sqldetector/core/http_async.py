from __future__ import annotations

import asyncio
import random
import sys
import time
from collections import defaultdict, deque
from typing import Dict

import httpx
import certifi

try:  # optional ssl trust-store on CPython 3.12+
    if sys.version_info >= (3, 12):  # pragma: no cover - platform specific
        import truststore  # type: ignore
    else:  # pragma: no cover
        truststore = None  # type: ignore
except Exception:  # pragma: no cover - truststore not available
    truststore = None  # type: ignore

from .errors import RetryBudgetExceeded, TimeoutError, WAFBlocked
from .config import Settings


class AdaptiveSemaphore:
    """Semaphore with a dynamically adjustable limit."""

    def __init__(self, value: int):
        self.limit = value
        self._sem = asyncio.Semaphore(value)

    async def acquire(self) -> None:
        await self._sem.acquire()

    def release(self) -> None:
        self._sem.release()

    def adjust(self, value: int) -> None:
        if value > self.limit:
            for _ in range(value - self.limit):
                self._sem.release()
        elif value < self.limit:
            diff = self.limit - value
            # decrease available tokens without blocking
            self._sem._value = max(0, self._sem._value - diff)
        self.limit = value


class HttpClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None
        self._semaphores: Dict[str, AdaptiveSemaphore] = defaultdict(
            lambda: AdaptiveSemaphore(settings.concurrency)
        )
        self._host_latencies: Dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=20))
        self._host_avgs: Dict[str, float] = {}
        self._tokens = float(settings.rate_limit)
        self._last_refill = time.monotonic()
        self._retry_budget = {
            "network": settings.retry_budget,
            "server": settings.retry_budget,
            "timeout": settings.retry_budget,
        }
        self._failures = 0
        self._circuit_open_until = 0.0
        self._latencies: deque[float] = deque(maxlen=50)
        self._hedge_counts: Dict[str, int] = defaultdict(int)
        self._req_counts: Dict[str, int] = defaultdict(int)

    async def __aenter__(self) -> "HttpClient":
        timeout = httpx.Timeout(
            connect=self.settings.timeout_connect,
            read=self.settings.timeout_read,
            write=self.settings.timeout_write,
            pool=self.settings.timeout_pool,
        )
        limits = httpx.Limits(
            max_connections=self.settings.max_connections,
            max_keepalive_connections=self.settings.max_keepalive_connections,
        )
        verify: object
        if truststore:  # pragma: no cover - depends on optional package
            verify = truststore.SSLContext()
        else:
            verify = certifi.where()
        encodings = ["gzip"]
        if self.settings.advanced.get("preset") != "stealth":
            try:  # pragma: no cover - optional dependency
                import brotli  # type: ignore

                encodings.insert(0, "br")
            except Exception:  # pragma: no cover - brotli not installed
                pass
            try:  # pragma: no cover - optional dependency
                import zstandard  # type: ignore

                encodings.append("zstd")
            except Exception:  # pragma: no cover - zstandard not installed
                pass
        headers = {
            "User-Agent": "sqldetector/1.0",
            "Accept-Encoding": ", ".join(encodings),
        }
        transport = self.settings.transport
        if self.settings.http_cache_enabled:
            from .cache_transport import CacheTransport

            transport = CacheTransport(transport)

        self._client = httpx.AsyncClient(
            http2=True,
            transport=transport,
            timeout=timeout,
            limits=limits,
            headers=headers,
            verify=verify,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        if self._client:
            await self._client.aclose()

    async def _acquire(self, url: str) -> tuple[str, AdaptiveSemaphore]:
        host = httpx.URL(url).host or ""
        sem = self._semaphores[host]
        await sem.acquire()
        return host, sem

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
        host, sem = await self._acquire(url)
        try:
            assert self._client is not None
            start = time.monotonic()
            resp = await self._client.request(method, url, **kwargs)
            latency = time.monotonic() - start
            self._latencies.append(latency)
            self._host_latencies[host].append(latency)
            self._adjust_concurrency(host)
            return resp
        except httpx.TimeoutException as exc:  # pragma: no cover - exercised in tests
            raise TimeoutError(str(exc)) from exc
        finally:
            sem.release()

    def _adjust_concurrency(self, host: str) -> None:
        latencies = self._host_latencies[host]
        if len(latencies) < 2:
            return
        avg = sum(latencies) / len(latencies)
        prev = self._host_avgs.get(host, avg)
        self._host_avgs[host] = avg
        sem = self._semaphores[host]
        if avg > prev * 1.2:
            sem.adjust(max(1, sem.limit // 2))
        elif avg < prev * 0.8 and sem.limit < self.settings.concurrency:
            sem.adjust(sem.limit + 1)

    async def _request_with_retries(self, method: str, url: str, **kwargs) -> httpx.Response:
        attempt = 0
        while True:
            try:
                resp = await self._request_once(method, url, **kwargs)
            except TimeoutError:
                if self._retry_budget["timeout"] <= 0:
                    raise RetryBudgetExceeded("timeout retry budget exhausted")
                self._retry_budget["timeout"] -= 1
                backoff = min(1, 0.1 * (2**attempt)) + random.uniform(0.1, 0.3)
                attempt += 1
                await asyncio.sleep(backoff)
                continue
            except httpx.RequestError as exc:
                if self._retry_budget["network"] <= 0:
                    raise RetryBudgetExceeded("network retry budget exhausted") from exc
                self._retry_budget["network"] -= 1
                backoff = min(1, 0.1 * (2**attempt)) + random.uniform(0.1, 0.3)
                attempt += 1
                await asyncio.sleep(backoff)
                continue

            if resp.status_code in (429, 403):
                await asyncio.sleep(1.0)
                continue
            if resp.status_code >= 500:
                if self._retry_budget["server"] <= 0:
                    raise RetryBudgetExceeded("server retry budget exhausted")
                self._retry_budget["server"] -= 1
                self._failures += 1
                if self._failures >= 3:
                    self._circuit_open_until = time.monotonic() + 1.0
                    raise WAFBlocked("circuit open")
                backoff = min(1, 0.1 * (2**attempt)) + random.uniform(0.1, 0.3)
                attempt += 1
                await asyncio.sleep(backoff)
                continue
            self._failures = 0
            return resp

    def _compute_hedge_delay(self) -> float:
        if len(self._latencies) < 5:
            return self.settings.hedge_delay
        latencies = sorted(self._latencies)
        index = int(0.95 * (len(latencies) - 1))
        p95 = latencies[index]
        delay = p95 * 0.2
        return max(0.02, min(0.15, delay))

    async def _hedged_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        first = asyncio.create_task(self._request_with_retries(method, url, **kwargs))
        await asyncio.sleep(self._compute_hedge_delay())
        second = asyncio.create_task(self._request_with_retries(method, url, **kwargs))
        done, pending = await asyncio.wait({first, second}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        return list(done)[0].result()

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if time.monotonic() < self._circuit_open_until:
            raise WAFBlocked("circuit open")
        host = httpx.URL(url).host or ""
        self._req_counts[host] += 1
        ratio = self._hedge_counts[host] / max(1, self._req_counts[host])
        if (self.settings.hedge_delay > 0 or len(self._latencies) >= 5) and (
            ratio < self.settings.hedge_max_ratio
        ):
            self._hedge_counts[host] += 1
            return await self._hedged_request(method, url, **kwargs)
        return await self._request_with_retries(method, url, **kwargs)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        if self.settings.range_fetch_kb > 0:
            headers = dict(kwargs.get("headers", {}))
            if "Range" not in headers:
                end = self.settings.range_fetch_kb * 1024 - 1
                headers["Range"] = f"bytes=0-{end}"
            kwargs["headers"] = headers
            resp = await self.request("GET", url, **kwargs)
            ctype = resp.headers.get("Content-Type", "").split(";")[0]
            if resp.status_code == 206 and resp.headers.get("Accept-Ranges") and ctype in {
                "text/html",
                "application/json",
                "text/xml",
                "application/xml",
            }:
                return resp
            headers.pop("Range", None)
            kwargs["headers"] = headers
            return await self.request("GET", url, **kwargs)
        return await self.request("GET", url, **kwargs)
