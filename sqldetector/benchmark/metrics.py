"""Benchmark metrics container."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkMetrics:
    qps: float
    latency_ms: float
    coverage: float
    tpr: float
    fpr: float
