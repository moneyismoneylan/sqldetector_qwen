from __future__ import annotations

import os

from argparse import Namespace
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Optional, Union

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore


@dataclass
class Settings:
    safe_mode: bool = True
    timeout_connect: float = 5.0
    timeout_read: float = 10.0
    timeout_write: float = 10.0
    timeout_pool: float = 5.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    concurrency: int = 5
    retry_budget: int = 5
    rate_limit: int = 5
    log_json: bool = False
    log_level: str = "INFO"
    trace_dir: Optional[Path] = None
    hedge_delay: float = 0.0
    transport: Optional[Any] = None
    trace_sample_rate: float = 1.0
    trace_compress: Optional[str] = None
    stop_after_first_finding: bool = False
    max_forms_per_page: Optional[int] = None
    max_tests_per_form: Optional[int] = None
    use_llm: str = "auto"
    llm_cache_path: Optional[Path] = None
    llm_cache_ttl_hours: int = 72
    max_pages: Optional[int] = None
    max_body_kb: Optional[int] = None
    skip_binary_ext: Optional[list[str]] = None
    fingerprint_db: Optional[Path] = None


def load_config(path: Union[str, Path]) -> dict[str, Any]:
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
    if str(field.type).startswith("pathlib.Path") or "Path" in str(field.type):
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
    if getattr(cli_args, "stop_after_first_finding", False):
        data["stop_after_first_finding"] = True
    if getattr(cli_args, "max_forms_per_page", None) is not None:
        data["max_forms_per_page"] = cli_args.max_forms_per_page
    if getattr(cli_args, "max_tests_per_form", None) is not None:
        data["max_tests_per_form"] = cli_args.max_tests_per_form
    if getattr(cli_args, "use_llm", None):
        data["use_llm"] = cli_args.use_llm
    return Settings(**data)
