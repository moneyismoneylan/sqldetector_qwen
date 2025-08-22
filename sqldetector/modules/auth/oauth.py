"""OAuth/OIDC flow loader stub."""
import json
from pathlib import Path
from typing import Dict, Any

def load(flow_path: str) -> Dict[str, Any]:
    """Load flow description from JSON file."""
    return json.loads(Path(flow_path).read_text())
