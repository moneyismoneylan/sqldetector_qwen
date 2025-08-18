from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, Optional

_registry: Dict[str, Dict[str, Callable]] = defaultdict(dict)


def register(kind: str, name: str, fn: Optional[Callable] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        _registry[kind][name] = func
        return func

    if fn is not None:
        return decorator(fn)
    return decorator


def get(kind: str) -> Dict[str, Callable]:
    return dict(_registry.get(kind, {}))
