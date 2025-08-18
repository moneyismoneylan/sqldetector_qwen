"""Content and DOM proximity filtering utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5
from typing import Set


@dataclass
class ProximityFilter:
    """Simple deduplication helper based on content hashes."""

    seen: Set[str] = field(default_factory=set)

    @staticmethod
    def normalize_url(url: str) -> str:
        return url.rstrip("/")

    def is_duplicate(self, url: str, content: str) -> bool:
        key = md5((self.normalize_url(url) + content).encode()).hexdigest()
        if key in self.seen:
            return True
        self.seen.add(key)
        return False
