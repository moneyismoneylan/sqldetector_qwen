"""Cache bypass utilities."""

from __future__ import annotations

import random
from typing import Dict, Tuple


def add_bypass(url: str, headers: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    cb = random.randint(0, 1_000_000)
    sep = "&" if "?" in url else "?"
    new_url = f"{url}{sep}cb={cb}"
    new_headers = dict(headers)
    new_headers.setdefault("Cache-Control", "no-cache")
    new_headers.setdefault("Pragma", "no-cache")
    return new_url, new_headers


__all__ = ["add_bypass"]
