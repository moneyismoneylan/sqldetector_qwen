from __future__ import annotations

import json
import logging
from datetime import datetime


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        data = {
            "time": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "msg": record.getMessage(),
            "run_id": getattr(record, "run_id", None),
            "request_id": getattr(record, "request_id", None),
            "phase": getattr(record, "phase", None),
        }
        return json.dumps(data)


class _RunFilter(logging.Filter):
    def __init__(self, run_id: str):
        super().__init__("sqldetector")
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        record.run_id = self.run_id
        return True


def setup_json_logging(level: str, run_id: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RunFilter(run_id))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
