import math
from typing import Dict


DEFAULT_COEFS = {
    "reflection": 1.2,
    "status": 1.0,
    "size": 0.8,
    "time": 0.5,
    "header": 0.6,
}
BIAS = -2.0


class FusionModel:
    """Tiny logistic regression to fuse weak signals.

    The model is intentionally simple: coefficients are static but can be
    overridden at construction time.  Input features should be normalised to
    ``[0,1]`` values representing the strength of individual signals.
    """

    def __init__(self, coefs: Dict[str, float] | None = None, bias: float = BIAS) -> None:
        self.coefs = coefs or DEFAULT_COEFS
        self.bias = bias

    def score(self, feats: Dict[str, float]) -> float:
        z = self.bias
        for name, coef in self.coefs.items():
            z += coef * feats.get(name, 0.0)
        return 1.0 / (1.0 + math.exp(-z))

    def confident(self, feats: Dict[str, float], th: float = 0.5) -> bool:
        return self.score(feats) >= th
