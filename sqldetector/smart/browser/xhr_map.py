from __future__ import annotations

from typing import List, Dict

try:  # pragma: no cover - optional dependency
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:  # pragma: no cover - if playwright missing
    sync_playwright = None  # type: ignore


def discover_xhr(url: str) -> List[Dict[str, str]]:
    """Headless browser run to map XHR/fetch calls.

    The implementation intentionally does a best effort: if Playwright is not
    available an empty list is returned.
    """

    if not sync_playwright:
        return []
    items: List[Dict[str, str]] = []
    with sync_playwright() as p:  # pragma: no cover - heavy dependency
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on(
            "request",
            lambda req: items.append({"url": req.url, "method": req.method}),
        )
        page.goto(url)
        browser.close()
    return items
