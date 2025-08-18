from __future__ import annotations

import os
from argparse import Namespace
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

# Python 3.11+ provides "tomllib" in the stdlib.  Earlier versions can use the
# third-party "tomli" package.  This shim keeps the module importable on systems
# that haven't upgraded yet, which is particularly helpful on Windows where old
# Python versions may linger.
try:  # pragma: no cover - executed only on Python <3.11
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "tomllib is unavailable; install 'tomli' or upgrade to Python 3.11+"
        ) from exc


@dataclass
class Settings:
    safe_mode: bool = True
    legal_ack: bool = False
    timeout: float = 10.0
    concurrency: int = 5
    retry_budget: int = 5
    rate_limit: int = 5
    log_json: bool = False
    log_level: str = "INFO"
    trace_dir: Path | None = None
    hedge_delay: float = 0.0
    transport: Any | None = None


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data


def _coerce(field, value: str) -> Any:
    if field.type is bool:
        return value.lower() in {"1", "true", "yes", "on"}
    if field.type is int:
        return int(value)
    if field.type is float:
        return float(value)
    if str(field.type).startswith('pathlib.Path') or 'Path' in str(field.type):
        return Path(value)
    return value


def merge_settings(cli_args: Namespace) -> Settings:
    data: dict[str, Any] = {}
    if getattr(cli_args, "config", None):
        data.update(load_config(cli_args.config))
    # environment variables
    for f in fields(Settings):
        env_key = f"SQLDETECTOR_{f.name.upper()}"
        if env_key in os.environ:
            data[f.name] = _coerce(f, os.environ[env_key])
    # CLI overrides
    if getattr(cli_args, "trace_dir", None):
        data["trace_dir"] = Path(cli_args.trace_dir)
    if getattr(cli_args, "log_json", False):
        data["log_json"] = True
    if getattr(cli_args, "log_level", None):
        data["log_level"] = cli_args.log_level
    if getattr(cli_args, "legal_ack", False):
        data["legal_ack"] = True
    return Settings(**data)
