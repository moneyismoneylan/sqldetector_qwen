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
    monkeypatch.setattr(sys, "argv", ["sqldetector_qwen.py", "http://example.com", "--legal-ack"])
    main()
    assert called["url"] == "http://example.com"


def test_cli_requires_legal_ack(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["sqldetector_qwen.py", "http://example.com"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
