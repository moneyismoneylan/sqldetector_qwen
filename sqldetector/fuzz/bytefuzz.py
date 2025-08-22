"""Byte-level fuzz payload generator."""

from __future__ import annotations

from typing import List

BOUNDARY_BYTES = [
    b"\x00",
    b"\xc0\x80",
    b"\xed\xa0\x80",
    b"%c0%af",
]


def generate_payloads() -> List[bytes]:
    return BOUNDARY_BYTES.copy()


__all__ = ["generate_payloads", "BOUNDARY_BYTES"]
