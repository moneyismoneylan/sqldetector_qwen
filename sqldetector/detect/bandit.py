"""Multi-armed bandit strategies for payload selection."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UCB1Planner:
    """Simple implementation of the UCB1 bandit algorithm.

    The planner keeps track of how many times each ``arm`` (payload family) has
    been pulled and the cumulative reward obtained from it.  When selecting the
    next arm, the classic Upper Confidence Bound formula is used which
    automatically balances exploration and exploitation.
    """

    arms: List[str]
    counts: Dict[str, int] = field(init=False)
    rewards: Dict[str, float] = field(init=False)
    total_pulls: int = 0

    def __post_init__(self) -> None:
        self.counts = {arm: 0 for arm in self.arms}
        self.rewards = {arm: 0.0 for arm in self.arms}

    def select_arm(self) -> str:
        """Select the arm with the highest UCB1 score."""

        # Ensure each arm is tried at least once
        for arm, count in self.counts.items():
            if count == 0:
                return arm

        self.total_pulls += 1
        scores = {}
        for arm in self.arms:
            avg_reward = self.rewards[arm] / self.counts[arm]
            bonus = math.sqrt(2 * math.log(self.total_pulls) / self.counts[arm])
            scores[arm] = avg_reward + bonus
        return max(scores, key=scores.get)

    def update(self, arm: str, reward: float) -> None:
        """Update statistics for ``arm`` with a new reward."""

        self.counts[arm] += 1
        self.rewards[arm] += reward

    def prune(self, min_pulls: int, threshold: float) -> None:
        """Remove arms whose average reward falls below ``threshold``.

        Arms must have been pulled at least ``min_pulls`` times before they are
        considered for pruning.  This provides a simple early stopping
        mechanism to drop ineffective payload families.
        """

        for arm in list(self.arms):
            pulls = self.counts[arm]
            if pulls >= min_pulls:
                avg = self.rewards[arm] / pulls if pulls else 0.0
                if avg < threshold:
                    self.arms.remove(arm)
                    self.counts.pop(arm, None)
                    self.rewards.pop(arm, None)


def select_arm(rewards: List[float]) -> int:
    """Compatibility helper returning the index of the best arm.

    ``rewards`` is interpreted as a list of average rewards; the arm with the
    highest value is returned.  This mirrors a greedy policy and is sufficient
    for small toy examples.
    """

    if not rewards:
        raise ValueError("rewards list must not be empty")
    return max(range(len(rewards)), key=lambda i: rewards[i])
