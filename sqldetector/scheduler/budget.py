from __future__ import annotations

"""Per-endpoint time budget enforcement."""

import time
from contextlib import contextmanager
from typing import Dict


class EndpointBudget:
    def __init__(self, budget_ms: int) -> None:
        self.budget_ms = budget_ms
        self.start: Dict[str, float] = {}

    @contextmanager
    def guard(self, endpoint: str):
        if self.budget_ms <= 0:
            yield
            return
        start = self.start.setdefault(endpoint, time.monotonic())
        if (time.monotonic() - start) * 1000 > self.budget_ms:
            raise TimeoutError(f"budget exceeded for {endpoint}")
        yield
