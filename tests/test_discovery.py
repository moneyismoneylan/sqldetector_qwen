import pytest
from sqldetector.discovery import collector


class DummyRequest:
    def __init__(self, url):
        self.url = url


class DummyPage:
    def __init__(self):
        self.handlers = {}

    def on(self, event, handler):
        self.handlers[event] = handler

    async def goto(self, url):
        self.handlers["request"](DummyRequest(url + "/api"))

    async def query_selector_all(self, selector):
        return []

    async def wait_for_timeout(self, ms):
        pass


class DummyBrowser:
    async def new_page(self):
        return DummyPage()

    async def close(self):
        pass


class DummyPW:
    def __init__(self):
        self.chromium = self

    async def launch(self, headless=True):
        return DummyBrowser()


class DummyContext:
    async def __aenter__(self):
        return DummyPW()

    async def __aexit__(self, exc_type, exc, tb):
        pass


def fake_async_playwright():
    return DummyContext()


@pytest.mark.asyncio
async def test_collect_captures_requests(monkeypatch):
    monkeypatch.setattr(collector, "async_playwright", fake_async_playwright)
    result = await collector.collect("http://example.com")
    assert result == ["http://example.com/api"]
