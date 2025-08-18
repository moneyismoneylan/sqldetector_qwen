import httpx
import pytest

from sqldetector.waf.fingerprint import identify


@pytest.mark.asyncio
async def test_identify_cloudflare():
    async def handler(request):
        return httpx.Response(403, headers={"Server": "cloudflare"}, text="blocked")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fp = await identify("http://test/", client=client)
    assert fp == "cloudflare"
