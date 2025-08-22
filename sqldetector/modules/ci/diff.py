"""CI diff helper stub."""
from typing import Iterable, List

def changed(a: Iterable[str], b: Iterable[str]) -> List[str]:
    return sorted(set(b) - set(a))
