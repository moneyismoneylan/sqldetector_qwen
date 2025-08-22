from __future__ import annotations

"""Self-tuning token bucket pacer based on CPU utilisation."""

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


class CPUPacer:
    def __init__(self, target_pct: int, min_rps: int, max_rps: int) -> None:
        self.target = target_pct
        self.min = min_rps
        self.max = max_rps
        self.rate = max_rps

    async def adjust(self) -> int:
        if psutil is None or self.target <= 0:
            return self.max
        usage = psutil.cpu_percent(interval=None)
        if usage > self.target and self.rate > self.min:
            self.rate = max(self.min, int(self.rate * 0.9))
        elif usage < self.target and self.rate < self.max:
            self.rate = min(self.max, int(self.rate * 1.1))
        return self.rate
