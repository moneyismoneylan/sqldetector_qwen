"""WAF normalization learner stub."""
from typing import Callable, Dict


def learn(send: Callable[[str], str]) -> Dict[str, str]:
    """Send a few canary payloads and record how they are normalized."""
    probes = ["1+1", "1%2b1", "1/**/1"]
    matrix: Dict[str, str] = {}
    for p in probes:
        try:
            matrix[p] = send(p)
        except Exception:
            matrix[p] = ""
    return matrix
