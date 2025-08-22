import json
from pathlib import Path
from typing import List, Dict, Any

def load(path: str) -> List[Dict[str, Any]]:
    """Extract request targets from a HAR file."""
    data = json.loads(Path(path).read_text())
    entries = data.get("log", {}).get("entries", [])
    results: List[Dict[str, Any]] = []
    for e in entries:
        req = e.get("request", {})
        results.append({"method": req.get("method", "GET"), "url": req.get("url")})
    return results
