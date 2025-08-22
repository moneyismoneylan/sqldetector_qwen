"""Simple on-disk HTTP conditional cache."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Optional

import httpx


class CacheTransport(httpx.AsyncBaseTransport):
    """Wrap another transport and provide ETag/Last-Modified cache."""

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self._transport = transport or httpx.AsyncHTTPTransport()
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)

    # --------------------------------------------------------------
    def _key(self, request: httpx.Request) -> Path:
        digest = hashlib.sha1(str(request.url).encode()).hexdigest()
        return self.cache_dir / f"{digest}.json"

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:  # noqa: D401
        meta_path = self._key(request)
        if request.method == "GET" and meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                if et := meta.get("etag"):
                    request.headers["If-None-Match"] = et
                if lm := meta.get("last_mod"):
                    request.headers["If-Modified-Since"] = lm
            except Exception:  # pragma: no cover - corrupt cache
                pass

        response = await self._transport.handle_async_request(request)

        if request.method != "GET":
            return response

        if response.status_code == 304 and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            return httpx.Response(
                200,
                headers=meta.get("headers", {}),
                content=Path(meta["body"]).read_bytes(),
                request=request,
            )

        if response.status_code == 200:
            et = response.headers.get("ETag")
            lm = response.headers.get("Last-Modified")
            if et or lm:
                body_path = meta_path.with_suffix(".body")
                data = await response.aread()
                body_path.write_bytes(data)
                meta = {
                    "etag": et,
                    "last_mod": lm,
                    "headers": dict(response.headers),
                    "body": str(body_path),
                }
                meta_path.write_text(json.dumps(meta))
                response = httpx.Response(
                    200,
                    headers=response.headers,
                    content=data,
                    request=request,
                )
        return response


# best effort synchronous fallback -----------------------------------------

