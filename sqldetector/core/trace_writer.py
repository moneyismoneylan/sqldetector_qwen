from __future__ import annotations

"""Asynchronous trace writer.

Events are pushed onto an ``asyncio.Queue`` and written by a single
background task.  Batching is used to reduce fsync overhead.  The API is
intentionally tiny: :meth:`append_jsonl` is non-blocking and
:meth:`aclose` should be awaited before shutdown.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import orjson


class TraceWriter:
    """Asynchronous JSONL writer used for trace events."""

    def __init__(
        self,
        run_id: str,
        trace_dir: Path,
        sample_rate: float = 1.0,
        compress: str | None = None,
        flush_interval: float = 0.5,
        batch_size: int = 50,
    ) -> None:
        self.run_id = run_id
        self.path = trace_dir / "trace.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sample_rate = float(sample_rate)
        self.compress = compress
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self._queue: "asyncio.Queue[Optional[Dict[str, Any]]]" = asyncio.Queue()
        self._worker = asyncio.create_task(self._run())

    def append_jsonl(self, event: Dict[str, Any], request_id: Optional[str] = None) -> None:
        """Queue a trace event for writing.

        The call is non-blocking; the data is serialized asynchronously by a
        background task.
        """

        payload = dict(event)
        payload["run_id"] = self.run_id
        if request_id:
            payload["request_id"] = request_id
        # sampling
        if self.sample_rate < 1.0:
            import random

            if random.random() > self.sample_rate:  # pragma: no cover - nondeterministic
                return
        self._queue.put_nowait(payload)

    async def _run(self) -> None:
        """Background coroutine writing queued events to disk."""
        while True:
            batch: list[Dict[str, Any]] = []
            item = await self._queue.get()
            if item is None:
                break
            batch.append(item)
            try:
                while len(batch) < self.batch_size:
                    batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                pass
            data = b"\n".join(orjson.dumps(ev) for ev in batch) + b"\n"
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "ab") as f:
                f.write(data)
            await asyncio.sleep(self.flush_interval)
        # drain remaining events if any
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            data = orjson.dumps(item) + b"\n"
            with open(self.path, "ab") as f:
                f.write(data)

    async def aclose(self) -> None:
        """Flush remaining events and stop background task."""
        await self._queue.put(None)
        await self._worker
