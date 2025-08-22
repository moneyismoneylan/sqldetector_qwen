"""Delta debugging helper to minimise payloads."""
from typing import Callable


def shrink(payload: str, test: Callable[[str], bool]) -> str:
    tokens = payload.split()
    i = 0
    while i < len(tokens):
        trial = " ".join(tokens[:i] + tokens[i + 1 :])
        if trial and test(trial):
            tokens = trial.split()
            i = 0
            continue
        i += 1
    return " ".join(tokens)
