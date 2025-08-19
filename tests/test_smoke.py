import sys
import pytest
from sqldetector_qwen import main
from sqldetector.planner import pipeline


def test_cli_invokes_pipeline(monkeypatch):
    called = {}

    def fake_run(url, dry_run=False, settings=None):
        called["url"] = url
        return []

    monkeypatch.setattr(pipeline, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["sqldetector_qwen.py", "http://example.com"])
    main()
    assert called["url"] == "http://example.com"
