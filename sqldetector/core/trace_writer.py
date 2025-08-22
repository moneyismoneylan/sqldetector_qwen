from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from sqldetector.tracewrap import write_trace


class TraceWriter:
    def __init__(
        self,
        run_id: str,
        trace_dir: Path,
        sample_rate: float = 1.0,
        compress: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.path = trace_dir / "trace.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self.compress = compress

    def append_jsonl(self, event: Dict[str, Any], request_id: Optional[str] = None) -> None:
        payload = dict(event)
        payload["run_id"] = self.run_id
        if request_id:
            payload["request_id"] = request_id
        write_trace(self.path, payload, self.sample_rate, self.compress, append=True)
