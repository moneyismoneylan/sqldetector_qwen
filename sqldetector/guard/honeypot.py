"""Honeypot/tarpit detector."""

from __future__ import annotations

from typing import Dict

THRESHOLD_SEC = 5.0


class HoneypotGuard:
    def __init__(self) -> None:
        self.latencies: Dict[str, float] = {}
        self.blacklist: set[str] = set()

    def record(self, url: str, latency: float) -> None:
        self.latencies[url] = latency
        if latency > THRESHOLD_SEC:
            self.blacklist.add(url)

    def is_blacklisted(self, url: str) -> bool:
        return url in self.blacklist


__all__ = ["HoneypotGuard", "THRESHOLD_SEC"]
