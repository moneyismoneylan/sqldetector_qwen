"""Per-route timing calibration stub."""
from statistics import median
from typing import List

def threshold(samples: List[float]) -> float:
    if not samples:
        return 0.0
    return median(samples) * 1.5
