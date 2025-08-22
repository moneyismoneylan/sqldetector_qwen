"""Accept-Language sharding helpers."""

from __future__ import annotations

from typing import List


def rotate(locales: List[str]) -> List[dict]:
    return [{"Accept-Language": loc} for loc in locales]


__all__ = ["rotate"]
