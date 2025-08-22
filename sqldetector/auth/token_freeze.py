"""CSRF/anti-bot token capture and refresh helpers."""

from __future__ import annotations

import re
from typing import Dict, Optional

TOKEN_RE = re.compile(r'name=["\']([^"\']*(?:token|csrf)[^"\']*)["\']\s+value=["\']([^"\']+)["\']', re.I)


def extract_tokens(html: str) -> Dict[str, str]:
    return {m.group(1): m.group(2) for m in TOKEN_RE.finditer(html)}


def refresh(session, url: str) -> Optional[Dict[str, str]]:  # pragma: no cover - network
    try:
        resp = session.get(url)
        return extract_tokens(resp.text)
    except Exception:
        return None


__all__ = ["extract_tokens", "refresh"]
