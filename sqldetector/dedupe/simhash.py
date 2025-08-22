from __future__ import annotations

"""Simple 64‑bit SimHash implementation used for near‑duplicate detection."""

import hashlib
import re
from typing import Iterable

try:  # optional dependency
    from simhash import Simhash  # type: ignore
except Exception:  # pragma: no cover
    Simhash = None  # type: ignore


_strip_tags = re.compile(r"<[^>]+>")
_collapse_ws = re.compile(r"\s+")


def _normalize(text: str) -> str:
    text = _strip_tags.sub(" ", text)
    text = text.lower()
    text = _collapse_ws.sub(" ", text).strip()
    return text


def _token_hash(token: str) -> int:
    h = hashlib.sha1(token.encode("utf8")).digest()[:8]
    return int.from_bytes(h, "big")


def simhash64(text: str) -> int:
    """Return a 64‑bit simhash for ``text``.

    If the ``simhash`` library is installed it is used; otherwise a very small
    local implementation based on 4‑character shingles is executed.  The result
    is always a 64‑bit integer.
    """

    norm = _normalize(text)
    if Simhash is not None:  # pragma: no cover - exercised when library present
        return Simhash(norm).value & ((1 << 64) - 1)

    weights = [0] * 64
    if len(norm) < 3:
        features = [norm]
    else:
        features = [norm[i : i + 3] for i in range(len(norm) - 2)]
    for feat in features:
        h = _token_hash(feat)
        for i in range(64):
            if (h >> i) & 1:
                weights[i] += 1
            else:
                weights[i] -= 1
    fp = 0
    for i, w in enumerate(weights):
        if w > 0:
            fp |= 1 << i
    return fp


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def is_near_duplicate(h1: int, h2: int, threshold: int) -> bool:
    return hamming_distance(h1, h2) <= threshold
