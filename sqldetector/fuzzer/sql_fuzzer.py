"""Dialect-aware SQL grammar fuzzer (simplified).

The real implementation would operate on ASTs for each database
engine.  For the purposes of unit tests we only provide a handful of
payload templates per dialect and deduplicate them using a tiny Bloom
filter analogue based on Python sets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set


@dataclass
class SQLFuzzer:
    templates: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "mysql": ["' OR 1=1 -- ", '" OR 1=1 #'],
            "postgres": ["' OR 1=1 -- ", "'); DROP TABLE users; --"],
            "mssql": ["' OR 1=1 -- ", '"; WAITFOR DELAY ''00:00:05'' --'],
            "oracle": ["' OR '1'='1", "' UNION SELECT NULL FROM dual --"],
        }
    )
    _seen: Set[int] = field(default_factory=set)

    def generate(self, dialect: str, base: str) -> Iterable[str]:
        """Generate unique payloads for the given dialect."""

        for template in self.templates.get(dialect.lower(), []):
            payload = base + template
            h = hash(payload)
            if h in self._seen:
                continue
            self._seen.add(h)
            yield payload
