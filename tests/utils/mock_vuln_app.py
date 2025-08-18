import asyncio
import json
from urllib.parse import parse_qs


async def app(scope, receive, send):
    assert scope["type"] == "http"
    query = parse_qs(scope.get("query_string", b"").decode())
    probe = query.get("probe", [None])[0]
    body = b"{\"items\": []}"
    if probe == "time":
        await asyncio.sleep(0.1)
    elif probe == "error":
        body = b"sql error"
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})
