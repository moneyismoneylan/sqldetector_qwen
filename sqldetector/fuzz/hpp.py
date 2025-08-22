"""HTTP parameter pollution helper."""

from __future__ import annotations

from typing import List, Tuple


def generate_variants(param: str, value: str) -> List[Tuple[str, List[str]]]:
    return [
        (param, [value, value]),
        (f"{param}[]", [value, value]),
    ]


def detect_difference(baseline: str, polluted: str) -> bool:
    return baseline != polluted


__all__ = ["generate_variants", "detect_difference"]
