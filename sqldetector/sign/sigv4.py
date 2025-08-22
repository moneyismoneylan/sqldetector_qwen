"""Minimal AWS SigV4 request signer."""

from __future__ import annotations

import datetime
import hashlib
import hmac
from typing import Dict


def sign_request(method: str, url: str, headers: Dict[str, str], body: bytes, creds: Dict[str, str]) -> Dict[str, str]:
    t = datetime.datetime.utcnow()
    amzdate = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")
    service = "execute-api"
    canonical_uri = "/"
    canonical_querystring = ""
    canonical_headers = f"host:{url}\n" + f"x-amz-date:{amzdate}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(body).hexdigest()
    canonical_request = "\n".join(
        [method, canonical_uri, canonical_querystring, canonical_headers, signed_headers, payload_hash]
    )
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{datestamp}/{creds['region']}/{service}/aws4_request"
    string_to_sign = "\n".join(
        [algorithm, amzdate, credential_scope, hashlib.sha256(canonical_request.encode()).hexdigest()]
    )
    def _sign(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()
    k_date = _sign(("AWS4" + creds['secret_key']).encode(), datestamp)
    k_region = _sign(k_date, creds['region'])
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
    authorization_header = (
        f"{algorithm} Credential={creds['access_key']}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    )
    new_headers = dict(headers)
    new_headers["Authorization"] = authorization_header
    new_headers["x-amz-date"] = amzdate
    return new_headers


__all__ = ["sign_request"]
