"""ETag aware crawl helper."""
from typing import Dict, Optional

class ETagCache:
    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}

    def should_fetch(self, url: str, etag: Optional[str]) -> bool:
        if not etag:
            return True
        prev = self._cache.get(url)
        self._cache[url] = etag
        return prev != etag
