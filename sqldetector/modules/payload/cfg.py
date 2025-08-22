"""Grammar based payload generator stub."""
from typing import List

_GRAMMAR = {
    "generic": ["' OR '1'='1", '" OR 1=1 --'],
    "numeric": ["1 OR 1=1"],
}

def generate(db: str = "generic", limit: int = 5) -> List[str]:
    payloads = _GRAMMAR.get(db, _GRAMMAR["generic"])
    return payloads[:limit]
