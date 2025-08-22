"""Helpers for loading and applying configuration presets."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib  # type: ignore

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"


def load_preset(name: str) -> Dict[str, Any]:
    """Load a preset TOML file from ``presets/<name>.toml``."""
    path = PRESETS_DIR / f"{name}.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


def merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two flat dictionaries, ``override`` taking precedence."""
    merged = dict(base)
    merged.update(override)
    return merged


def apply_system_aware_overrides(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Clamp aggressive settings on low spec machines."""
    cores = 1
    try:
        cores = max(1, (__import__("os").cpu_count() or 1))
    except Exception:  # pragma: no cover
        pass

    ram_gb = None
    if psutil is not None:
        try:
            ram_gb = psutil.virtual_memory().total / (1024**3)
        except Exception:  # pragma: no cover - psutil misbehaving
            ram_gb = None

    if cores <= 4 or (ram_gb is not None and ram_gb <= 8):
        cfg["max_connections"] = min(cfg.get("max_connections", 10), 12)
        cfg["max_keepalive_connections"] = min(cfg.get("max_keepalive_connections", 4), 4)
        cfg["timeout_connect"] = cfg.get("timeout_connect", 3.0)
        cfg["timeout_read"] = cfg.get("timeout_read", 6.0)
        cfg["timeout_write"] = cfg.get("timeout_write", 6.0)
        cfg["timeout_pool"] = cfg.get("timeout_pool", 3.0)
    return cfg
