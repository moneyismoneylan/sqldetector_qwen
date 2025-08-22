"""Delayed/second-order SQL injection detector."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

MARKER = "/*ELIFNAZ*/"


@dataclass
class SecondOrderTracker:
    pending: Dict[str, Set[str]] = field(default_factory=dict)

    def inject_marker(self, payload: str, marker: str = MARKER) -> str:
        return f"{payload}{marker}"

    def queue(self, url: str, marker: str = MARKER) -> None:
        self.pending.setdefault(marker, set()).add(url)

    def check(self, url: str, body: str) -> bool:
        for marker, urls in list(self.pending.items()):
            if marker in body and url in urls:
                urls.remove(url)
                return True
        return False


__all__ = ["SecondOrderTracker", "MARKER"]
