"""AutoPilot helpers for sqldetector.

This package contains light-weight modules used by the AutoPilot
feature. Each module is designed to degrade gracefully when optional
runtime dependencies are missing.
"""

__all__ = [
    "selector",
    "policy",
    "system",
    "store",
    "probes",
]
