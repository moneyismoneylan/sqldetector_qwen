"""Naive CDN detection helpers."""
from typing import Dict

_CDN_HEADERS = {"via", "x-cache", "x-cdn"}

def detect(headers: Dict[str, str]) -> bool:
    return any(h.lower() in _CDN_HEADERS for h in headers)
