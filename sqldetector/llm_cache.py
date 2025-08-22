"""Simple SQLite-backed cache for LLM responses."""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Optional


class LLMCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v BLOB, ts INTEGER)")
        self.conn.commit()

    @staticmethod
    def make_key(host: str, schema: str, payload_family: str, model: str, prompt_ver: str) -> str:
        raw = "|".join([host, schema, payload_family, model, prompt_ver]).encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, key: str, ttl_hours: int | None) -> Optional[bytes]:
        cur = self.conn.execute("SELECT v, ts FROM kv WHERE k=?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        value, ts = row
        if ttl_hours is not None:
            if time.time() - ts > ttl_hours * 3600:
                return None
        return value

    def set(self, key: str, value: bytes) -> None:
        self.conn.execute(
            "REPLACE INTO kv (k, v, ts) VALUES (?, ?, ?)", (key, value, int(time.time()))
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


__all__ = ["LLMCache"]
