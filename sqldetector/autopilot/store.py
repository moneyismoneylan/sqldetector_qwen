"""Simple JSON based persistence for AutoPilot decisions."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STORE_PATH = Path(__file__).resolve().parent.parent / "cache" / "autopilot_store.json"


def _load_store() -> Dict[str, Any]:
    try:
        with STORE_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # pragma: no cover - no store yet
        return {}


def _save_store(store: Dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(store, fh, indent=2, sort_keys=True)


def load(domain: str) -> Dict[str, Any]:
    """Return cached profile for ``domain`` if present."""
    store = _load_store()
    return store.get(domain, {})


def save(domain: str, profile: Dict[str, Any], preset: str) -> None:
    """Persist profile and preset selection for ``domain``."""
    store = _load_store()
    store[domain] = {
        "last_profile": profile,
        "chosen_preset": preset,
        "ts": time.time(),
    }
    _save_store(store)
