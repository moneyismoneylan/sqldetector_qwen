"""Subdomain seeding utilities."""

from __future__ import annotations

import re
from typing import Set

SUBDOMAIN_RE = re.compile(r"https?://([a-z0-9.-]+)")


def extract(text: str, base_domain: str) -> Set[str]:
    subs: Set[str] = set()
    for match in SUBDOMAIN_RE.finditer(text):
        host = match.group(1)
        if host.endswith(base_domain) and host != base_domain:
            subs.add(host)
    return subs


__all__ = ["extract", "SUBDOMAIN_RE"]
