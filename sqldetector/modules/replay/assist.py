"""Replay assist placeholder."""
from pathlib import Path
from typing import List

def load(path: str) -> List[str]:
    return [l.strip() for l in Path(path).read_text().splitlines() if l.strip()]
