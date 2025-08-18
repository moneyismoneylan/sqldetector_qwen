import sys
from pathlib import Path

import httpx

from sqldetector.core.config import Settings
from sqldetector.planner import pipeline

sys.path.append(str(Path(__file__).resolve().parent / "utils"))
from mock_vuln_app import app  # noqa: E402


def test_pipeline_with_asgi_app():
    transport = httpx.ASGITransport(app=app)
    settings = Settings(legal_ack=True, transport=transport)
    result = pipeline.run("http://testserver/products", dry_run=False, settings=settings)
    assert result[0]["status"] == 200
