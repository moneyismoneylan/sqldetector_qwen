from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class TraceWriter:
    def __init__(self, run_id: str, trace_dir: Path):
        self.run_id = run_id
        self.path = trace_dir / "trace.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_jsonl(self, event: Dict[str, Any], request_id: Optional[str] = None) -> None:
        payload = dict(event)
        payload["run_id"] = self.run_id
        if request_id:
            payload["request_id"] = request_id
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
