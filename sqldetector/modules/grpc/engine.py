"""Tiny gRPC fuzz engine placeholder."""
from typing import Any, Dict


def fuzz(method: str, message: Dict[str, Any]) -> Dict[str, Any]:
    return {"method": method, "message": message, "issues": []}
