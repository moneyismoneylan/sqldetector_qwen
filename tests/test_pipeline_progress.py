import sys
from pathlib import Path

import httpx

from sqldetector.core.config import Settings
from sqldetector.planner import pipeline

sys.path.append(str(Path(__file__).resolve().parent / "utils"))
from mock_vuln_app import app  # noqa: E402


def test_pipeline_progress():
    transport = httpx.ASGITransport(app=app)
    settings = Settings(transport=transport)
    calls = []

    def progress(pct: float) -> None:
        calls.append(pct)

    pipeline.run("http://testserver/products", settings=settings, progress=progress)
    assert calls[0] == 0.0
    assert calls[-1] == 100.0

