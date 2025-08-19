"""Randomized payload transformations.

These helpers perform light-weight mutations to reduce the chance of WAF pattern
matches.  The real project would feature many more dialect specific tweaks; for
unit tests we only shuffle case and optionally append different SQL comment
styles.
"""
from __future__ import annotations

import random
from typing import Iterable, Optional

COMMENT_STYLES = ["--", "#", "/* */"]


def randomize(payload: str, *, rng: Optional[random.Random] = None) -> str:
    """Return a randomized variant of ``payload``.

    Characters are randomly upper/lower cased and a comment style is appended at
    the end.  ``rng`` can be supplied to obtain deterministic results in tests.
    """

    if rng is None:
        rng = random

    transformed = ''.join(
        c.upper() if c.isalpha() and rng.random() < 0.5 else c.lower() if c.isalpha() else c
        for c in payload
    )
    comment = rng.choice(COMMENT_STYLES)
    if comment == "/* */":
        return f"{transformed}/* */"
    return f"{transformed}{comment}"


def batch_randomize(payloads: Iterable[str], *, rng: Optional[random.Random] = None) -> Iterable[str]:
    """Yield randomized variants for an iterable of payloads."""

    for p in payloads:
        yield randomize(p, rng=rng)
