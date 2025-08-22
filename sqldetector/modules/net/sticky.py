"""Sticky session helper."""
from typing import Dict, Optional


class StickySession:
    def __init__(self) -> None:
        self.cookie: Optional[str] = None

    def update(self, headers: Dict[str, str]) -> None:
        self.cookie = headers.get("set-cookie", self.cookie)

    def headers(self) -> Dict[str, str]:
        return {"Cookie": self.cookie} if self.cookie else {}
