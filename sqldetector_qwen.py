import argparse
import sys
from urllib.parse import urlparse

from sqldetector.planner import pipeline
from sqldetector.core.config import Settings, merge_settings
from sqldetector.presets import (
    load_preset,
    deep_merge as merge_dicts,
    apply_system_overrides,
)
from sqldetector.autopilot import selector, policy, system as autosys, store


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI-powered SQL injection detector")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without network calls")
    parser.add_argument("--config", type=str, help="Path to TOML configuration file")
    parser.add_argument("--trace-dir", type=str, help="Directory to store trace logs")
    parser.add_argument(
        "--preset",
        choices=["fast","stealth","api","spa","forms","crawler","budget-ci"],
        help="Use built-in preset",
    )
    parser.add_argument("--auto", action="store_true", help="Enable AutoPilot mode")
    parser.add_argument("--autopilot", action="store_true", help="Alias for --auto")
    parser.add_argument("--print-plan", action="store_true", help="Print AutoPilot plan and exit if --dry-run")
    parser.add_argument("--force-preset", type=str, help="Force preset name in AutoPilot mode")
    parser.add_argument(
        "--stop-after-first-finding", action="store_true", help="Exit on first finding",
    )
    parser.add_argument("--max-forms-per-page", type=int)
    parser.add_argument("--max-tests-per-form", type=int)
    parser.add_argument("--use-llm", choices=["auto", "always", "never"])
    parser.add_argument("--log-json", action="store_true", help="Enable JSON structured logging")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    parser.add_argument("--bandit", choices=["off", "ucb1", "thompson"], help="Payload bandit algorithm")
    parser.add_argument("--dns-cache-ttl", type=int, dest="dns_cache_ttl", help="DNS cache TTL seconds")
    parser.add_argument("--prewarm", action="store_true", help="Pre-warm HTTP connections")
    parser.add_argument("--happy-eyeballs", action="store_true", help="Enable Happy Eyeballs dialer")
    parser.add_argument("--range-fetch-kb", type=int, help="Partial body fetch size in KB")
    parser.add_argument("--simhash", action="store_true", help="Enable simhash dedupe")
    parser.add_argument("--near-dup-th", type=int, dest="near_dup_th", help="Simhash Hamming distance threshold")
    parser.add_argument("--form-dedupe", action="store_true", help="Enable form schema dedupe")
    parser.add_argument("--server-weighting", action="store_true", help="Weight payloads by server fingerprint")
    parser.add_argument("--endpoint-budget-ms", type=int, help="Per-endpoint time budget in ms")
    parser.add_argument("--bloom", action="store_true", help="Enable persistent bloom skiplist")
    parser.add_argument("--bloom-bits", type=int, help="Bloom filter size in bits")
    parser.add_argument("--bloom-ttl", type=int, help="Bloom filter TTL hours")
    parser.add_argument("--cpu-target-pct", type=int, help="CPU usage target percentage")
    parser.add_argument("--cpu-pacer-min-rps", type=int, help="Minimum pacer rate")
    parser.add_argument("--cpu-pacer-max-rps", type=int, help="Maximum pacer rate")

    # SMART mode flags (opt-in)
    parser.add_argument("--smart", action="store_true", help="Enable SMART mode")
    parser.add_argument("--poc", action="store_true", help="Generate explainable PoC artifacts")
    parser.add_argument("--fusion", action="store_true", help="Enable signal fusion")
    parser.add_argument("--waf-adapt", action="store_true", help="Enable WAF-adaptive engine")
    parser.add_argument("--oob", action="store_true", help="Enable out-of-band checks")
    parser.add_argument("--xhr-map", action="store_true", help="Map client-side XHR/fetch flows")
    parser.add_argument("--dbms-fp", action="store_true", help="DBMS fingerprinting and robust timing")
    parser.add_argument("--flow-sm", action="store_true", help="Multi-step flow state machine")
    parser.add_argument("--dedupe-adv", action="store_true", help="Advanced SimHash/FormSig++ dedupe")
    parser.add_argument("--kg", action="store_true", help="Endpoint-param knowledge graph")
    parser.add_argument("--remediate", action="store_true", help="Developer remediation tips")
    parser.add_argument("--lang", choices=["tr", "en"], default="tr", help="Narration language")
    parser.add_argument("--report", choices=["json", "html", "all"], default="all", help="Report format")
    parser.add_argument("--no-consent", action="store_true", help="Skip SMART mode consent notice")
    parser.add_argument("--unsafe-artifacts", action="store_true", help="Do not redact secrets in PoC artifacts")

    args = parser.parse_args(argv)

    if args.autopilot:
        args.auto = True

    if args.smart and not args.no_consent:
        from pathlib import Path

        consent_file = Path.home() / ".sqldetector_smart_consent"
        if not consent_file.exists():
            print("Bu aracı yalnızca yetkili testlerde kullanın.")
            consent_file.write_text("ok")

    if args.smart:
        from sqldetector.ui.narrate import Narrator

        narrator = Narrator(lang=args.lang)
        narrator.step("Hedef profili çıkarılıyor…")

    settings = merge_settings(args)
    cfg = settings.__dict__

    if args.preset:
        preset_cfg = load_preset(args.preset).get("sqldetector", {})
        cfg = merge_dicts(preset_cfg, cfg)

    if args.auto:
        sysinfo = autosys.detect_system()
        domain = urlparse(args.url).hostname or args.url
        client = None
        try:
            import requests  # type: ignore

            client = requests.Session()
        except Exception:
            pass
        if client is None:
            print("AutoPilot requires the requests package", file=sys.stderr)
            return 1
        try:
            profile = selector.classify_target(args.url, client, sysinfo)
        except Exception:
            print("AutoPilot: unable to reach target", file=sys.stderr)
            return 1
        preset_name = args.force_preset or policy.choose_preset(profile)
        preset_cfg = load_preset(preset_name).get("sqldetector", {})
        cfg = merge_dicts(preset_cfg, cfg)
        cfg = apply_system_overrides(cfg, sysinfo, profile.get("rtt_ms"))
        store.save(domain, profile, preset_name)
        if args.print_plan:
            print(f"AutoPilot selected: {preset_name} (signals: {profile['signals']})")
            if args.dry_run:
                return 0
        settings = Settings(**cfg)
        print(
            f"AutoPilot selected: {preset_name} (signals: {profile['signals']})",
            file=sys.stderr,
        )
    else:
        sysinfo = autosys.detect_system()
        cfg = apply_system_overrides(cfg, sysinfo, None)
        settings = Settings(**cfg)

    if sys.platform != "win32":  # pragma: no cover - best effort
        try:
            import uvloop  # type: ignore

            uvloop.install()
        except Exception:
            pass

    return pipeline.run(args.url, dry_run=args.dry_run, settings=settings)


if __name__ == "__main__":
    main()
