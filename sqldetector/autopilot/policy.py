"""Preset selection policies."""
from __future__ import annotations

from typing import Any, Dict

PRESET_MAP = {
    "waf-guarded": "stealth",
    "api-json": "api",
    "spa": "spa",
    "forms-heavy": "forms",
    "static": "fast",
    "admin": "stealth",
    "ecom": "crawler",
    "heavy-site": "turbo",
}


def choose_preset(profile: Dict[str, Any]) -> str:
    """Choose a preset name based on classification profile."""
    kind = profile.get("kind", "fast")
    return PRESET_MAP.get(kind, "fast")


def live_adjustments(profile: Dict[str, Any], runtime_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Suggest live configuration adjustments.

    The returned dictionary may contain a ``preset`` key indicating that
    the run should switch to a different preset.  Implementations are
    intentionally conservative to avoid oscillations.
    """
    adjustments: Dict[str, Any] = {}

    if runtime_metrics.get("waf") or runtime_metrics.get("error_rate", 0) > 0.3:
        adjustments["preset"] = "stealth"
    elif runtime_metrics.get("forms_per_page", 0) > profile.get("forms_per_page", 0) * 2:
        adjustments["preset"] = "forms"

    return adjustments
