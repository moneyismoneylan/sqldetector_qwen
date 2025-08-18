"""Adaptive attack planner using a simple multi-armed bandit model."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AdaptivePlanner:
    arms: List[str]
    epsilon: float = 0.1
    counts: Dict[str, int] = field(init=False)
    rewards: Dict[str, float] = field(init=False)

    def __post_init__(self) -> None:
        self.counts = {arm: 0 for arm in self.arms}
        self.rewards = {arm: 0.0 for arm in self.arms}

    def select_arm(self) -> str:
        """Select an arm using epsilon-greedy strategy."""
        if random.random() < self.epsilon:
            return random.choice(self.arms)
        return max(
            self.arms,
            key=lambda a: (self.rewards[a] / self.counts[a]) if self.counts[a] else 0.0,
        )

    def update(self, arm: str, reward: float) -> None:
        self.counts[arm] += 1
        self.rewards[arm] += reward
