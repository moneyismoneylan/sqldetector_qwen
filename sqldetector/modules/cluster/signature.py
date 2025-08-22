"""Response signature clustering stub."""
from typing import Dict, List, Any

def cluster(signatures: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for sig in signatures:
        key = (sig.get("status"), len(sig.get("body", "")))
        groups.setdefault(key, []).append(sig)
    return list(groups.values())
