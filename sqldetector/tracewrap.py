"""Trace writing helpers with sampling and optional compression."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

try:
    import zstandard as zstd  # type: ignore
except Exception:  # pragma: no cover - optional
    zstd = None


def write_trace(
    path: Path,
    data: dict[str, Any],
    sample_rate: float = 1.0,
    compress: str | None = None,
    append: bool = True,
) -> None:
    """Write a JSON trace entry with sampling and compression."""
    if sample_rate < 1.0 and random.random() > sample_rate:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data) + "\n").encode()
    mode = "ab" if append else "wb"
    if compress == "zstd" and zstd is not None:
        path = path.with_suffix(path.suffix + ".zst")
        cctx = zstd.ZstdCompressor()
        with open(path, mode) as f:
            f.write(cctx.compress(payload))
    else:
        with open(path, mode) as f:
            f.write(payload)
