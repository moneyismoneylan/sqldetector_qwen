from __future__ import annotations

import os

from argparse import Namespace
from dataclasses import dataclass, fields, field
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
    hedge_max_ratio: float = 0.1
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
    bandit_enabled: bool = False
    bandit_algo: str = "ucb1"
    dns_cache_ttl_sec: int = 900
    dns_warmup_batch: int = 8
    prewarm_connections: bool = False
    happy_eyeballs: bool = False
    range_fetch_kb: int = 0
    http_cache_enabled: bool = False
    respect_robots: bool = True
    simhash_enabled: bool = False
    near_duplicate_threshold: int = 6
    form_dedupe_enabled: bool = False
    server_weighting: bool = False
    endpoint_budget_ms: int = 0
    bloom_enabled: bool = False
    bloom_bits: int = 1_048_576
    bloom_ttl_hours: int = 72
    cpu_target_pct: int = 0
    cpu_pacer_min_rps: int = 1
    cpu_pacer_max_rps: int = 200
    # container for advanced experimental features
    advanced: dict[str, Any] = field(default_factory=dict)


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
    data.setdefault("advanced", {})
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
    if getattr(cli_args, "bandit", None):
        if cli_args.bandit == "off":
            data["bandit_enabled"] = False
        else:
            data["bandit_enabled"] = True
            data["bandit_algo"] = cli_args.bandit
    if getattr(cli_args, "dns_cache_ttl", None) is not None:
        data["dns_cache_ttl_sec"] = cli_args.dns_cache_ttl
    if getattr(cli_args, "dns_warmup_batch", None) is not None:
        data["dns_warmup_batch"] = cli_args.dns_warmup_batch
    if getattr(cli_args, "prewarm", False):
        data["prewarm_connections"] = True
    if getattr(cli_args, "happy_eyeballs", False):
        data["happy_eyeballs"] = True
    if getattr(cli_args, "range_fetch_kb", None) is not None:
        data["range_fetch_kb"] = cli_args.range_fetch_kb
    if getattr(cli_args, "http_cache", False):
        data["http_cache_enabled"] = True
    if getattr(cli_args, "ignore_robots", False):
        data["respect_robots"] = False
    if getattr(cli_args, "simhash", False):
        data["simhash_enabled"] = True
    if getattr(cli_args, "near_dup_th", None) is not None:
        data["near_duplicate_threshold"] = cli_args.near_dup_th
    if getattr(cli_args, "form_dedupe", False):
        data["form_dedupe_enabled"] = True
    if getattr(cli_args, "server_weighting", False):
        data["server_weighting"] = True
    if getattr(cli_args, "endpoint_budget_ms", None) is not None:
        data["endpoint_budget_ms"] = cli_args.endpoint_budget_ms
    if getattr(cli_args, "bloom", False):
        data["bloom_enabled"] = True
    if getattr(cli_args, "bloom_bits", None) is not None:
        data["bloom_bits"] = cli_args.bloom_bits
    if getattr(cli_args, "bloom_ttl", None) is not None:
        data["bloom_ttl_hours"] = cli_args.bloom_ttl
    if getattr(cli_args, "cpu_target_pct", None) is not None:
        data["cpu_target_pct"] = cli_args.cpu_target_pct
    if getattr(cli_args, "cpu_pacer_min_rps", None) is not None:
        data["cpu_pacer_min_rps"] = cli_args.cpu_pacer_min_rps
    if getattr(cli_args, "cpu_pacer_max_rps", None) is not None:
        data["cpu_pacer_max_rps"] = cli_args.cpu_pacer_max_rps
    # advanced flags mirrored under [advanced]
    adv_map = {
        "smart": bool,
        "lang": str,
        "report": str,
        "import_openapi": str,
        "import_postman": str,
        "import_har": str,
        "graphql": bool,
        "grpc": bool,
        "param_infer": bool,
        "waf_learn": bool,
        "ratelimit_auto": bool,
        "tls_fp": str,
        "http3": bool,
        "cdn_aware": bool,
        "oauth": str,
        "layer_split_tests": bool,
        "payload_cfg": str,
        "delta_debug": bool,
        "route_calibrate": bool,
        "cluster_endpoints": bool,
        "ci_diff": list,
        "js_extract": bool,
        "etag_conditional": bool,
        "encoding_adapt": bool,
        "sticky_session": bool,
        "replay": str,
        "otel": str,
        "online-optimizer": bool,
        "second-order": bool,
        "hpp": bool,
        "byte-fuzz": bool,
        "method-override": bool,
        "cache-bypass": bool,
        "token-freeze": bool,
        "template-diff": bool,
        "l10n-payloads": bool,
        "sigv4": str,
        "captcha-aware": bool,
        "honeypot-guard": bool,
        "shadow-param": bool,
        "safe-poc": bool,
        "subdomain-seed": bool,
        "locale-shard": bool,
        "twin-sampler": bool,
        "header-mutator": bool,
        "csv-import": bool,
        "micro": bool,
    }
    adv = data["advanced"]
    for key in adv_map:
        attr = key.replace('-', '_')
        val = getattr(cli_args, attr, None)
        if val is not None:
            adv[key] = val
    data["advanced"] = adv
    return Settings(**data)
