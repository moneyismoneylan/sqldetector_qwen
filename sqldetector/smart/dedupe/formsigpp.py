import json
from typing import List, Dict


def form_signature(action: str, inputs: List[Dict[str, str]]) -> str:
    """Return a normalised signature for a form."""
    action_norm = action.rstrip("/")
    schema = sorted((inp.get("name"), inp.get("type"), inp.get("path")) for inp in inputs)
    key = (action_norm, tuple(schema))
    return json.dumps(key)
