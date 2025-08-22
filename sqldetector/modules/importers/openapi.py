import json
from pathlib import Path
from typing import List, Dict, Any
try:
    from urllib.request import urlopen
except Exception:  # pragma: no cover
    urlopen = None  # type: ignore

def load(source: str) -> List[Dict[str, Any]]:
    """Load minimal endpoints from an OpenAPI JSON file or URL.

    The importer is intentionally tiny but sufficient for offline tests.  Only
    the ``paths`` section is processed and each HTTP method is expanded into an
    entry of ``{"method": method, "url": path}``.
    """
    data: Dict[str, Any]
    path = Path(source)
    if path.exists():
        data = json.loads(path.read_text())
    elif urlopen is not None and source.startswith(("http://", "https://")):
        with urlopen(source) as f:  # pragma: no cover - network optional
            data = json.loads(f.read().decode())
    else:  # pragma: no cover - invalid path
        raise FileNotFoundError(source)
    results: List[Dict[str, Any]] = []
    for p, methods in data.get("paths", {}).items():
        for m in methods:
            results.append({"method": m.upper(), "url": p})
    return results
