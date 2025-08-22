from __future__ import annotations

"""Derive payload family weighting hints from HTTP response headers."""

from typing import Dict


def server_weight(headers: Dict[str, str]) -> Dict[str, float]:
    server = headers.get("server", "").lower()
    powered = headers.get("x-powered-by", "").lower()
    weights: Dict[str, float] = {}
    if "php" in server or "php" in powered:
        weights["php"] = 2.0
    if "asp" in server or "asp" in powered or "iis" in server:
        weights["asp"] = 2.0
    if "java" in server or "tomcat" in server or "jetty" in server or "spring" in powered:
        weights["java"] = 2.0
    if "rails" in server or "rack" in powered:
        weights["rails"] = 2.0
    return weights
