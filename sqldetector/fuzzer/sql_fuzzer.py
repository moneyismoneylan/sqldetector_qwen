"""Dialect-aware SQL grammar fuzzer (simplified).

 The real implementation would operate on ASTs for each database engine.
 For the purposes of unit tests we only provide a handful of payload
 templates per dialect and deduplicate them using a tiny Bloom filter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Iterable, List
import asyncio

from sqldetector.filter.bloom import BloomFilter


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
    dedup: BloomFilter = field(default_factory=BloomFilter)

    def generate(self, dialect: str, base: str) -> Iterable[str]:
        """Generate unique payloads for the given dialect."""

        for template in self.templates.get(dialect.lower(), []):
            payload = base + template
            if self.dedup.add(payload):
                continue
            yield payload

    async def generate_async(self, dialect: str, base: str) -> AsyncIterator[str]:
        """Asynchronous variant of :meth:`generate`.

        Using ``async`` allows callers to interleave payload generation with
        other I/O-bound work.  The coroutine yields control back to the event
        loop after each payload to keep the loop responsive.
        """
        for template in self.templates.get(dialect.lower(), []):
            payload = base + template
            if self.dedup.add(payload):
                continue
            yield payload
            await asyncio.sleep(0)
