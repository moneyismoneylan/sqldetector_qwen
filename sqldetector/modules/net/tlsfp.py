"""TLS/JA3 fingerprint selection helper."""
from typing import Any


def setup(mode: str = "auto") -> Any:
    """Return a token representing the selected fingerprint strategy."""
    if mode not in {"auto", "browser", "default"}:
        mode = "default"
    return mode
