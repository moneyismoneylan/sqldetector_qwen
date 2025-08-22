"""Adaptive header mutator."""

from __future__ import annotations

from typing import Dict, List

CANDIDATE_HEADERS = [
    {"Accept": "*/*"},
    {"Content-Type": "application/json"},
    {"X-Requested-With": "XMLHttpRequest"},
    {"Prefer": "respond-async"},
]


def explore() -> List[Dict[str, str]]:
    return CANDIDATE_HEADERS.copy()


__all__ = ["explore", "CANDIDATE_HEADERS"]
