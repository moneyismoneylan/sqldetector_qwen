"""Endpoint discovery using Playwright.

The implementation is intentionally lightweight: it launches a headless browser
(using Playwright if available) and records all network requests triggered by the
page.  Simple form auto-fill and submission is attempted to surface additional
endpoints.  When Playwright is not installed the function returns an empty list.
"""
from __future__ import annotations

from typing import List, Set

try:  # pragma: no cover - optional dependency
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover
    async_playwright = None  # type: ignore


async def collect(url: str) -> List[str]:
    """Return a list of endpoints discovered while visiting ``url``."""
    if async_playwright is None:  # pragma: no cover - fallback when dependency missing
        return []

    endpoints: Set[str] = set()
    async with async_playwright() as pw:  # type: ignore[func-returns-value]
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("request", lambda req: endpoints.add(req.url))
        await page.goto(url)
        # try to submit forms with dummy data
        for form in await page.query_selector_all("form"):
            inputs = await form.query_selector_all("input[name]")
            for inp in inputs:
                try:
                    await inp.fill("1")
                except Exception:
                    pass
            try:
                await form.evaluate("form => form.submit()")
                await page.wait_for_timeout(50)
            except Exception:
                pass
        await browser.close()
    return sorted(endpoints)
