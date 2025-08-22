from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Event:
    ts: float
    mode: str
    reason: str


@dataclass
class AdaptiveEngine:
    """Generic WAF-aware pacing engine."""

    level: str = "observe"
    mode: str = "fast"
    timeline: List[Event] = field(default_factory=list)

    def _log(self, reason: str) -> None:
        self.timeline.append(Event(time.time(), self.mode, reason))

    def observe(self, resp: Dict[str, any]) -> str:
        """Inspect a response and adjust mode if necessary."""
        status = resp.get("status")
        headers = {k.lower(): v for k, v in resp.get("headers", {}).items()}
        if self.level == "off":
            return self.mode
        if status in (403, 429) or "cf-ray" in headers:
            if self.level in ("stealth", "aggressive"):
                if self.mode != "stealth":
                    self.mode = "stealth"
                    self._log(f"downshift:{status}")
        elif self.mode == "stealth" and status and status < 400:
            # recover after a successful response
            self.mode = "fast"
            self._log("recover")
        return self.mode
