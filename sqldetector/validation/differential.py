"""Differential and statistical response validation utilities."""
from __future__ import annotations

import statistics
from typing import Iterable


def significant_timing_delta(a: Iterable[float], b: Iterable[float], threshold: float = 0.05) -> bool:
    """Return True if the mean timing delta exceeds ``threshold`` seconds."""

    mean_a = statistics.mean(list(a))
    mean_b = statistics.mean(list(b))
    return abs(mean_a - mean_b) > threshold
