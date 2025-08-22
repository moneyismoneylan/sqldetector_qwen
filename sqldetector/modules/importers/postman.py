import json
from pathlib import Path
from typing import List, Dict, Any

def load(path: str) -> List[Dict[str, Any]]:
    """Load endpoints from a minimal Postman collection JSON file."""
    data = json.loads(Path(path).read_text())
    results: List[Dict[str, Any]] = []

    def _walk(items: List[Dict[str, Any]]) -> None:
        for item in items:
            req = item.get("request")
            if req:
                url = req.get("url")
                raw = url.get("raw") if isinstance(url, dict) else url
                results.append({"method": req.get("method", "GET").upper(), "url": raw})
            if "item" in item:
                _walk(item["item"])

    _walk(data.get("item", []))
    return results
