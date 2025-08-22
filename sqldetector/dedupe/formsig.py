from __future__ import annotations

"""Utilities for deduplicating HTML form schemas."""

from dataclasses import dataclass, field
from typing import Iterable, List, Set, Tuple
from urllib.parse import urlsplit, urlunsplit


def canonical_action(url: str) -> str:
    if not url:
        return ""
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))


def form_signature(action: str, fields: Iterable[Tuple[str, str]]) -> str:
    canonical_fields = sorted((name.strip().lower(), typ.strip().lower()) for name, typ in fields)
    action_norm = canonical_action(action)
    serialized = ";".join(f"{n}:{t}" for n, t in canonical_fields)
    return f"{action_norm}|{serialized}"


@dataclass
class FormSigStore:
    """Track seen form signatures per host."""

    seen_map: dict[str, Set[str]] = field(default_factory=dict)

    def seen(self, host: str, signature: str) -> bool:
        s = self.seen_map.setdefault(host, set())
        if signature in s:
            return True
        s.add(signature)
        return False
