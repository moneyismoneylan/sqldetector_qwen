"""Idempotent PoC builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class PoCPair:
    confirm: Tuple[str, str]
    verify: Tuple[str, str]


def build_pair(url: str, payload: str) -> PoCPair:
    confirm = ("POST", url)
    verify = ("GET", url)
    return PoCPair(confirm, verify)


def invariant(before: str, after: str) -> bool:
    return before == after


__all__ = ["PoCPair", "build_pair", "invariant"]
