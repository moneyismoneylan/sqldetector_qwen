"""Orchestration pipeline (skeleton)."""

import asyncio
from pathlib import Path
from typing import List, Optional

from sqldetector.core.config import Settings
from sqldetector.core.errors import PolicyViolation
from sqldetector.core.http_async import HttpClient
from sqldetector.core.logging import setup_json_logging
from sqldetector.core.state import new_run
from sqldetector.core.trace_writer import TraceWriter


def run(url: str, dry_run: bool = False, settings: Optional[Settings] = None) -> List[dict]:
    settings = settings or Settings()
    if not settings.legal_ack:
        raise PolicyViolation("Legal acknowledgement required")

    state = new_run(settings.trace_dir or Path("traces"))
    if settings.log_json:
        setup_json_logging(settings.log_level, state.run_id)
    trace = TraceWriter(state.run_id, state.trace_dir)
    trace.append_jsonl({"event": "pipeline_start", "url": url})

    if dry_run:
        return []

    async def _run() -> List[dict]:
        async with HttpClient(settings) as client:
            resp = await client.get(url)
            trace.append_jsonl({"event": "request", "status": resp.status_code})
            return [{"status": resp.status_code}]

    return asyncio.run(_run())
