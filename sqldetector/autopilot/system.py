"""System capability detection and configuration tuning."""
from __future__ import annotations

from typing import Any, Dict

import os

try:  # optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover - psutil missing
    psutil = None


def detect_system() -> Dict[str, int]:
    """Return a very small set of system characteristics."""
    cores = os.cpu_count() or 1
    ram_gb = 0
    if psutil is not None:
        try:
            ram_gb = int(psutil.virtual_memory().total / (1024 ** 3))
        except Exception:  # pragma: no cover
            ram_gb = 0
    return {"cores": int(cores), "ram_gb": int(ram_gb)}


def tune_by_system(cfg: Dict[str, Any], sysinfo: Dict[str, int], rtt_ms: Any) -> Dict[str, Any]:
    """Clamp aggressive settings based on system capabilities and RTT."""
    cfg = dict(cfg)
    cores = sysinfo.get("cores", 1)
    ram = sysinfo.get("ram_gb", 0)

    if cores <= 2 or ram <= 4:
        cfg["max_connections"] = min(cfg.get("max_connections", 10), 8)
        cfg["max_keepalive_connections"] = min(cfg.get("max_keepalive_connections", 4), 4)
        cfg["timeout_connect"] = min(cfg.get("timeout_connect", 5.0), 5.0)
        cfg["timeout_read"] = min(cfg.get("timeout_read", 10.0), 10.0)
    if rtt_ms and rtt_ms > 1000:
        # High latency -> enable hedging
        cfg.setdefault("hedge_enabled", True)
        cfg.setdefault("hedge_delay_ms", 200)
    return cfg
