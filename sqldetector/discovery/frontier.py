"""Priority frontier queue for crawl targets."""

from __future__ import annotations

from heapq import heappush, heappop
from typing import Set, Tuple

from sqldetector.core.config import Settings


class Frontier:
    """Simple priority queue respecting preset weights."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._heap: list[Tuple[int, int, str]] = []
        self._seen: Set[str] = set()
        self._counter = 0

    # --------------------------------------------------------------
    def _priority(self, url: str) -> int:
        u = url.lower()
        if "form" in u:
            return 0
        if "/api" in u:
            return 1
        if u.endswith(".json") or "json" in u:
            return 2
        if u.endswith(".html") or u.endswith("/"):
            return 3
        return 4

    def add(self, url: str) -> None:
        if (self.settings.simhash_enabled or self.settings.bloom_enabled) and url in self._seen:
            return
        self._seen.add(url)
        heappush(self._heap, (self._priority(url), self._counter, url))
        self._counter += 1

    def pop(self) -> str:
        _, _, url = heappop(self._heap)
        return url

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._heap)

