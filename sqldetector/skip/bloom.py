from __future__ import annotations

"""Persistent Bloom filter for skipping safe inputs."""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict


class PersistentBloom:
    def __init__(self, bits: int, ttl_hours: int, path: Path | None = None) -> None:
        self.bits = bits
        self.ttl = ttl_hours * 3600
        self.path = path or Path("cache/skip.bloom")
        self.meta_path = self.path.with_suffix(".json")
        self.bytes = bits // 8
        self.array = bytearray(self.bytes)
        self.timestamps: Dict[str, float] = {}
        self._load()

    # --------------------------------------------------------------
    def _hashes(self, key: str) -> tuple[int, int]:
        h = hashlib.sha1(key.encode("utf8")).digest()
        h1 = int.from_bytes(h[:8], "big") % self.bits
        h2 = int.from_bytes(h[8:16], "big") % self.bits
        return h1, h2

    def add(self, key: str) -> None:
        for idx in self._hashes(key):
            self.array[idx // 8] |= 1 << (idx % 8)
        self.timestamps[key] = time.time()

    def __contains__(self, key: str) -> bool:
        for idx in self._hashes(key):
            if not (self.array[idx // 8] & (1 << (idx % 8))):
                return False
        ts = self.timestamps.get(key)
        if not ts:
            return False
        return time.time() - ts < self.ttl

    # --------------------------------------------------------------
    def _load(self) -> None:
        try:
            with open(self.path, "rb") as f:
                data = f.read()
                if len(data) == self.bytes:
                    self.array = bytearray(data)
            with open(self.meta_path, "r", encoding="utf8") as f:
                self.timestamps = json.load(f)
        except Exception:
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "wb") as f:
                f.write(self.array)
            with open(self.meta_path, "w", encoding="utf8") as f:
                json.dump(self.timestamps, f)
        except Exception:
            pass
