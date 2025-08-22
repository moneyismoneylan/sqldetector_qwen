"""Orchestration pipeline (skeleton)."""

import asyncio
from pathlib import Path
from typing import Callable, List, Optional

from sqldetector.core.config import Settings
from sqldetector.core.errors import WAFBlocked
from sqldetector.core.http_async import HttpClient
from sqldetector.core.logging import setup_json_logging
from sqldetector.core.state import new_run
from sqldetector.core.trace_writer import TraceWriter


def run(
    url: str,
    dry_run: bool = False,
    settings: Optional[Settings] = None,
    progress: Optional[Callable[[float], None]] = None,
) -> List[dict]:
    settings = settings or Settings()

    state = new_run(settings.trace_dir or Path("traces"))
    if settings.log_json:
        setup_json_logging(settings.log_level, state.run_id)
    trace = TraceWriter(
        state.run_id,
        state.trace_dir,
        getattr(settings, "trace_sample_rate", 1.0),
        getattr(settings, "trace_compress", None),
    )
    trace.append_jsonl({"event": "pipeline_start", "url": url})

    if progress:
        progress(0.0)

    if dry_run:
        if progress:
            progress(100.0)
        return []

    async def _run() -> List[dict]:
        async with HttpClient(settings) as client:
            try:
                resp = await client.get(url)
                status = resp.status_code
            except WAFBlocked:
                if progress:
                    progress(50.0)
                import cloudscraper

                scraper = cloudscraper.create_scraper()
                resp = await asyncio.to_thread(scraper.get, url)
                status = resp.status_code
            if progress:
                progress(100.0)
            trace.append_jsonl({"event": "request", "status": status})
            return [{"status": status}]

    return asyncio.run(_run())
