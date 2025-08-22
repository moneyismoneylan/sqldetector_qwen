"""Rate limit intelligence helpers."""
from typing import Dict


def learn(headers: Dict[str, str]) -> int:
    """Derive a safe requests-per-second window from HTTP headers."""
    if "Retry-After" in headers:
        try:
            return max(1, int(1 / int(headers["Retry-After"])))
        except Exception:
            return 1
    if "X-RateLimit-Limit" in headers:
        try:
            return max(1, int(headers["X-RateLimit-Limit"]))
        except Exception:
            return 1
    return 1
