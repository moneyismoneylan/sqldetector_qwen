"""Target classification helpers.

The functions here perform a very small set of HTTP probes in order to
infer the nature of the remote target.  They intentionally avoid heavy
network usage so that AutoPilot remains fast.  All network operations
must be optional and safe to skip when the network is unavailable.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Dict

try:  # optional dependency
    import requests  # type: ignore
except Exception:  # pragma: no cover - requests not installed
    requests = None


@dataclass
class _Resp:
    headers: Dict[str, str]
    text: str = ""


WAF_HINTS = {
    "server": ["cloudflare", "akamai", "sucuri"],
    "via": ["cloudfront"],
    "cf-ray": [],
}

FRAMEWORK_RE = re.compile(r"react|angular|vue", re.I)


def _count_forms(body: str) -> int:
    return body.lower().count("<form")


def classify_target(seed_url: str, client: Any, sysinfo: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a target using a few light-weight probes.

    Parameters
    ----------
    seed_url:
        URL of the target root.
    client:
        HTTP client with ``get`` and ``head`` methods (``requests``-like).
    sysinfo:
        Host system information dictionary.

    Returns
    -------
    dict
        Profile describing the target.  Keys include ``kind``, ``signals``,
        ``rtt_ms``, ``waf`` and ``forms_per_page``.
    """

    profile: Dict[str, Any] = {
        "kind": "fast",
        "signals": {},
        "rtt_ms": None,
        "waf": False,
        "forms_per_page": 0.0,
    }

    if requests is None or client is None:
        return profile

    # Gather a few HEAD timings
    head_rtts = []
    headers_seen: Dict[str, str] = {}
    for _ in range(3):
        try:
            t0 = time.perf_counter()
            resp = client.head(seed_url, timeout=5)
            head_rtts.append((time.perf_counter() - t0) * 1000)
            headers_seen.update({k.lower(): v for k, v in resp.headers.items()})
        except Exception:
            continue
    if head_rtts:
        profile["rtt_ms"] = sum(head_rtts) / len(head_rtts)

    # Quick GET for body analysis
    body = ""
    try:
        resp = client.get(seed_url, timeout=8)
        headers_seen.update({k.lower(): v for k, v in resp.headers.items()})
        body = resp.text[:65536]
    except Exception:
        pass

    # WAF detection
    for key, needles in WAF_HINTS.items():
        val = headers_seen.get(key)
        if not val:
            continue
        if needles and any(n in val.lower() for n in needles):
            profile["waf"] = True
        if key == "cf-ray":
            profile["waf"] = True
    profile["signals"]["headers"] = headers_seen

    # Content-type hinting
    ctype = headers_seen.get("content-type", "").split(";")[0]
    if ctype:
        profile["signals"]["content_type"] = ctype

    # Form density
    forms = _count_forms(body)
    profile["forms_per_page"] = float(forms)

    # JS framework detection
    framework = None
    if FRAMEWORK_RE.search(body):
        framework = FRAMEWORK_RE.search(body).group(0).lower()
    profile["signals"]["framework"] = framework

    # Heuristic classification
    if ctype.startswith("application/json"):
        profile["kind"] = "api-json"
    elif framework and forms <= 1:
        profile["kind"] = "spa"
    elif forms >= 3:
        profile["kind"] = "forms-heavy"
    elif profile["waf"]:
        profile["kind"] = "waf-guarded"
    elif ctype.startswith("text/html"):
        profile["kind"] = "static"

    return profile
