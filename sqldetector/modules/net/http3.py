"""HTTP/3 transport stub."""
try:  # pragma: no cover - optional
    import aioquic  # type: ignore
    _available = True
except Exception:  # pragma: no cover
    _available = False


def is_available() -> bool:
    return _available
