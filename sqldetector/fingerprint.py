"""Page fingerprinting helpers for incremental scans."""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import xxhash  # type: ignore
except Exception:  # pragma: no cover - optional
    xxhash = None


class FingerprintDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS fp (url TEXT PRIMARY KEY, etag TEXT, lastmod TEXT, bodysz INTEGER, bodyhash TEXT, updated INTEGER)"
        )
        self.conn.commit()

    def load(self, url: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT etag,lastmod,bodysz,bodyhash,updated FROM fp WHERE url=?", (url,)
        )
        row = cur.fetchone()
        if not row:
            return None
        keys = ["etag", "lastmod", "bodysz", "bodyhash", "updated"]
        return dict(zip(keys, row))

    def store(self, url: str, fp: Dict[str, Any]) -> None:
        self.conn.execute(
            "REPLACE INTO fp (url, etag, lastmod, bodysz, bodyhash, updated) VALUES (?,?,?,?,?,?)",
            (
                url,
                fp.get("etag"),
                fp.get("lastmod"),
                fp.get("bodysz"),
                fp.get("bodyhash"),
                int(time.time()),
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


def _hash_body(body: bytes) -> str:
    slice_ = body[:65536] + body[-65536:]
    if xxhash is not None:
        return xxhash.xxh64_hexdigest(slice_)
    return hashlib.sha256(slice_).hexdigest()


def fingerprint_from_response(resp: Any) -> Dict[str, Any]:
    body = getattr(resp, "content", b"")
    if isinstance(body, str):
        body = body.encode()
    headers = getattr(resp, "headers", {})
    fp = {
        "etag": headers.get("ETag"),
        "lastmod": headers.get("Last-Modified"),
        "bodysz": len(body),
        "bodyhash": _hash_body(body),
    }
    return fp


def should_skip_heavy(
    prev: Optional[Dict[str, Any]], curr: Dict[str, Any], max_age_hours: int = 24
) -> bool:
    if not prev:
        return False
    now = time.time()
    if prev.get("etag") and curr.get("etag") and prev["etag"] == curr["etag"]:
        if now - prev.get("updated", 0) < max_age_hours * 3600:
            return True
    if prev.get("bodyhash") == curr.get("bodyhash"):
        if now - prev.get("updated", 0) < max_age_hours * 3600:
            return True
    return False


__all__ = ["FingerprintDB", "fingerprint_from_response", "should_skip_heavy"]
