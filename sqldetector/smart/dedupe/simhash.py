import hashlib
from typing import List


def _hash(text: str) -> int:
    """Compute a simple 64-bit SimHash for the given text."""
    tokens = text.split()
    v = [0] * 64
    for tok in tokens:
        h = int.from_bytes(
            hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest(), "big"
        )
        for i in range(64):
            v[i] += 1 if h & (1 << i) else -1
    out = 0
    for i in range(64):
        if v[i] > 0:
            out |= 1 << i
    return out


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def cluster(pages: List[str], thresh: int = 6) -> List[List[str]]:
    """Cluster near-duplicate pages using SimHash64."""
    clusters: List[tuple[int, List[str]]] = []
    for body in pages:
        h = _hash(body)
        placed = False
        for i, (ch, texts) in enumerate(clusters):
            if hamming(h, ch) <= thresh:
                texts.append(body)
                placed = True
                break
        if not placed:
            clusters.append((h, [body]))
    return [c[1] for c in clusters]
