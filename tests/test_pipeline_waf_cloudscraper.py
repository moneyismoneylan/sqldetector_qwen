import sys
from pathlib import Path
from types import SimpleNamespace

import cloudscraper
import httpx

from sqldetector.core.config import Settings
from sqldetector.core.errors import WAFBlocked
from sqldetector.core.http_async import HttpClient
from sqldetector.planner import pipeline

sys.path.append(str(Path(__file__).resolve().parent / "utils"))
from mock_vuln_app import app  # noqa: E402


async def _blocked(*args, **kwargs):
    raise WAFBlocked("blocked")


def test_pipeline_falls_back_to_cloudscraper(monkeypatch):
    transport = httpx.ASGITransport(app=app)
    settings = Settings(transport=transport)

    monkeypatch.setattr(HttpClient, "get", _blocked)

    dummy = SimpleNamespace(status_code=200)
    scraper = SimpleNamespace(get=lambda url: dummy)
    monkeypatch.setattr(cloudscraper, "create_scraper", lambda: scraper)

    result = pipeline.run("http://testserver/products", settings=settings)
    assert result[0]["status"] == 200

