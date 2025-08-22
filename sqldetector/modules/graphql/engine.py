"""Minimal GraphQL fuzzing stub.

The real project would perform introspection and structured injection.  For the
purposes of tests this module only exposes a ``fuzz`` function that echoes the
input query while preserving JSON types.
"""
from __future__ import annotations

from typing import Any, Dict


def fuzz(query: Dict[str, Any]) -> Dict[str, Any]:
    """Return the query back to caller; placeholder for real fuzzing."""
    return {"sent": query, "issues": []}
