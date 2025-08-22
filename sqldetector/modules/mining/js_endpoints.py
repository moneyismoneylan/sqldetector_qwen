"""JavaScript endpoint mining using regex."""
import re
from typing import List

_PATTERN = re.compile(r"fetch\(['\"]([^'\"]+)['\"]")

def extract(src: str) -> List[str]:
    return _PATTERN.findall(src)
