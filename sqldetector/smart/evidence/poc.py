from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def _redact(value: str) -> str:
    return "<redacted>" if value and len(value) > 80 else value


def build_snippets(
    url: str,
    clean_params: Dict[str, Any],
    inj_params: Dict[str, Any],
    clean_resp: Dict[str, Any],
    inj_resp: Dict[str, Any],
    unsafe: bool = False,
    outdir: str = "artifacts",
) -> Dict[str, Any]:
    """Generate minimal PoC snippets for a confirmed finding.

    The function is intentionally lightweight: it emits small ``curl`` and
    ``requests`` examples and a stub Postman collection saved under
    ``outdir``.  Secrets are redacted unless ``unsafe`` is ``True``.
    """

    Path(outdir).mkdir(parents=True, exist_ok=True)
    param, value = next(iter(inj_params.items()))
    curl = f"curl -G {url} --data-urlencode '{param}={value}'"
    requests_snippet = (
        "import requests\n"
        f"requests.get('{url}', params={{'{param}': '{value}'}})\n"
    )
    postman = {
        "info": {"name": "sqldetector PoC", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": [
            {
                "name": url,
                "request": {
                    "method": "GET",
                    "url": {"raw": url, "protocol": url.split(":", 1)[0], "host": [url]},
                },
            }
        ],
    }
    pm_path = Path(outdir) / "postman.json"
    pm_path.write_text(json.dumps(postman))

    diff = {
        "status": [clean_resp.get("status"), inj_resp.get("status")],
        "length": [clean_resp.get("len"), inj_resp.get("len")],
        "time": [clean_resp.get("time"), inj_resp.get("time")],
    }

    if not unsafe:
        diff = {k: [_redact(str(v)) for v in vals] for k, vals in diff.items()}

    return {
        "curl": curl,
        "requests": requests_snippet,
        "postman": str(pm_path),
        "diff": diff,
    }
