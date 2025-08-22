from __future__ import annotations

"""Lightweight async DNS resolver with in-memory + on-disk cache."""

import asyncio
import json
import socket
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

CACHE_PATH = Path("cache/dns.json")

try:  # optional dependency
    import aiodns  # type: ignore
except Exception:  # pragma: no cover
    aiodns = None


class DNSCache:
    def __init__(self, ttl: int = 900) -> None:
        self.ttl = ttl
        self.cache: Dict[str, Tuple[float, List[str]]] = {}
        self._load()

    # --------------------------------------------------------------
    def _load(self) -> None:
        try:
            with open(CACHE_PATH, "r", encoding="utf8") as f:
                data = json.load(f)
            now = time.time()
            for host, (ts, addrs) in data.items():
                if now - ts < self.ttl:
                    self.cache[host] = (ts, addrs)
        except Exception:
            pass

    def _save(self) -> None:
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf8") as f:
                json.dump(self.cache, f)
        except Exception:
            pass

    # --------------------------------------------------------------
    async def resolve(self, host: str) -> List[str]:
        now = time.time()
        if host in self.cache and now - self.cache[host][0] < self.ttl:
            return list(self.cache[host][1])

        addrs: List[str] = []
        if aiodns is not None:
            resolver = aiodns.DNSResolver()
            try:
                result = await resolver.query(host, "A")
                addrs = [r.host for r in result]
            except Exception:
                pass
        if not addrs:
            loop = asyncio.get_event_loop()
            try:
                infos = await loop.getaddrinfo(host, None)
                addrs = [info[4][0] for info in infos]
            except socket.gaierror:
                addrs = []
        self.cache[host] = (now, addrs)
        self._save()
        return addrs

    # synchronous fallback for libraries expecting getaddrinfo
    @lru_cache(maxsize=256)
    def getaddrinfo(self, host: str, port: int):  # pragma: no cover - trivial
        return socket.getaddrinfo(host, port)
