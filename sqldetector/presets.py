"""Helpers for loading and applying configuration presets."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib  # type: ignore

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"


def load_preset(name: str) -> Dict[str, Any]:
    """Load a preset TOML file from ``presets/<name>.toml``."""
    path = PRESETS_DIR / f"{name}.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def apply_system_overrides(cfg: Dict[str, Any], sysinfo: Dict[str, int], rtt_ms: Any) -> Dict[str, Any]:
    """Apply system-aware clamps using ``autopilot.system`` heuristics."""
    from .autopilot import system as sysmod

    return sysmod.tune_by_system(cfg, sysinfo, rtt_ms)


# Backwards compatibility ----------------------------------------------------
merge_config = deep_merge


def apply_system_aware_overrides(cfg: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
    from .autopilot.system import detect_system

    return apply_system_overrides(cfg, detect_system(), None)
