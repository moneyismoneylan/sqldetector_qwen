"""Timing-based statistical tests.

This module implements a very small subset of the statistics that the real
project would use.  The goal for the exercises is to provide lightweight and
dependency free helpers that still capture the spirit of the recommendation
"Timing-channel statistics" from the design document.

``evaluate_timing`` performs two calculations:

* Mann–Whitney U test – a non‑parametric test that determines whether two
  independent samples come from the same distribution.  We return the ``U``
  statistic and an approximated two‑sided ``p`` value using a normal
  distribution.
* Cliff's delta – a non‑parametric effect size metric which expresses how often
  values in ``variant`` are larger than those in ``control``.

The function returns a dictionary containing the above metrics so callers can
decide whether an observed timing difference is significant.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Sequence


def _mann_whitney_u(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Return the U statistic and a two-sided p-value.

    The implementation follows the textbook algorithm and uses a normal
    approximation for the p-value which is sufficient for small sample sizes
    used in our unit tests.  Ties are ignored which keeps the function compact.
    """

    n1, n2 = len(x), len(y)
    ranked = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks = [0.0] * (n1 + n2)
    for i, (_, grp) in enumerate(ranked, 1):
        ranks[i - 1] = i
    r1 = sum(ranks[i] for i, (_, grp) in enumerate(ranked) if grp == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    u = min(u1, u2)
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sigma == 0:
        return u, 1.0
    z = (u - mu) / sigma
    # two sided normal distribution using error function
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return u, p


def _cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    gt = lt = 0
    for a in x:
        for b in y:
            if a > b:
                gt += 1
            elif a < b:
                lt += 1
    n1, n2 = len(x), len(y)
    if n1 * n2 == 0:
        return 0.0
    return (gt - lt) / (n1 * n2)


def evaluate_timing(control: Sequence[float], variant: Sequence[float]) -> Dict[str, Any]:
    """Evaluate timing differences between two sample sets.

    Parameters
    ----------
    control, variant:
        Sequences of timing measurements (in seconds).

    Returns
    -------
    Dict[str, Any]
        Dictionary containing the Mann–Whitney ``u`` statistic, ``p`` value and
        Cliff's ``delta`` effect size.
    """

    control = list(control)
    variant = list(variant)
    u, p = _mann_whitney_u(control, variant)
    delta = _cliffs_delta(control, variant)
    return {"u": u, "p": p, "cliffs_delta": delta}


def sequential_test(control_fn, variant_fn, *, max_rounds: int = 7, alpha: float = 0.05):
    """Run a simple sequential test between two callables.

    ``control_fn`` and ``variant_fn`` are callables returning timing samples. The
    function collects up to ``max_rounds`` samples from each and after every
    round evaluates the Mann–Whitney p-value.  Testing stops early once the
    p-value drops below ``alpha``.  Returns a tuple ``(detected, stats)`` where
    ``detected`` indicates whether a significant difference was observed and
    ``stats`` contains the last statistics plus the number of rounds executed.
    """

    control: list[float] = []
    variant: list[float] = []
    stats: Dict[str, Any] = {"u": 0.0, "p": 1.0, "cliffs_delta": 0.0, "rounds": 0}
    for round_ in range(1, max_rounds + 1):
        control.append(control_fn())
        variant.append(variant_fn())
        stats = evaluate_timing(control, variant)
        stats["rounds"] = round_
        if stats["p"] < alpha:
            return True, stats
    return False, stats

