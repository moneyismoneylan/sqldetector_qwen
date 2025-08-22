"""Cheap prefilter to short-circuit obviously safe inputs."""
from __future__ import annotations

import re
from typing import Dict, Iterable, List

try:
    import ahocorasick  # type: ignore
except Exception:  # pragma: no cover - optional dependency missing
    ahocorasick = None

_SQL_TOKENS = [
    "select",
    "union",
    "sleep",
    "'--",
    "/*",
    "or 1=1",
]
_SUS_KEYS = ["id", "cat", "pid", "uid", "order", "sort", "page", "offset", "limit"]

if ahocorasick:
    _AC = ahocorasick.Automaton()
    for token in _SQL_TOKENS:
        _AC.add_word(token, token)
    _AC.make_automaton()
else:
    _REGEX = re.compile("|".join(re.escape(t) for t in _SQL_TOKENS), re.I)


def _scan(text: str) -> List[str]:
    text = text.lower()
    signals: List[str] = []
    if ahocorasick:
        for _, found in _AC.iter(text):
            signals.append(found)
    else:
        signals.extend(_REGEX.findall(text))
    return signals


def cheap_prefilter(
    url: str,
    params: Dict[str, str] | Iterable[tuple[str, str]],
    form_meta: Dict[str, str] | None = None,
    content_type: str | None = None,
) -> Dict[str, object]:
    form_meta = form_meta or {}
    if isinstance(params, dict):
        items = params.items()
    else:
        items = list(params)
    blob = url.lower() + "&".join(f"{k}={v}" for k, v in items).lower()
    signals = _scan(blob)
    key_hits = [k for k, _ in items if k.lower() in _SUS_KEYS]
    score = 0.0
    if signals:
        score = 0.7
    elif key_hits:
        score = 0.3
    return {"score": min(1.0, score), "signals": sorted(set(signals + key_hits))}


def should_skip_deep_tests(score: float, threshold: float = 0.2) -> bool:
    return score < threshold
