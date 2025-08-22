from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Step:
    url: str
    params: Dict[str, Any]


@dataclass
class StateMachine:
    """Track multi-step flows like login→dashboard."""

    steps: List[Step] = field(default_factory=list)

    def add(self, url: str, params: Dict[str, Any]) -> None:
        self.steps.append(Step(url, params))

    def trace(self) -> List[Dict[str, Any]]:
        return [step.__dict__ for step in self.steps]
