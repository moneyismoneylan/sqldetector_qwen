"""Online optimizer for multi-objective scheduling."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FamilyStats:
    positives: int = 0
    tests: int = 0
    total_cost_ms: float = 0.0

    @property
    def avg_cost(self) -> float:
        if self.tests == 0:
            return 0.0
        return self.total_cost_ms / self.tests

    @property
    def positives_per_hour(self) -> float:
        hours = self.total_cost_ms / 1000.0 / 3600.0
        if hours == 0:
            return 0.0
        return self.positives / hours

    def update(self, positive: bool, cost_ms: float) -> None:
        self.tests += 1
        if positive:
            self.positives += 1
        self.total_cost_ms += cost_ms


class OnlineOptimizer:
    """Simple UCB1/Thompson hybrid optimizer."""

    def __init__(self) -> None:
        self.stats: Dict[str, FamilyStats] = {}
        self.total_tests = 0

    def record(self, family: str, positive: bool, cost_ms: float) -> None:
        stat = self.stats.setdefault(family, FamilyStats())
        stat.update(positive, cost_ms)
        self.total_tests += 1

    def _ucb(self, family: str, stat: FamilyStats) -> float:
        if stat.tests == 0:
            return float("inf")
        avg_reward = stat.positives_per_hour or 0.0
        bonus = math.sqrt(2 * math.log(self.total_tests + 1) / stat.tests)
        if stat.avg_cost == 0:
            return avg_reward + bonus
        return avg_reward / stat.avg_cost + bonus

    def decide_next_families(self, budget_ms: float) -> List[str]:
        scored = []
        for family, stat in self.stats.items():
            if stat.avg_cost and stat.avg_cost > budget_ms:
                continue
            score = self._ucb(family, stat)
            scored.append((score, family))
        scored.sort(reverse=True)
        return [f for _s, f in scored]


__all__ = ["OnlineOptimizer", "FamilyStats"]
