"""Tiny Bloom filter used for payload deduplication."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BloomFilter:
    size: int = 1024
    hashes: int = 3

    def __post_init__(self) -> None:
        self._bits = bytearray(self.size // 8 + 1)

    def _hashes(self, item: str):
        h1 = hash(item)
        h2 = hash(item[::-1])
        for i in range(self.hashes):
            yield (h1 + i * h2) % self.size

    def _get(self, idx: int) -> bool:
        return bool(self._bits[idx // 8] & (1 << (idx % 8)))

    def _set(self, idx: int) -> None:
        self._bits[idx // 8] |= 1 << (idx % 8)

    def add(self, item: str) -> bool:
        """Add ``item`` to the filter and return True if it was probably present."""
        seen = True
        for idx in self._hashes(item):
            if not self._get(idx):
                seen = False
                self._set(idx)
        return seen
