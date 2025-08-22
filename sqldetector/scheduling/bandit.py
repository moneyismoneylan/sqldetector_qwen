from __future__ import annotations

"""Simple multi-armed bandit scheduler with persistence.

The scheduler keeps statistics for each payload *family* scoped by
``(host, endpoint)``.  Two algorithms are available:

* ``ucb1`` – deterministic Upper Confidence Bound implementation
* ``thompson`` – Thompson sampling using Beta distributions

State is kept in memory and periodically written to ``cache/bandit.json``.
The file is best-effort and ignored on errors which keeps the feature
optional and lightweight.
"""

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Tuple

CACHE_PATH = Path("cache/bandit.json")


@dataclass
class ArmStats:
    pulls: int = 0
    reward: float = 0.0
    alpha: float = 1.0  # Thompson prior parameters
    beta: float = 1.0

    def avg(self) -> float:
        return self.reward / self.pulls if self.pulls else 0.0


@dataclass
class BanditScheduler:
    algo: str = "ucb1"
    state: Dict[Tuple[str, str, str], ArmStats] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # persistence helpers
    def load(self) -> None:
        try:
            with open(CACHE_PATH, "r", encoding="utf8") as f:
                data = json.load(f)
            for key, vals in data.items():
                host, endpoint, family = key.split("\u0000")
                self.state[(host, endpoint, family)] = ArmStats(*vals)
        except Exception:
            pass

    def save(self) -> None:
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "\u0000".join(k): [v.pulls, v.reward, v.alpha, v.beta]
                for k, v in self.state.items()
            }
            with open(CACHE_PATH, "w", encoding="utf8") as f:
                json.dump(data, f)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _key(self, host: str, endpoint: str, family: str) -> Tuple[str, str, str]:
        return host, endpoint, family

    def _stats(self, host: str, endpoint: str, family: str) -> ArmStats:
        key = self._key(host, endpoint, family)
        if key not in self.state:
            self.state[key] = ArmStats()
        return self.state[key]

    # ------------------------------------------------------------------
    def select(self, host: str, endpoint: str, families: Iterable[str]) -> str:
        families = list(families)
        if not families:
            raise ValueError("families list must not be empty")

        # ensure state
        for fam in families:
            self._stats(host, endpoint, fam)

        if self.algo == "thompson":
            best = None
            best_val = -1.0
            for fam in families:
                st = self._stats(host, endpoint, fam)
                val = random.betavariate(st.alpha, st.beta)
                if val > best_val:
                    best_val = val
                    best = fam
            return best if best is not None else families[0]

        # default UCB1
        total_pulls = sum(self._stats(host, endpoint, fam).pulls for fam in families) + 1
        # Try each arm once first
        for fam in families:
            st = self._stats(host, endpoint, fam)
            if st.pulls == 0:
                return fam
        scores = {}
        for fam in families:
            st = self._stats(host, endpoint, fam)
            bonus = math.sqrt(2 * math.log(total_pulls) / st.pulls)
            scores[fam] = st.avg() + bonus
        return max(scores, key=scores.get)

    def update(self, host: str, endpoint: str, family: str, reward: float) -> None:
        st = self._stats(host, endpoint, family)
        st.pulls += 1
        st.reward += reward
        st.alpha += reward
        st.beta += max(0.0, 1 - reward)
