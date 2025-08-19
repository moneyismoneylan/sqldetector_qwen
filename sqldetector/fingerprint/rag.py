"""Very small RAG-like helper using header fingerprints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import xxhash


@dataclass
class FingerprintIndex:
    store: Dict[str, str]

    def lookup(self, headers: Dict[str, str]) -> Optional[str]:
        key = xxhash.xxh3_64_hexdigest("|".join(f"{k}:{v}" for k, v in sorted(headers.items())))
        return self.store.get(key)
