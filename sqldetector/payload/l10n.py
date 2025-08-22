"""Locale-aware payload helpers."""

from __future__ import annotations

from datetime import datetime
from typing import List


def numeric_variants(num: int, locale: str) -> List[str]:
    variants = [str(num)]
    if locale.startswith("tr"):
        variants.append(f"{num:,}".replace(",", "."))
    elif locale.startswith("en"):
        variants.append(f"{num:,}")
    return variants


def date_variants(dt: datetime, locale: str) -> List[str]:
    if locale.startswith("tr"):
        return [dt.strftime("%d.%m.%Y")]
    return [dt.strftime("%Y-%m-%d")]


__all__ = ["numeric_variants", "date_variants"]
