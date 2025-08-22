"""Timing sampler using A/B/A' measurements."""

from __future__ import annotations

import statistics
from typing import Callable, List


def sample(ping: Callable[[], float]) -> float:
    samples: List[float] = [ping(), ping(), ping()]
    return statistics.median(samples)


__all__ = ["sample"]
