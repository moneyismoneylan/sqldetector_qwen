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
    from sqldetector.ui.narrate import Narrator
    narrator = Narrator(lang=settings.advanced.get("lang", "tr"))
    narrator.step(f"Sayfa geziliyor: {url}")

    state = new_run(settings.trace_dir or Path("traces"))
    if settings.log_json:
        setup_json_logging(settings.log_level, state.run_id)

    if progress:
        progress(0.0)

    if dry_run:
        if progress:
            progress(100.0)
        return []

    if settings.advanced.get("micro"):
        from sqldetector.runners.micro import run_micro
        if progress:
            progress(0.0)
        result = asyncio.run(run_micro(url, settings.__dict__))
        if progress:
            progress(100.0)
        narrator.ok("Micro tarama tamamlandı")
        return result

    async def _run() -> List[dict]:
        trace = TraceWriter(
            state.run_id,
            state.trace_dir,
            getattr(settings, "trace_sample_rate", 1.0),
            getattr(settings, "trace_compress", None),
        )
        trace.append_jsonl({"event": "pipeline_start", "url": url})
        async with HttpClient(settings) as client:
            try:
                resp = await client.get(url)
                status = resp.status_code
            except WAFBlocked:
                if progress:
                    progress(50.0)
                narrator.note("WAF engeli aşılıyor")
                import cloudscraper

                scraper = cloudscraper.create_scraper()
                resp = await asyncio.to_thread(scraper.get, url)
                status = resp.status_code
            if progress:
                progress(100.0)
            trace.append_jsonl({"event": "request", "status": status})
            await trace.aclose()
            return [{"status": status}]

    result = asyncio.run(_run())
    narrator.ok("Tamamlandı")
    return result
