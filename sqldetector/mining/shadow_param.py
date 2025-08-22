"""Shadow parameter discovery from hints."""

from __future__ import annotations

import json
from typing import Set


def from_headers(headers: dict[str, str]) -> Set[str]:
    params: Set[str] = set()
    allow = headers.get("Allow")
    if allow:
        params.update({h.lower() for h in allow.split(",") if h})
    link = headers.get("Link")
    if link and "?" in link:
        try:
            q = link.split("?")[1]
            for kv in q.split("&"):
                params.add(kv.split("=")[0])
        except Exception:
            pass
    return params


def from_json_schema(schema: str) -> Set[str]:
    try:
        data = json.loads(schema)
    except Exception:
        return set()
    props = data.get("properties", {})
    return set(props.keys())


__all__ = ["from_headers", "from_json_schema"]
