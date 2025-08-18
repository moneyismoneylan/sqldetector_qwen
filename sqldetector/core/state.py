from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunState:
    run_id: str
    seed: int
    started_at: datetime
    trace_dir: Path


def new_run(trace_dir: Path | None = None) -> RunState:
    if trace_dir is None:
        trace_dir = Path("traces")
    trace_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    seed = random.randint(0, 2**32 - 1)
    return RunState(run_id=run_id, seed=seed, started_at=datetime.utcnow(), trace_dir=trace_dir)
